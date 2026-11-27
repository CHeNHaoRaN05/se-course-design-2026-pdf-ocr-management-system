import assert from "node:assert/strict";
import test from "node:test";
import { readFile } from "node:fs/promises";
import ts from "typescript";

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
