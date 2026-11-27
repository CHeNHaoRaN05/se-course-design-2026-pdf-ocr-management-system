/**
 * 现场用例的浏览器级校验（不是 CI 用例，跑一次取证用）。
 *
 * MODE=full      ：README 场景，覆盖 TC-READ-01 缩放钳制、TC-FILE-04 异常态、TC-SEARCH-03 片段转义
 * MODE=degraded  ：OCR 未挂载实例，覆盖 TC-OCR-01 的页面禁用与提示
 *
 * 用法：
 *   node scripts/verify-demo-ui.mjs full     http://127.0.0.1:5173 http://127.0.0.1:8000
 *   node scripts/verify-demo-ui.mjs degraded http://127.0.0.1:5174 http://127.0.0.1:8001
 */
import { chromium } from "@playwright/test";

const mode = process.argv[2] ?? "full";
const BASE = process.argv[3] ?? "http://127.0.0.1:5173";
const API = process.argv[4] ?? "http://127.0.0.1:8000";
const EMAIL = process.env.SE_EMAIL ?? "demo-user@example.com";
const PASSWORD = process.env.SE_PASSWORD ?? "Demo12345";

const results = [];
const pass = (id, detail) => {
  results.push({ id, ok: true, detail });
  console.log(`[PASS] ${id} | ${detail}`);
};
const fail = (id, detail) => {
  results.push({ id, ok: false, detail });
  console.log(`[FAIL] ${id} | ${detail}`);
};

async function makeTwoPagePdf() {
  const { PDFDocument, StandardFonts } = await import("pdf-lib");
  const doc = await PDFDocument.create();
  const font = await doc.embedFont(StandardFonts.Helvetica);
  for (const index of [1, 2]) {
    const page = doc.addPage([420, 595]);
    page.drawText(`verify page ${index}`, { x: 40, y: 520, size: 18, font });
  }
  return Buffer.from(await doc.save()).toString("base64");
}

async function setupFile(token) {
  const pdf = Buffer.from(await makeTwoPagePdf(), "base64");
  const body = new FormData();
  body.set("file", new Blob([pdf], { type: "application/pdf" }), "verify-ui.pdf");
  const response = await fetch(`${API}/api/v1/files`, {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` },
    body,
  });
  if (!response.ok) throw new Error(`上传样本失败：${response.status}`);
  return (await response.json()).id;
}

async function main() {
  const login = await fetch(`${API}/api/v1/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email: EMAIL, password: PASSWORD }),
  });
  if (!login.ok) throw new Error(`登录失败：${login.status}`);
  const token = (await login.json()).access_token;
  const fileId = await setupFile(token);

  const browser = await chromium.launch();
  const context = await browser.newContext();
  await context.addInitScript((value) => {
    localStorage.setItem("pdf_system_token", value);
  }, token);
  const page = await context.newPage();
  const dialogs = [];
  page.on("dialog", async (dialog) => {
    dialogs.push(dialog.message());
    await dialog.dismiss();
  });

  if (mode === "full") {
    // TC-READ-01：渲染、翻页与缩放钳制
    await page.goto(`${BASE}/files/${fileId}`, { waitUntil: "networkidle" });
    await page.waitForSelector("canvas", { timeout: 20000 });
    for (let i = 0; i < 15; i += 1) await page.getByLabel("缩小显示").click();
    const low = await page.locator("text=/^\\d+%$/").first().innerText();
    for (let i = 0; i < 40; i += 1) await page.getByLabel("放大显示").click();
    const high = await page.locator("text=/^\\d+%$/").first().innerText();
    await page.getByLabel("放大显示").click();
    const capped = await page.locator("text=/^\\d+%$/").first().innerText();
    if (low === "50%" && high === "300%" && capped === "300%")
      pass("TC-READ-01", `canvas 可见；缩放下限 ${low}、上限 ${high}，再点仍为 ${capped}`);
    else fail("TC-READ-01", `缩放下限 ${low}、上限 ${high}、再点 ${capped}`);

    // TC-FILE-04：接口 503 时显示失败而不是空库
    await page.route("**/api/v1/files/query*", (route) =>
      route.fulfill({ status: 503, contentType: "application/json", body: '{"detail":"upstream down"}' }),
    );
    await page.goto(`${BASE}/files`, { waitUntil: "networkidle" });
    const errorVisible = await page.getByText("文档库加载失败").isVisible().catch(() => false);
    const emptyVisible = await page.getByText("你的文档空间，等待第一份资料").isVisible().catch(() => false);
    if (errorVisible && !emptyVisible) pass("TC-FILE-04", "503 时显示“文档库加载失败”，未误报为空库");
    else fail("TC-FILE-04", `错误态=${errorVisible} 空态=${emptyVisible}`);
    await page.unroute("**/api/v1/files/query*");

    // TC-SEARCH-03：特殊字符按字面渲染，不执行脚本
    const keyword = "<script>alert(1)</script>";
    await page.goto(`${BASE}/search?q=${encodeURIComponent(keyword)}`, { waitUntil: "networkidle" });
    await page.waitForTimeout(1500);
    const literal = await page.getByText(keyword, { exact: false }).first().isVisible().catch(() => false);
    if (literal && dialogs.length === 0) pass("TC-SEARCH-03", "片段以文本呈现，未触发脚本对话框");
    else fail("TC-SEARCH-03", `字面可见=${literal} 对话框=${JSON.stringify(dialogs)}`);
  } else {
    // TC-OCR-01：未挂载时页面禁用提交并提示
    await page.goto(`${BASE}/files/${fileId}`, { waitUntil: "networkidle" });
    const notice = await page
      .getByText(/OCR 服务未挂载/)
      .isVisible()
      .catch(() => false);
    const submit = page.getByRole("button", { name: /开始识别|新建识别任务/ }).first();
    const disabled = await submit.isDisabled().catch(() => false);
    if (notice && disabled) pass("TC-OCR-01", "未挂载提示可见，开始识别按钮禁用");
    else fail("TC-OCR-01", `提示=${notice} 按钮禁用=${disabled}`);
  }

  await browser.close();
  const failed = results.filter((item) => !item.ok);
  console.log(`\n${mode} 模式：${results.length - failed.length}/${results.length} 通过`);
  process.exitCode = failed.length ? 1 : 0;
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
