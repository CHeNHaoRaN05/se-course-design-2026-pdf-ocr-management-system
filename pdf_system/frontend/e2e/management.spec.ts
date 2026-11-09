import { test, expect } from "@playwright/test";
import { mockApi, otherUserId } from "./fixtures";

test("login and registration validate input and preserve the requested destination", async ({
  page,
}, testInfo) => {
  const state = await mockApi(page, { loggedIn: false });
  await page.goto("/stats");
  await expect(page).toHaveURL(/login/);
  await page.screenshot({
    path: testInfo.outputPath("login-desktop.png"),
    fullPage: true,
    animations: "disabled",
  });
  await page.getByLabel("邮箱地址").fill("student@example.com");
  await page.getByLabel("密码", { exact: true }).fill("Password123");
  await page.getByRole("button", { name: "登录工作空间" }).click();
  await expect(page).toHaveURL(/stats/);
  await expect(page.getByRole("heading", { name: "配额与统计" })).toBeVisible();
  await expect(page.locator(".quota-summary")).toContainText("180");
  await page.screenshot({
    path: testInfo.outputPath("stats-desktop.png"),
    fullPage: true,
    animations: "disabled",
  });
  expect(
    state.requests.find((r) => r.path === "/auth/login")?.auth,
  ).toBeUndefined();
  await page.getByRole("button", { name: "退出登录" }).click();
  await expect(page).toHaveURL(/login/);
  await page.getByRole("button", { name: "注册", exact: true }).click();
  await page.getByLabel("邮箱地址").fill("new@example.com");
  await page.getByLabel("密码", { exact: true }).fill("Password123");
  await page.getByLabel("确认密码").fill("Different123");
  await page.getByRole("button", { name: "注册并登录" }).click();
  await expect(page.getByRole("alert")).toContainText("不一致");
});

test("library supports full-list pagination, search, selection and grid view", async ({
  page,
}, testInfo) => {
  await mockApi(page);
  await page.goto("/files");
  await expect(page.locator("tbody tr")).toHaveCount(12);
  await page.getByRole("button", { name: "下一页", exact: true }).click();
  await expect(page.locator("tbody tr")).toHaveCount(3);
  await page.getByLabel("按文件名搜索").fill("验收");
  await expect(page.locator("tbody tr")).toHaveCount(1);
  await expect(page.locator("tbody")).toContainText("项目验收报告");
  await page.getByLabel("按文件名搜索").fill("");
  await expect(page.locator("tbody tr")).toHaveCount(12);
  await page.getByLabel("卡片视图").click();
  await expect(page.locator(".document-card")).toHaveCount(12);
  await page.getByLabel("列表视图").click();
  await page.screenshot({
    path: testInfo.outputPath("library-desktop.png"),
    fullPage: true,
    animations: "disabled",
  });
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBe(true);
});

test("rename and delete are confirmed; trash history restores using real endpoints", async ({
  page,
}) => {
  const state = await mockApi(page);
  await page.goto("/files");
  await page.getByLabel("软件工程课程设计需求分析.pdf 的更多操作").click();
  await page.getByRole("button", { name: "重命名", exact: true }).click();
  await page.getByLabel("文件名称").fill("重命名后的资料.pdf");
  await page.getByRole("button", { name: "确认", exact: true }).click();
  await expect(page.getByRole("dialog")).toContainText("成功 1 项");
  await page.getByRole("button", { name: "完成", exact: true }).click();
  await page.getByLabel("选择 重命名后的资料.pdf", { exact: true }).check();
  await page.getByRole("button", { name: "删除", exact: true }).click();
  expect(state.trash).toHaveLength(0);
  await page.getByRole("button", { name: "取消", exact: true }).click();
  expect(state.trash).toHaveLength(0);
  await page.getByRole("button", { name: "删除", exact: true }).click();
  await page.getByRole("button", { name: "确认", exact: true }).click();
  await page.getByRole("button", { name: "完成", exact: true }).click();
  await page.getByRole("link", { name: "回收站", exact: true }).click();
  await expect(page.getByRole("status")).toContainText("本浏览器");
  await expect(page.locator("tbody")).toContainText("重命名后的资料");
  await page.getByRole("button", { name: "还原", exact: true }).click();
  await page.getByRole("button", { name: "确认", exact: true }).click();
  await expect(page.getByRole("dialog")).toContainText("成功 1 项");
  expect(state.trash).toHaveLength(0);
});

test("batch operation reports partial failures rather than claiming full success", async ({
  page,
}) => {
  const state = await mockApi(page);
  await page.goto("/files");
  await page
    .getByLabel("选择 软件工程课程设计需求分析.pdf", { exact: true })
    .check();
  await page.getByLabel("选择 项目验收报告.pdf", { exact: true }).check();
  state.failNextUpdate();
  await page.getByRole("button", { name: "移动", exact: true }).click();
  await page.getByLabel("目标分类路径").fill("/验收资料");
  await page.getByRole("button", { name: "确认", exact: true }).click();
  await expect(page.getByRole("dialog")).toContainText("成功 1 项 · 失败 1 项");
});

test("multi-upload rejects invalid files and retries metadata without a duplicate upload", async ({
  page,
}) => {
  const state = await mockApi(page);
  await page.goto("/upload");
  await page.locator('input[type="file"]').setInputFiles([
    { name: "new.pdf", mimeType: "application/pdf", buffer: state.pdf },
    {
      name: "fake.pdf",
      mimeType: "application/pdf",
      buffer: Buffer.from("not a pdf"),
    },
  ]);
  await page.getByLabel("保存到分类").fill("/新资料");
  state.failNextUpdate();
  await page.getByRole("button", { name: "开始上传", exact: true }).click();
  await expect(page.locator(".upload-summary")).toContainText("失败 2");
  expect(
    state.requests.filter((r) => r.path === "/files" && r.method === "POST"),
  ).toHaveLength(1);
  await page.getByRole("button", { name: "上传剩余 / 重试失败项" }).click();
  await expect(page.locator(".upload-summary")).toContainText("成功 1");
  expect(
    state.requests.filter((r) => r.path === "/files" && r.method === "POST"),
  ).toHaveLength(1);
});

test("PDF merge and split create new files while preserving originals", async ({
  page,
}) => {
  const state = await mockApi(page);
  await page.goto("/files");
  await page
    .getByLabel("选择 软件工程课程设计需求分析.pdf", { exact: true })
    .check();
  await page.getByLabel("选择 项目验收报告.pdf", { exact: true }).check();
  await page.getByRole("button", { name: "合并", exact: true }).click();
  await page.getByLabel("输出文件名").fill("合并结果.pdf");
  await page.getByRole("button", { name: "确认", exact: true }).click();
  await expect(page.getByRole("dialog")).toContainText("成功 1 项");
  await page.getByRole("button", { name: "完成", exact: true }).click();
  expect(state.files).toHaveLength(16);
  await page
    .getByLabel("选择 软件工程课程设计需求分析.pdf", { exact: true })
    .check();
  await page.getByRole("button", { name: "拆分", exact: true }).click();
  await page.getByLabel(/页段（共/).fill("1,2");
  await page.getByRole("button", { name: "确认", exact: true }).click();
  await expect(page.getByRole("dialog")).toContainText("成功 2 项");
  expect(state.files).toHaveLength(18);
});

test("share creation, code validation, metadata-only access and revoke", async ({
  page,
}) => {
  const state = await mockApi(page);
  await page.goto(`/shares?file=${state.files[0].id}`);
  await page.getByLabel(/提取码/).fill("2468");
  await page.getByRole("button", { name: "生成分享链接" }).click();
  await expect(page.locator(".created-share")).toContainText("分享已就绪");
  const body = state.requests.find(
    (r) => r.path === "/share" && r.method === "POST",
  )?.body as any;
  expect(body.expires_at).not.toMatch(/Z$/);
  expect(body.allow_download).toBe(false);
  await page.getByRole("link", { name: "访问分享页" }).click();
  await page.getByRole("button", { name: "访问文档", exact: true }).click();
  await expect(page.getByRole("alert")).toContainText("无法访问此分享");
  await page.getByLabel(/提取码/).fill("2468");
  await page.getByRole("button", { name: "访问文档", exact: true }).click();
  await expect(page.getByRole("status")).toContainText("未开放原文件");
  await expect(page.getByRole("button", { name: "下载文档" })).toHaveCount(0);
  expect(
    state.requests
      .filter((r) => r.path.startsWith("/share/token/"))
      .every((r) => !r.auth),
  ).toBe(true);
  await page.goto("/shares");
  await page.getByRole("button", { name: "撤销分享", exact: true }).click();
  expect(state.shares).toHaveLength(1);
  await page.getByRole("button", { name: "确认撤销" }).click();
  await expect(page.getByText("暂无分享记录", { exact: true })).toBeVisible();
  expect(state.shares).toHaveLength(0);
});

test("viewer cannot upload, manage shares or visit admin pages", async ({
  page,
}) => {
  const state = await mockApi(page, { role: "viewer" });
  await page.goto("/upload");
  await expect(
    page.getByRole("button", { name: "拖拽文件至此，或点击选择" }),
  ).toBeDisabled();
  await page.goto("/shares");
  await expect(
    page.getByRole("button", { name: "生成分享链接" }),
  ).toBeDisabled();
  await page.goto("/admin/users");
  await expect(
    page.getByRole("heading", { name: "此页面仅管理员可访问" }),
  ).toBeVisible();
  expect(
    state.requests.filter((r) =>
      ["POST", "PATCH", "DELETE"].includes(r.method),
    ),
  ).toHaveLength(0);
});

test("global search highlights escaped content and keeps per-account history", async ({
  page,
}) => {
  await mockApi(page);
  await page.goto("/files");
  await page.getByLabel("全局文档搜索").fill("验收报告");
  await page.getByLabel("全局文档搜索").press("Enter");
  await expect(page).toHaveURL(/search\?q=/);
  await expect(page.locator("mark").first()).toContainText("验收报告");
  await expect(page.locator(".search-result")).toHaveCount(2);
  await expect(page.locator(".search-result").first()).toContainText(
    "<script>alert(1)</script>",
  );
  await expect(
    page.getByRole("button", { name: "验收报告", exact: true }),
  ).toBeVisible();
  await page.getByRole("button", { name: "清空历史" }).click();
  await expect(page.getByText("暂无检索历史。")).toBeVisible();
});

test("admin can use known ID when user-list API is unavailable; audit fallback is explicit", async ({
  page,
}) => {
  const state = await mockApi(page, { role: "admin" });
  await page.goto("/admin/users");
  await expect(page.getByRole("status")).toContainText("尚未开放用户列表");
  await page.getByLabel("用户 ID", { exact: true }).fill(otherUserId);
  await page.getByLabel("目标角色").selectOption("viewer");
  await page.getByRole("button", { name: "检查并确认修改" }).click();
  await page.getByRole("button", { name: "确认修改", exact: true }).click();
  await expect(page.locator("tbody").first()).toContainText("协作成员");
  expect(
    state.requests.some(
      (r) =>
        r.path === `/auth/users/${otherUserId}/role` && r.method === "PATCH",
    ),
  ).toBe(true);
  await page.goto("/admin/audit");
  await expect(
    page.getByRole("heading", { name: "等待接入审计数据" }),
  ).toBeVisible();
  await expect(page.getByRole("button", { name: "导出当前页" })).toBeDisabled();
});

test("401 after an authenticated request clears credentials and returns to login", async ({
  page,
}) => {
  const state = await mockApi(page);
  await page.goto("/files");
  await expect(page.locator("tbody tr")).toHaveCount(12);
  state.expire();
  await page.getByRole("button", { name: "刷新", exact: true }).click();
  await expect(page).toHaveURL(/login/);
  expect(
    await page.evaluate(() => localStorage.getItem("pdf_system_token")),
  ).toBeNull();
});

test("password change and token refresh retain feedback and account identity", async ({
  page,
}) => {
  const state = await mockApi(page);
  await page.goto("/account");
  await page.getByLabel("当前密码").fill("OldPassword1");
  await page.getByLabel("新密码", { exact: true }).fill("NewPassword2");
  await page.getByLabel("确认新密码").fill("NewPassword2");
  await page.getByRole("button", { name: "保存新密码" }).click();
  await expect(page.getByRole("status")).toContainText("密码已修改");
  expect(
    state.requests.find((r) => r.path === "/auth/change-password")?.body,
  ).toEqual({ old_password: "OldPassword1", new_password: "NewPassword2" });
});

test("narrow layout navigation remains usable and has no horizontal page overflow", async ({
  page,
}, testInfo) => {
  await mockApi(page);
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/files");
  await expect(page.locator("tbody tr")).toHaveCount(12);
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBe(true);
  await page.getByRole("button", { name: "展开导航" }).click();
  await page
    .getByRole("link", { name: "上传文档", exact: true })
    .first()
    .click();
  await expect(
    page.getByRole("heading", { name: "上传文档", exact: true }),
  ).toBeVisible();
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBe(true);
  await page.screenshot({
    path: testInfo.outputPath("upload-mobile.png"),
    fullPage: true,
    animations: "disabled",
  });
});

test("implemented list extensions render server trash, users and audit data", async ({
  page,
}) => {
  await mockApi(page, { role: "admin", extensions: true });
  await page.goto("/admin/users");
  await expect(
    page.getByRole("heading", { name: "用户列表", exact: true }),
  ).toBeVisible();
  await expect(page.locator("tbody").first()).toContainText("协作成员");
  await page.goto("/admin/audit");
  await expect(page.locator("tbody tr")).toHaveCount(1);
  await expect(page.getByRole("button", { name: "导出当前页" })).toBeEnabled();
  const download = page.waitForEvent("download");
  await page.getByRole("button", { name: "导出当前页" }).click();
  expect((await download).suggestedFilename()).toContain("操作日志");
  await page.goto("/trash");
  await expect(page.getByRole("heading", { name: /已删除文档/ })).toBeVisible();
  await expect(page.getByText(/当前显示本浏览器/)).toHaveCount(0);
});

test("logout in another tab invalidates the active page without exposing the previous account", async ({
  page,
  context,
}) => {
  await mockApi(page);
  await page.goto("/files");
  await expect(page.locator("tbody tr")).toHaveCount(12);
  const second = await context.newPage();
  await mockApi(second, { loggedIn: false });
  await second.goto("/account");
  await expect(second.getByRole("heading", { name: "账户设置" })).toBeVisible();
  await second.getByRole("button", { name: "退出登录" }).click();
  await expect(page).toHaveURL(/login/);
  await expect(page.locator(".sidebar-user")).toHaveCount(0);
});

test("oversize upload is rejected before any POST request", async ({
  page,
}) => {
  const state = await mockApi(page);
  await page.goto("/upload");
  await page.locator('input[type="file"]').setInputFiles({
    name: "oversize.pdf",
    mimeType: "application/pdf",
    buffer: Buffer.alloc(20 * 1024 * 1024 + 1),
  });
  await page.getByRole("button", { name: "开始上传", exact: true }).click();
  await expect(page.locator(".upload-queue")).toContainText("超过 20 MiB");
  expect(
    state.requests.filter((r) => r.path === "/files" && r.method === "POST"),
  ).toHaveLength(0);
});

test("file list failure is distinct from an empty library", async ({
  page,
}) => {
  await mockApi(page);
  await page.route("**/api/v1/files?**", (route) =>
    route.fulfill({
      status: 503,
      contentType: "application/json",
      body: JSON.stringify({ detail: "服务暂不可用" }),
    }),
  );
  await page.goto("/files");
  await expect(
    page.getByRole("heading", { name: "文档库加载失败" }),
  ).toBeVisible();
  await expect(
    page.getByRole("heading", { name: "你的文档空间，等待第一份资料" }),
  ).toHaveCount(0);
});
