import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";
import ts from "typescript";

async function loadTypescript(path) {
  const source = await readFile(new URL(path, import.meta.url), "utf8");
  const { outputText } = ts.transpileModule(source, { compilerOptions: {
    module: ts.ModuleKind.ESNext, target: ts.ScriptTarget.ES2020,
  } });
  return import("data:text/javascript;base64," + Buffer.from(outputText).toString("base64"));
}
const { parsePageRange } = await loadTypescript("../src/features/ocr/pageRange.ts");
const { emptyFilters, historyKey, readHistory, rememberSearch } = await loadTypescript("../src/features/search/searchHistory.ts");

test("page selection is bounded, sorted and deduplicated", () => {
  assert.equal(parsePageRange(" "), undefined);
  assert.deepEqual(parsePageRange("3,1-3，5"), [1, 2, 3, 5]);
  for (const bad of ["0", "1-101", "4-2", "1,", "x", "-1", "1.5"]) {
    assert.throws(() => parsePageRange(bad));
  }
});

test("history is isolated by account, deduplicated, bounded and clearable", () => {
  const values = new Map();
  globalThis.localStorage = {
    getItem: (key) => values.get(key) ?? null,
    setItem: (key, value) => values.set(key, value),
    removeItem: (key) => values.delete(key),
  };
  for (let i = 0; i < 25; i++) rememberSearch("alice", { ...emptyFilters, q: String(i) });
  assert.equal(readHistory("alice").length, 20);
  assert.deepEqual(readHistory("bob"), []);
  rememberSearch("alice", { ...emptyFilters, q: "22" });
  assert.equal(readHistory("alice")[0].q, "22");
  assert.equal(readHistory("alice").length, 20);
  rememberSearch("alice", { ...emptyFilters, q: "22", tag: "实验" });
  assert.equal(readHistory("alice")[0].tag, "实验");
  localStorage.removeItem(historyKey("alice"));
  assert.deepEqual(readHistory("alice"), []);
  localStorage.setItem(historyKey("alice"), "broken JSON");
  assert.deepEqual(readHistory("alice"), []);
  localStorage.setItem(historyKey("alice"), '[{"q": "missing fields"}]');
  assert.deepEqual(readHistory("alice"), []);
});

test("disabled browser storage does not break searching", () => {
  globalThis.localStorage = {
    getItem() { throw new Error("disabled"); },
    setItem() { throw new Error("full"); },
  };
  assert.deepEqual(readHistory("alice"), []);
  assert.equal(rememberSearch("alice", { ...emptyFilters, q: "测试" })[0].q, "测试");
});
