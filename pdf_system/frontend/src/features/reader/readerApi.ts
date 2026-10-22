import { api } from "../../shared/http";

/** 书签与批注（负责人：乙）。payload.bbox 与 OCR bbox 同一口径（契约 C4）。 */
export interface Bookmark {
  id: string;
  page_no: number;
  title: string;
  created_at: string;
}

export interface Annotation {
  id: string;
  page_no: number;
  kind: "highlight" | "note" | "ink";
  payload: { text: string; bbox: [number, number, number, number] | null };
  created_at: string;
  updated_at: string;
}

const base = (fileId: string) => `/files/${fileId}/reader`;

export const listBookmarks = (fileId: string) => api<Bookmark[]>(`${base(fileId)}/bookmarks`);
export const addBookmark = (fileId: string, page_no: number, title = "") =>
  api<Bookmark>(`${base(fileId)}/bookmarks`, { method: "POST", body: JSON.stringify({ page_no, title }) });
export const removeBookmark = (fileId: string, id: string) =>
  api<void>(`${base(fileId)}/bookmarks/${id}`, { method: "DELETE" });

export const listAnnotations = (fileId: string, pageNo?: number) =>
  api<Annotation[]>(`${base(fileId)}/annotations${pageNo ? `?page_no=${pageNo}` : ""}`);
export const addAnnotation = (fileId: string, body: { page_no: number; kind?: string; text?: string; bbox?: number[] }) =>
  api<Annotation>(`${base(fileId)}/annotations`, { method: "POST", body: JSON.stringify(body) });
export const removeAnnotation = (fileId: string, id: string) =>
  api<void>(`${base(fileId)}/annotations/${id}`, { method: "DELETE" });
