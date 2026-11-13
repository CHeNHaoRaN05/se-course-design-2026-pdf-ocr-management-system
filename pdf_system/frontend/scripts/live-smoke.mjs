/** Optional smoke test against running, disposable local API + Vite servers.
 * Creates a test account and documents; use an isolated database/storage.
 * Run: node scripts/live-smoke.mjs
 */
import assert from "node:assert/strict";
import { randomBytes } from "node:crypto";
import { mkdirSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { chromium, expect } from "@playwright/test";
import { PDFDocument } from "pdf-lib";

const browser = await chromium.launch();
const context = await browser.newContext({
  viewport: { width: 1440, height: 1000 },
});
const page = await context.newPage();
const origin = process.env.SE_FRONTEND_ORIGIN || "http://127.0.0.1:5173";
const password = randomBytes(16).toString("hex") + "A1";
const email = `frontend-smoke-${randomBytes(5).toString("hex")}@example.com`;
const errors = [];
page.on("pageerror", (error) => errors.push(error.message));
const completed = [];
mkdirSync("test-results", { recursive: true });
try {
  await page.goto(`${origin}/login`);
  await page.getByRole("button", { name: "注册", exact: true }).click();
  await page.getByLabel("邮箱地址").fill(email);
  await page.getByLabel(/显示名称/).fill("前端真实接口联调");
  await page.getByLabel("密码", { exact: true }).fill(password);
  await page.getByLabel("确认密码").fill(password);
  await page.getByRole("button", { name: "注册并登录" }).click();
  await expect(page).toHaveURL(/\/files$/);
  await expect(
    page.getByRole("heading", { name: "你的文档空间，等待第一份资料" }),
  ).toBeVisible();
  completed.push("register/login/profile");

  const pdf = await PDFDocument.create();
  pdf.addPage([595, 842]);
  pdf.addPage([595, 842]);
  const buffer = Buffer.from(await pdf.save());
  await page.goto(`${origin}/upload`);
  await page.locator('input[type="file"]').setInputFiles([
    { name: "联调样本一.pdf", mimeType: "application/pdf", buffer },
    { name: "联调样本二.pdf", mimeType: "application/pdf", buffer },
  ]);
  await page.getByLabel("保存到分类").fill("/联调/课程资料");
  await page.getByLabel("添加标签").fill("联调, 验证");
  await page.getByRole("button", { name: "开始上传", exact: true }).click();
  await expect(page.locator(".upload-summary")).toContainText("成功 2", {
    timeout: 15000,
  });
  await page.goto(`${origin}/files`);
  await expect(page.locator("tbody tr")).toHaveCount(2);
  completed.push("multi-upload/metadata/list");

  await page.getByLabel("选择 联调样本一.pdf", { exact: true }).check();
  await page.getByLabel("选择 联调样本二.pdf", { exact: true }).check();
  await page.getByRole("button", { name: "合并", exact: true }).click();
  await page.getByLabel("输出文件名").fill("真实合并.pdf");
  await page.getByRole("button", { name: "确认", exact: true }).click();
  await expect(page.getByRole("dialog")).toContainText("成功 1 项");
  await page.getByRole("button", { name: "完成", exact: true }).click();
  await expect(page.locator("tbody tr")).toHaveCount(3);
  await page.getByLabel("选择 真实合并.pdf", { exact: true }).check();
  await page.getByRole("button", { name: "拆分", exact: true }).click();
  await page.getByLabel(/页段（共/).fill("1-2,3-4");
  await page.getByRole("button", { name: "确认", exact: true }).click();
  await expect(page.getByRole("dialog")).toContainText("成功 2 项");
  await page.getByRole("button", { name: "完成", exact: true }).click();
  await expect(page.locator("tbody tr")).toHaveCount(5);
  completed.push("merge/split/real-PDF-validation");

  await page.goto(`${origin}/shares`);
  await page.getByLabel("选择文档").selectOption({ label: "联调样本一.pdf" });
  await page.getByLabel(/提取码/).fill("2468");
  await page.getByLabel("允许访问与下载原文件").check();
  await page.getByRole("button", { name: "生成分享链接" }).click();
  await expect(page.locator(".created-share")).toContainText("分享已就绪");
  const shareUrl = await page.locator("#created-link").inputValue();
  const guest = await browser.newContext();
  const guestPage = await guest.newPage();
  await guestPage.goto(shareUrl);
  await guestPage.getByLabel(/提取码/).fill("2468");
  await guestPage
    .getByRole("button", { name: "访问文档", exact: true })
    .click();
  const download = guestPage.waitForEvent("download");
  await guestPage
    .getByRole("button", { name: "下载文档", exact: true })
    .click();
  assert.equal((await download).suggestedFilename(), "联调样本一.pdf");
  await page.getByRole("button", { name: "撤销分享", exact: true }).click();
  await page.getByRole("button", { name: "确认撤销", exact: true }).click();
  await guestPage.reload();
  await guestPage.getByLabel(/提取码/).fill("2468");
  await guestPage
    .getByRole("button", { name: "访问文档", exact: true })
    .click();
  await expect(guestPage.getByRole("alert")).toContainText("无法访问此分享");
  await guest.close();
  completed.push("share/guest-code/download/revoke");

  await page.goto(`${origin}/files`);
  await page.getByLabel("选择 联调样本一.pdf", { exact: true }).check();
  await page.getByRole("button", { name: "删除", exact: true }).click();
  await page.getByRole("button", { name: "确认", exact: true }).click();
  await expect(page.getByRole("dialog")).toContainText("成功 1 项");
  await page.getByRole("button", { name: "完成", exact: true }).click();
  await page.goto(`${origin}/trash`);
  await expect(page.locator("tbody tr")).toHaveCount(1);
  await page.getByRole("button", { name: "还原", exact: true }).click();
  await page.getByRole("button", { name: "确认", exact: true }).click();
  await expect(page.getByRole("dialog")).toContainText("成功 1 项");
  await page.getByRole("button", { name: "完成", exact: true }).click();
  await page.goto(`${origin}/files`);
  await expect(page.locator("tbody tr")).toHaveCount(5);
  completed.push("soft-delete/server-trash/restore");

  await page.goto(`${origin}/stats`);
  await expect(page.locator(".metric-card").first()).toContainText("5");
  await page.goto(`${origin}/account`);
  await page.getByLabel("当前密码").fill(password);
  await page.getByLabel("新密码", { exact: true }).fill(password + "2");
  await page.getByLabel("确认新密码").fill(password + "2");
  await page.getByRole("button", { name: "保存新密码" }).click();
  await expect(page.getByRole("status")).toContainText("密码已修改");
  await page.getByRole("button", { name: "续期当前会话" }).click();
  await expect(page.getByRole("status")).toContainText("当前登录会话已续期");
  await page.getByRole("button", { name: "退出登录" }).click();
  await expect(page).toHaveURL(/login/);
  completed.push("quota/password/token-rotation/logout");
  assert.deepEqual(errors, []);
  writeFileSync(
    "test-results/live-result.json",
    JSON.stringify(
      { result: "passed", backend: "real FastAPI/SQLite", completed },
      null,
      2,
    ),
  );
  console.log(
    JSON.stringify(
      {
        result: "passed",
        backend: "real FastAPI, SQLite, OCR disabled",
        completed,
      },
      null,
      2,
    ),
  );
} catch (error) {
  writeFileSync(
    "test-results/live-result.json",
    JSON.stringify(
      { result: "failed", completed, error: String(error) },
      null,
      2,
    ),
  );
  console.error(
    JSON.stringify(
      { result: "failed", completed, error: String(error) },
      null,
      2,
    ),
  );
  await page
    .screenshot({
      path: join("test-results", "live-failure.png"),
      fullPage: true,
      animations: "disabled",
    })
    .catch(() => {});
  process.exitCode = 1;
} finally {
  await context.close();
  await browser.close();
}
