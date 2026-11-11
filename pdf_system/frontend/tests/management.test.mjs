import assert from "node:assert/strict";
import test from "node:test";
import { readFile } from "node:fs/promises";
import ts from "typescript";
import { PDFDocument } from "pdf-lib";

async function load(path, replacements = {}) {
  let source = await readFile(new URL(path, import.meta.url), "utf8");
  for (const [from, to] of Object.entries(replacements))
    source = source.replaceAll(from, to);
  const { outputText } = ts.transpileModule(source, {
    compilerOptions: {
      module: ts.ModuleKind.ESNext,
      target: ts.ScriptTarget.ES2022,
    },
  });
  return import(
    `data:text/javascript;base64,${Buffer.from(outputText).toString("base64")}`
  );
}
const management = await load("../src/features/management/management.ts");
const pdf = await load("../src/features/files/pdfTools.ts", {
  '"pdf-lib"': JSON.stringify(import.meta.resolve("pdf-lib")),
});

test("folder and tag validation applies depth limits, normalization and deduplication", () => {
  assert.equal(
    management.normalizeFolder(" 学习 / 软件工程 "),
    "/学习/软件工程",
  );
  assert.equal(management.normalizeFolder("///a//b/"), "/a/b");
  assert.equal(management.normalizeFolder(""), "/");
  assert.throws(() => management.normalizeFolder("/a/b/c/d/e/f"));
  assert.throws(() => management.normalizeFolder("a/../b"));
  assert.deepEqual(management.parseTags("合同，归档,合同\n 2026 "), [
    "合同",
    "归档",
    "2026",
  ]);
  assert.throws(() => management.parseTags("a".repeat(65)));
  assert.throws(() =>
    management.parseTags(
      Array.from({ length: 21 }, (_, i) => `${i}`).join(","),
    ),
  );
});
test("duplicate filenames keep existing documents intact", () => {
  assert.equal(
    management.uniqueFilename("报告.pdf", ["报告.pdf", "报告(1).pdf"]),
    "报告(2).pdf",
  );
  assert.equal(management.uniqueFilename("a.b.pdf", ["a.b.pdf"]), "a.b(1).pdf");
});
test("naive backend timestamps are interpreted as UTC", () => {
  assert.equal(
    management.asDate("2026-11-09T01:30:00").toISOString(),
    "2026-11-09T01:30:00.000Z",
  );
  assert.equal(
    management.asDate("2026-11-09T09:30:00+08:00").toISOString(),
    "2026-11-09T01:30:00.000Z",
  );
});
test("PDF split rejects overlapping, invalid and out-of-bounds ranges", () => {
  assert.deepEqual(pdf.splitGroups("1-2,4", 4), [[0, 1], [3]]);
  assert.deepEqual(pdf.splitGroups("", 5, 2), [[0, 1], [2, 3], [4]]);
  for (const bad of ["1-3,3-4", "0", "1-5", "3-1", "1,", "", "-1", "x"])
    assert.throws(() => pdf.splitGroups(bad, 4));
  for (const every of [0, -1, 6, 1.5, NaN])
    assert.throws(() => pdf.splitGroups("", 5, every));
});
test("PDF merge/split preserves requested page order and original documents", async () => {
  const one = await PDFDocument.create();
  one.addPage([100, 200]);
  one.addPage([300, 400]);
  const two = await PDFDocument.create();
  two.addPage([500, 600]);
  const first = await one.save();
  const second = await two.save();
  const merged = await PDFDocument.load(
    await pdf.mergePdfs([first.buffer, second.buffer]),
  );
  assert.deepEqual(
    merged.getPages().map((page) => page.getWidth()),
    [100, 300, 500],
  );
  const split = await pdf.splitPdf((await merged.save()).buffer, [[2], [0, 1]]);
  assert.deepEqual(
    (await PDFDocument.load(split[0]))
      .getPages()
      .map((page) => page.getWidth()),
    [500],
  );
  assert.deepEqual(
    (await PDFDocument.load(split[1]))
      .getPages()
      .map((page) => page.getWidth()),
    [100, 300],
  );
  assert.equal((await PDFDocument.load(first)).getPageCount(), 2);
  const large = await PDFDocument.create();
  for (let i = 0; i < 100; i++) large.addPage();
  await assert.rejects(
    pdf.mergePdfs([(await large.save()).buffer, second.buffer]),
    /100 页/,
  );
});
