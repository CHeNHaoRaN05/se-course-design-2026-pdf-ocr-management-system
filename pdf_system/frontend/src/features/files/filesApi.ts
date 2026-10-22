import { api, apiBlob } from "../../shared/http";
import type { FileItem } from "../../shared/types";

export const listFiles = (params: Record<string, string> = {}) =>
  api<FileItem[]>("/files?" + new URLSearchParams(params));

export const uploadFile = (file: File) => {
  const body = new FormData();
  body.set("file", file);
  return api<FileItem>("/files", { method: "POST", body });
};

export const deleteFile = (fileId: string) => api<FileItem>(`/files/${fileId}`, { method: "DELETE" });

export const updateFile = (fileId: string, patch: { name?: string; folder?: string; tags?: string[] }) =>
  api<FileItem>(`/files/${fileId}`, { method: "PATCH", body: JSON.stringify(patch) });

/** 原文件：pdf.js 需要带 JWT 直连，因此统一走 apiBlob 再转 objectURL。 */
export const fileBlob = (fileId: string) => apiBlob(`/files/${fileId}/content`);

export const pageSizes = (fileId: string) =>
  api<{ page_no: number; width_pt: number; height_pt: number; rotation: number }[]>(`/files/${fileId}/pages`);
