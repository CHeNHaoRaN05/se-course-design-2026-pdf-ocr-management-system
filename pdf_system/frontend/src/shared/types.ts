/** 跨模块共享的类型（负责人：甲维护；改动需走 PR）。 */
export interface FileItem {
  id: string;
  name: string;
  folder: string;
  media_type: string;
  size: number;
  page_count: number;
  version: number;
  tags: string[];
  created_at: string;
}

export interface OcrBlock {
  id: number;
  text: string;
  confidence: number;
  bbox: [number, number, number, number]; // 归一化左上原点（契约 C4）
  needs_review: boolean;
}

export interface OcrPageResult {
  page_no: number;
  status: "pending" | "succeeded" | "failed";
  revision: number;
  error: string | null;
  result: {
    width: number;
    height: number;
    blocks: OcrBlock[];
    text: string;
    tables: { id: number; strategy: string; cells: string[][] }[];
    corrected: boolean;
    warnings: string[];
  } | null;
}

export interface OcrJob {
  id: string;
  file_id: string;
  status: "queued" | "running" | "retry_wait" | "succeeded" | "partial_success" | "failed" | "cancelled";
  options: Record<string, unknown>;
  attempts: number;
  progress: { total: number; succeeded: number; failed: number; percent: number };
  pages: { page_no: number; status: string; error: string | null }[];
  created_at: string;
  finished_at: string | null;
}

export const TERMINAL = new Set(["succeeded", "partial_success", "failed", "cancelled"]);
