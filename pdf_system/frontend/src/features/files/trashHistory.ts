import type { FileItem } from "../../shared/types";
import type { TrashItem } from "../../shared/management";
const key = (userId: string) => `pdf_trash_history_v1:${userId}`;
export function readTrash(userId: string): TrashItem[] {
  try {
    const value: unknown = JSON.parse(
      localStorage.getItem(key(userId)) ?? "[]",
    );
    return Array.isArray(value)
      ? value
          .filter(
            (row): row is TrashItem =>
              !!row &&
              typeof row.id === "string" &&
              typeof row.name === "string" &&
              typeof row.deleted_at === "string" &&
              Array.isArray(row.tags),
          )
          .slice(0, 1000)
      : [];
  } catch {
    return [];
  }
}
function save(userId: string, rows: TrashItem[]) {
  try {
    localStorage.setItem(key(userId), JSON.stringify(rows));
  } catch {
    /* 列表缓存不是服务端事实，失败不阻止删除或还原 */
  }
}
export function rememberTrash(userId: string, file: FileItem) {
  save(
    userId,
    [
      { ...file, deleted_at: new Date().toISOString() },
      ...readTrash(userId).filter((row) => row.id !== file.id),
    ].slice(0, 1000),
  );
}
export function forgetTrash(userId: string, id: string) {
  save(
    userId,
    readTrash(userId).filter((row) => row.id !== id),
  );
}
