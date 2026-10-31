export interface SearchFilters {
  q: string; file_id: string; file_name: string; tag: string; date_from: string; date_to: string;
}
export const emptyFilters: SearchFilters = { q: "", file_id: "", file_name: "", tag: "", date_from: "", date_to: "" };
export const historyKey = (userId: string) => `pdf_search_history_v1:${userId}`;
export function readHistory(userId: string): SearchFilters[] {
  try {
    const value: unknown = JSON.parse(localStorage.getItem(historyKey(userId)) ?? "[]");
    if (!Array.isArray(value)) return [];
    return value.filter((row): row is SearchFilters => row && typeof row === "object"
      && Object.keys(emptyFilters).every((key) => typeof row[key] === "string")
      && row.q.trim().length > 0 && row.q.length <= 100).slice(0, 20);
  } catch { return []; }
}
export function rememberSearch(userId: string, filters: SearchFilters): SearchFilters[] {
  const next = [filters, ...readHistory(userId).filter((row) =>
    !Object.keys(emptyFilters).every((key) => row[key as keyof SearchFilters] === filters[key as keyof SearchFilters]))].slice(0, 20);
  try { localStorage.setItem(historyKey(userId), JSON.stringify(next)); } catch { /* Storage may be disabled. */ }
  return next;
}
