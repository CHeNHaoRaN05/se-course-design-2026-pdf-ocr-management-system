import { api, apiBlob } from "../../shared/http";
import type { FileItem } from "../../shared/types";

export const listFiles = (params: Record<string, string> = {}) =>
  api<FileItem[]>("/files?" + new URLSearchParams(params));

export const uploadFile = (file: File) => {
  const body = new FormData();
  body.set("file", file);
  return api<FileItem>("/files", { method: "POST", body });
};

export const deleteFile = (fileId: string) =>
  api<FileItem>(`/files/${fileId}`, { method: "DELETE" });

export const updateFile = (
  fileId: string,
  patch: { name?: string; folder?: string; tags?: string[] },
) =>
  api<FileItem>(`/files/${fileId}`, {
    method: "PATCH",
    body: JSON.stringify(patch),
  });

/** 原文件：pdf.js 需要带 JWT 直连，因此统一走 apiBlob 再转 objectURL。 */
export const fileBlob = (fileId: string) => apiBlob(`/files/${fileId}/content`);

export const pageSizes = (fileId: string) =>
  api<
    { page_no: number; width_pt: number; height_pt: number; rotation: number }[]
  >(`/files/${fileId}/pages`);

/** 当前列表接口没有 total，逐页读取后统一筛选/排序，避免只排序当前页。 */
export async function allFiles(signal?: AbortSignal): Promise<FileItem[]> {
  const result: FileItem[] = [];
  for (let offset = 0; ; offset += 100) {
    const page = await api<FileItem[]>(`/files?limit=100&offset=${offset}`, {
      signal,
    });
    result.push(...page);
    if (page.length < 100)
      return [...new Map(result.map((file) => [file.id, file])).values()];
  }
}
export const restoreFile = (id: string) =>
  api<FileItem>(`/files/${id}/restore`, { method: "POST" });
export const purgeFile = (id: string) =>
  api<void>(`/files/${id}/purge`, { method: "DELETE" });

export async function validateUpload(file: File): Promise<void> {
  if (!file.size) throw new Error("文件为空，请重新选择。");
  if (file.size > 20 * 1024 * 1024)
    throw new Error("文件超过 20 MiB，请压缩或拆分后上传。");
  const extension = file.name.split(".").pop()?.toLowerCase();
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
