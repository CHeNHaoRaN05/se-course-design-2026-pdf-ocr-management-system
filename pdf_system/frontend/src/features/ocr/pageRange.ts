/** Parse a bounded 1-based page selection; empty input means all pages. */
export function parsePageRange(value: string): number[] | undefined {
  if (!value.trim()) return undefined;
  const pages = new Set<number>();
  for (const part of value.split(/[,，]/)) {
    const match = part.trim().match(/^(\d+)(?:\s*-\s*(\d+))?$/);
    if (!match) throw new Error("页码格式应为 1-3,5");
    const start = Number(match[1]), end = Number(match[2] ?? match[1]);
    if (start < 1 || end < start || end > 100) throw new Error("页码须在 1–100 之间，且范围递增");
    for (let page = start; page <= end; page++) pages.add(page);
  }
  return [...pages].sort((a, b) => a - b);
}
