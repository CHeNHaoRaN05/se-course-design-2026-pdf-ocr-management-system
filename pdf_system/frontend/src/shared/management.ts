import type { FileItem } from "./types";
export type Role = "user" | "viewer" | "admin";
export interface UserInfo {
  id: string;
  email: string;
  display_name: string;
  role: Role;
  disabled: boolean;
  created_at: string;
}
export interface QuotaOverview {
  files: number;
  storage_bytes: number;
  quota: {
    month: string;
    pages_reserved: number;
    pages_used: number;
    pages_committed: number;
  };
}
export interface ShareItem {
  id: string;
  file_id: string;
  token: string;
  share_url: string;
  expires_at: string | null;
  access_code: string | null;
  allow_download: boolean;
  visit_count: number;
  created_at: string;
}
export interface TrashItem extends FileItem {
  deleted_at: string;
  sha256?: string;
}
export interface AuditItem {
  id: string;
  actor_id: string;
  action: string;
  resource_id: string | null;
  created_at: string;
  detail?: Record<string, unknown>;
}
export const roleNames: Record<Role, string> = {
  user: "普通用户",
  viewer: "只读用户",
  admin: "管理员",
};
export function formatBytes(bytes: number): string {
  if (!bytes) return "0 B";
  const index = Math.min(Math.floor(Math.log(bytes) / Math.log(1024)), 3);
  return `${(bytes / 1024 ** index).toLocaleString("zh-CN", { maximumFractionDigits: index ? 1 : 0 })} ${["B", "KiB", "MiB", "GiB"][index]}`;
}
/** 后端 naive datetime 均为 UTC，避免浏览器按本地时间解释。 */
export function asDate(value: string): Date {
  return new Date(/(?:Z|[+-]\d{2}:\d{2})$/i.test(value) ? value : `${value}Z`);
}
export function formatDate(value?: string | null, time = false): string {
  if (!value) return "—";
  const date = asDate(value);
  return Number.isNaN(date.getTime())
    ? "—"
    : date.toLocaleString(
        "zh-CN",
        time
          ? {
              year: "numeric",
              month: "2-digit",
              day: "2-digit",
              hour: "2-digit",
              minute: "2-digit",
            }
          : { year: "numeric", month: "2-digit", day: "2-digit" },
      );
}
export const errorText = (error: unknown) =>
  error instanceof Error ? error.message : "操作失败，请重试。";
export function normalizeFolder(value: string): string {
  const parts = value
    .trim()
    .split(/[\\/]+/)
    .map((part) => part.trim())
    .filter(Boolean);
  if (parts.length > 5) throw new Error("分类最多支持 5 级。");
  if (parts.some((p) => p === "." || p === ".."))
    throw new Error("分类名称不能使用 . 或 ..。");
  const folder = "/" + parts.join("/");
  if (folder.length > 255) throw new Error("分类路径不能超过 255 个字符。");
  return folder;
}
export function parseTags(value: string): string[] {
  const tags = [
    ...new Set(
      value
        .split(/[,，\n]/)
        .map((tag) => tag.trim())
        .filter(Boolean),
    ),
  ];
  if (tags.length > 20 || tags.some((tag) => tag.length > 64))
    throw new Error("最多 20 个标签，每个标签不超过 64 个字符。");
  return tags;
}
export function uniqueFilename(
  name: string,
  existing: Iterable<string>,
): string {
  const names = new Set(existing);
  if (!names.has(name)) return name;
  const dot = name.lastIndexOf(".");
  const stem = dot > 0 ? name.slice(0, dot) : name;
  const ext = dot > 0 ? name.slice(dot) : "";
  let index = 1;
  while (names.has(`${stem}(${index})${ext}`)) index++;
  return `${stem}(${index})${ext}`;
}
export const statusNames: Record<string, string> = {
  none: "未识别",
  queued: "排队中",
  running: "识别中",
  retry_wait: "等待重试",
  succeeded: "已识别",
  partial_success: "部分成功",
  failed: "识别失败",
  cancelled: "已取消",
  unknown: "状态不可用",
};
