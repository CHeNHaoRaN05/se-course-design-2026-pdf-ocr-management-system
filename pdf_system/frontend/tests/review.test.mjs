import assert from "node:assert/strict";
import test from "node:test";
import { build } from "esbuild";
async function load(entry) {
  const result = await build({
    entryPoints: [entry],
    bundle: true,
    write: false,
    format: "esm",
    platform: "node",
    logLevel: "silent",
  });
  return import(
    `data:text/javascript;base64,${Buffer.from(result.outputFiles[0].text).toString("base64")}`
  );
}
const http = await load("src/shared/http.ts");
const files = await load("src/features/files/filesApi.ts");
const { readAllPages } = await load("src/features/management/pagination.ts");
const { csvCell, validDateRange } = await load(
  "src/features/management/csv.ts",
);
const { formatBytes, formatDate, normalizeFilename, uniqueFilename } =
  await load("src/features/management/management.ts");
const storage = new Map();
globalThis.localStorage = {
  getItem: (k) => storage.get(k) ?? null,
  setItem: (k, v) => storage.set(k, v),
  removeItem: (k) => storage.delete(k),
};
globalThis.window = new EventTarget();

test("real backend error codes, empty detail, nested object and 422 fallback", async () => {
  for (const [detail, expected] of [
    ["upload_size_limit", "20 MiB"],
    ["invalid_image", "图片"],
    ["pdf_page_limit", "100"],
    ["render_pixel_limit", "像素"],
    ["invalid_or_encrypted_pdf", "加密"],
    ["only_pdf_png_jpeg_supported", "JPEG"],
    ["image_pixel_limit", "2000"],
    ["invalid_storage_key", "存储"],
    ["", "输入参数"],
    [{ msg: "x" }, "x"],
    [[{ msg: "bad" }], "bad"],
  ]) {
    globalThis.fetch = async () =>
      new Response(JSON.stringify({ detail }), { status: 422 });
    await assert.rejects(
      http.api("/probe"),
      (e) => e.status === 422 && e.message.includes(expected),
    );
  }
});
test("aborted stale requests never clear an active credential", async () => {
  http.tokenStore.set("new");
  const controller = new AbortController();
  globalThis.fetch = async () => {
    controller.abort();
    return new Response("{}", { status: 401 });
  };
  await assert.rejects(http.api("/probe", { signal: controller.signal }), {
    name: "AbortError",
  });
  assert.equal(http.tokenStore.get(), "new");
});
test("repeated pages terminate with an error instead of infinite requests", async () => {
  let requests = 0;
  const page = Array.from({ length: 100 }, (_, id) => ({ id: String(id) }));
  await assert.rejects(
    readAllPages(async () => {
      requests++;
      return page;
    }),
    /重复/,
  );
  assert.equal(requests, 2);
  let offsetLog = [];
  const result = await readAllPages(async (offset) => {
    offsetLog.push(offset);
    return offset === 0 ? page : [{ id: "last" }];
  });
  assert.equal(result.length, 101);
  assert.deepEqual(offsetLog, [0, 100]);
});
test("file names preserve extension under truncation, collision and trailing spaces", async () => {
  const name = "a".repeat(300) + ".pdf";
  const first = normalizeFilename(name);
  assert.equal(first.length, 255);
  assert.ok(first.endsWith(".pdf"));
  const second = uniqueFilename(name, [first]);
  assert.equal(second.length, 255);
  assert.ok(second.endsWith("(1).pdf"));
  await files.validateUpload(
    new File(["%PDF-1.7\n"], "报告.pdf ", { type: "application/pdf" }),
  );
});
test("byte/date boundaries keep UTC timestamps correct and date-only values stable", () => {
  assert.equal(formatBytes(-1), "—");
  assert.equal(formatBytes(NaN), "—");
  assert.equal(formatBytes(Infinity), "—");
  assert.equal(formatBytes(0.5), "0.5 B");
  assert.equal(formatBytes(0), "0 B");
  assert.equal(formatDate("2026-11-10", true), "2026/11/10");
  const original = process.env.TZ;
  process.env.TZ = "Asia/Shanghai";
  assert.ok(formatDate("2026-11-10T08:30:00", true).includes("16:30"));
  assert.equal(
    formatDate("2026-11-10T08:30:00Z", true),
    formatDate("2026-11-10T08:30:00", true),
  );
  if (original === undefined) delete process.env.TZ;
  else process.env.TZ = original;
});
test("CSV retains raw values and neutralizes formula/control prefixes", () => {
  assert.equal(csvCell("file_uploaded"), '"file_uploaded"');
  assert.equal(csvCell("2026-11-10T08:30:00"), '"2026-11-10T08:30:00"');
  for (const value of [
    "=1+1",
    " +1",
    "@SUM(1)",
    "-1",
    ";cmd",
    "\t=1",
    "\n=1",
    "'abc",
  ])
    assert.ok(csvCell(value).startsWith("\"'"));
  assert.equal(csvCell('a,"b"'), '"a,""b"""');
  assert.equal(validDateRange("2026-02-30", ""), false);
  assert.equal(validDateRange("2026-11-10", "2026-11-09"), false);
  assert.equal(validDateRange("2026-11-09", "2026-11-10"), true);
});
