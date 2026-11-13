/** No page.route, route.fulfill, or fake API transport in this project. */
import {
  test,
  expect,
  type Page,
  type APIRequestContext,
} from "@playwright/test";
import { PDFDocument } from "pdf-lib";
import { randomUUID } from "node:crypto";
async function setup(page: Page, request: APIRequestContext) {
  const email = `${randomUUID()}@e2e.test`;
  const password = "TestPassword123";
  const result = await request.post("/api/v1/auth/register", {
    data: { email, password },
  });
  expect(result.status()).toBe(201);
  const { access_token } = await result.json();
  await page.addInitScript(
    (token) => localStorage.setItem("pdf_system_token", token),
    access_token,
  );
  return {
    headers: { Authorization: `Bearer ${access_token}` },
    token: access_token,
  };
}
async function pdf(pages = 2) {
  const doc = await PDFDocument.create();
  for (let i = 0; i < pages; i++) doc.addPage([100 + i * 10, 200]);
  return Buffer.from(await doc.save());
}
async function upload(
  request: APIRequestContext,
  headers: Record<string, string>,
  name = "document.pdf",
  buffer?: Buffer,
) {
  const r = await request.post("/api/v1/files", {
    headers,
    multipart: {
      file: {
        name,
        mimeType: "application/pdf",
        buffer: buffer ?? (await pdf()),
      },
    },
  });
  expect(r.status()).toBe(201);
  return r.json();
}

test("real query total and page boundaries, missing OCR status, text and type filters", async ({
  page,
  request,
}) => {
  const { headers } = await setup(page, request);
  for (let i = 0; i < 14; i++)
    await upload(request, headers, `document-${i}.pdf`);
  await page.goto("/files");
  await expect(page.locator("tbody tr")).toHaveCount(12);
  await expect(page.locator(".pagination")).toContainText("共 14 项");
  await expect(page.getByLabel("识别状态", { exact: true })).toBeDisabled();
  await page.getByRole("button", { name: "下一页", exact: true }).click();
  await expect(page.locator("tbody tr")).toHaveCount(2);
  await page.getByLabel("按文件名搜索").fill("document-13");
  await expect(page.locator("tbody tr")).toHaveCount(1);
  const response = await request.get(
    "/api/v1/files/query?status=succeeded&sort=status",
    { headers },
  );
  const data = await response.json();
  expect(data.total).toBe(14);
  expect(data.status_available).toBe(false);
  expect(data.effective_sort).toBe("newest");
  await page.getByLabel("文件类型", { exact: true }).selectOption("image/png");
  await expect(page.locator("tbody tr")).toHaveCount(0);
});

test("real concurrent uploads allocate unique names across requests", async ({
  page,
  request,
}) => {
  const { headers } = await setup(page, request);
  const buffer = await pdf();
  const results = await Promise.all(
    Array.from({ length: 4 }, () =>
      upload(request, headers, "same.pdf", buffer),
    ),
  );
  expect(new Set(results.map((r) => r.name)).size).toBe(4);
  await page.goto("/files");
  await expect(page.locator("tbody tr")).toHaveCount(4);
});

test("browser merge and split operate on real PDFs and persist lineage", async ({
  page,
  request,
}) => {
  const { headers } = await setup(page, request);
  const a = await upload(request, headers, "first.pdf");
  const b = await upload(request, headers, "second.pdf");
  await page.goto("/files");
  await page.getByLabel("选择 first.pdf", { exact: true }).check();
  await page.getByLabel("选择 second.pdf", { exact: true }).check();
  await page.getByRole("button", { name: "合并", exact: true }).click();
  await page.getByLabel("输出文件名").fill("merged.pdf");
  await page.getByRole("button", { name: "确认", exact: true }).click();
  await expect(page.getByRole("dialog")).toContainText("成功 1 项");
  await page.getByRole("button", { name: "完成", exact: true }).click();
  const list = await (
    await request.get("/api/v1/files/query?q=merged.pdf", { headers })
  ).json();
  const merged = list.items[0];
  expect(merged.page_count).toBe(4);
  expect(merged.version).toBe(2);
  expect(merged.replaced_from).toBe(a.id);
  const content = await request.get(`/api/v1/files/${merged.id}/content`, {
    headers,
  });
  expect((await PDFDocument.load(await content.body())).getPageCount()).toBe(4);
  await page.getByLabel("选择 merged.pdf", { exact: true }).check();
  await page.getByRole("button", { name: "拆分", exact: true }).click();
  await page.getByLabel(/页段（共/).fill("1-2,3-4");
  await page.getByRole("button", { name: "确认", exact: true }).click();
  await expect(page.getByRole("dialog")).toContainText("成功 2 项");
  expect(
    (await request.get(`/api/v1/files/${b.id}`, { headers })).status(),
  ).toBe(200);
});

test("real bulk returns per-item deleted-file failures and total failure 409", async ({
  page,
  request,
}) => {
  const { headers } = await setup(page, request);
  const a = await upload(request, headers, "old.pdf");
  const b = await upload(request, headers, "active.pdf");
  await request.delete(`/api/v1/files/${a.id}`, { headers });
  const result = await request.post("/api/v1/files/bulk", {
    headers,
    data: { file_ids: [a.id, b.id], action: "delete" },
  });
  expect(result.status()).toBe(207);
  expect((await result.json()).succeeded).toBe(1);
  const failed = await request.post("/api/v1/files/bulk", {
    headers,
    data: { file_ids: [a.id], action: "delete" },
  });
  expect(failed.status()).toBe(409);
  await page.goto("/trash");
  await expect(page.locator("tbody tr")).toHaveCount(2);
  await expect(page.locator(".pagination")).toContainText("共 2 项");
});

test("real admin and audit pagination, non-admin forbidden", async ({
  page,
  request,
}) => {
  const { headers } = await setup(page, request);
  expect(
    (
      await request.get("/api/v1/auth/users?envelope=true", { headers })
    ).status(),
  ).toBe(403);
  const login = await request.post("/api/v1/auth/login", {
    data: {
      email: "admin@e2e.test",
      password: process.env.SE_SMOKE_ADMIN_PASSWORD,
    },
  });
  expect(login.status()).toBe(200);
  const admin = await login.json();
  await page.addInitScript(
    (token) => localStorage.setItem("pdf_system_token", token),
    admin.access_token,
  );
  await upload(request, headers);
  await page.goto("/admin/users");
  await expect(page.locator(".pagination")).toBeVisible();
  await expect(
    page.getByRole("heading", { name: "用户列表", exact: true }),
  ).toBeVisible();
  await page.goto("/admin/audit");
  await expect(page.locator("tbody tr").first()).toBeVisible();
  const resp = await request.get("/api/v1/audit?envelope=true&limit=1", {
    headers: { Authorization: `Bearer ${admin.access_token}` },
  });
  const data = await resp.json();
  expect(data.items).toHaveLength(1);
  expect(data.total).toBeGreaterThan(0);
});

test("real upload and metadata persistence with proxy cold-start dependencies", async ({
  page,
  request,
}) => {
  await setup(page, request);
  await page.goto("/upload");
  await page.locator("input[type=file]").setInputFiles([
    { name: "a.pdf", mimeType: "application/pdf", buffer: await pdf() },
    { name: "b.pdf", mimeType: "application/pdf", buffer: await pdf() },
  ]);
  await page.getByLabel("保存到分类").fill("/真实/验收");
  await page.getByLabel("添加标签").fill("test");
  await page.getByRole("button", { name: "开始上传", exact: true }).click();
  await expect(page.locator(".upload-summary")).toContainText("成功 2");
  await page.goto("/files");
  await expect(page.locator("tbody tr")).toHaveCount(2);
  await expect(
    page.locator("tbody").getByText("test", { exact: true }),
  ).toHaveCount(2);
});

test("real oversized queries, blank suggest and naive share expiry are rejected", async ({
  page,
  request,
}) => {
  const { headers } = await setup(page, request);
  const file = await upload(request, headers);
  for (const path of [
    "/files?q=" + "x".repeat(256),
    "/files/query?folder=" + "x".repeat(256),
    "/search/suggest?q=%20%20",
  ])
    expect((await request.get("/api/v1" + path, { headers })).status()).toBe(
      422,
    );
  const r = await request.post("/api/v1/share", {
    headers,
    data: { file_id: file.id, expires_at: "2099-01-01T12:00:00" },
  });
  expect(r.status()).toBe(422);
  await page.goto(`/shares?file=${file.id}`);
  await page.getByLabel(/提取码/).fill("abc123");
  await page.getByRole("button", { name: "生成分享链接" }).click();
  await expect(page.locator(".created-share")).toContainText("分享已就绪");
});

test('real metadata changes refresh another open library tab',async({page,context,request})=>{
 const {headers}=await setup(page,request);await upload(request,headers,'before.pdf');
 await page.goto('/files');const second=await context.newPage();await second.goto('http://127.0.0.1:5175/files');await expect(second.locator('tbody')).toContainText('before.pdf');
 await page.getByLabel('before.pdf 的更多操作').click();await page.getByRole('button',{name:'重命名',exact:true}).click();await page.getByLabel('文件名称').fill('after.pdf');await page.getByRole('button',{name:'确认',exact:true}).click();
 await expect(page.getByRole('dialog')).toContainText('成功 1 项');await expect(second.locator('tbody')).toContainText('after.pdf');await second.close();
});
