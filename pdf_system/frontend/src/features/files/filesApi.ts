import { normalizeFilename } from "../management/management";
import { readAllPages } from "../management/pagination";
import { delay, throwIfAborted } from "../../shared/requests";
import { api, apiBlob, ApiError } from "../../shared/http";
import type { FileItem } from "../../shared/types";

export const listFiles = (params: Record<string, string> = {}) =>
  api<FileItem[]>("/files?" + new URLSearchParams(params));

export const uploadFile = (file: File, signal?: AbortSignal) => {
  const body = new FormData();
  body.set("file", file, normalizeFilename(file.name));
  return api<FileItem>("/files", { method: "POST", body, signal });
};

export const deleteFile = (fileId: string) =>
  api<FileItem>(`/files/${fileId}`, { method: "DELETE" });

export async function updateFile(
  fileId: string,
  patch: { name?: string; folder?: string; tags?: string[] },
  signal?: AbortSignal,
): Promise<FileItem> {
  // These PATCH fields replace metadata, so transport-only retries are idempotent.
  for (let attempt = 0; ; attempt++) {
    throwIfAborted(signal);
    try {
      return await api<FileItem>(`/files/${fileId}`, {
        method: "PATCH",
        body: JSON.stringify(patch),
        signal,
      });
    } catch (error) {
      if (
        !(error instanceof ApiError) ||
        ![0, 408, 502, 503, 504].includes(error.status) ||
        attempt >= 2
      )
        throw error;
      await delay(150 * (attempt + 1), signal);
    }
  }
}

/** 原文件：pdf.js 需要带 JWT 直连，因此统一走 apiBlob 再转 objectURL。 */
export const fileBlob = (fileId: string, signal?: AbortSignal) =>
  apiBlob(`/files/${fileId}/content`, undefined, signal);

export const pageSizes = (fileId: string) =>
  api<
    { page_no: number; width_pt: number; height_pt: number; rotation: number }[]
  >(`/files/${fileId}/pages`);

/** 下拉选择等需要完整清单时使用有界分页；文件库本身使用服务端分页。 */
export const allFiles = (signal?: AbortSignal): Promise<FileItem[]> =>
  readAllPages(
    (offset) =>
      api<FileItem[]>(`/files?limit=100&offset=${offset}`, { signal }),
    signal,
  );
export interface FileQuery {
  items: (FileItem & { status: string; generation: number | null })[];
  total: number;
  status_available: boolean;
  effective_sort: string;
}
export const queryFiles = (
  params: Record<string, string>,
  signal?: AbortSignal,
) => api<FileQuery>(`/files/query?${new URLSearchParams(params)}`, { signal });
export const bulkFiles = (
  body: {
    file_ids: string[];
    action: "delete" | "move" | "tag";
    folder?: string;
    tags?: string[];
    append_tags?: boolean;
  },
  signal?: AbortSignal,
) =>
  api<{ items: { id: string; name: string; ok: boolean; message?: string }[] }>(
    "/files/bulk",
    { method: "POST", body: JSON.stringify(body), signal },
  ).catch((error) => {
    if (
      error instanceof ApiError &&
      error.status === 409 &&
      error.body &&
      Array.isArray((error.body as { items?: unknown }).items)
    )
      return error.body as {
        items: { id: string; name: string; ok: boolean; message?: string }[];
      };
    throw error;
  });
export const mergeFiles = (file_ids: string[], name: string) =>
  api<FileItem>("/files/merge", {
    method: "POST",
    body: JSON.stringify({ file_ids, name }),
  });
export const splitFile = (
  id: string,
  body: { name: string; groups?: number[][]; every?: number },
) =>
  api<FileItem[]>(`/files/${id}/split`, {
    method: "POST",
    body: JSON.stringify(body),
  });
export const restoreFile = (id: string) =>
  api<FileItem>(`/files/${id}/restore`, { method: "POST" });
export const purgeFile = (id: string) =>
  api<void>(`/files/${id}/purge`, { method: "DELETE" });

export async function validateUpload(file: File): Promise<void> {
  if (!file.size) throw new Error("文件为空，请重新选择。");
  if (file.size > 20 * 1024 * 1024)
    throw new Error("文件超过 20 MiB，请压缩或拆分后上传。");
  const extension = normalizeFilename(file.name)
    .split(".")
    .pop()
    ?.toLowerCase();
  const types: Record<string, string> = {
    pdf: "application/pdf",
    png: "image/png",
    jpg: "image/jpeg",
    jpeg: "image/jpeg",
  };
  if (!extension || !types[extension])
    throw new Error("仅支持 PDF、PNG、JPG 和 JPEG 文件。");
  if (
    file.type &&
    file.type !== "application/octet-stream" &&
    file.type !== types[extension]
  )
    throw new Error("扩展名与文件类型不一致。");
  const header = new Uint8Array(await file.slice(0, 1024).arrayBuffer());
  const isPdf = new TextDecoder().decode(header).includes("%PDF-");
  const isPng = [137, 80, 78, 71, 13, 10, 26, 10].every(
    (byte, i) => header[i] === byte,
  );
  const isJpeg = header[0] === 255 && header[1] === 216 && header[2] === 255;
  if (!(extension === "pdf" ? isPdf : extension === "png" ? isPng : isJpeg))
    throw new Error("文件内容与扩展名不符，可能已经损坏。");
  // 最终页数、加密与像素检查由后端执行，前端不取代内容校验。
}
