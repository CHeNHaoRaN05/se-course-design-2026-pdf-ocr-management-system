/** OCR 接口封装（负责人：丙）。
 *  /api/v1/ocr/*      —— OCR 模块原生接口（识别、校对、导出、检索）
 *  /api/v1/ocr-host/* —— 主系统补齐的宿主侧接口（能力、配额结算、统计）
 */
import { api, apiBlob } from "../../shared/http";
import type { OcrJob, OcrPageResult } from "../../shared/types";

export interface JobCreateBody {
  file_id: string;
  pages?: number[];
  mode?: "general" | "handwriting";
  recognition_model?: "official" | "custom";
  dpi?: number;
  tables?: boolean;
  min_confidence?: number;
}

export const ocrCapabilities = () => api<Record<string, unknown>>("/ocr/capabilities");
export const hostCapabilities = () => api<Record<string, unknown>>("/ocr-host/capabilities");

export const startOcrJob = (body: JobCreateBody) => api<OcrJob>("/ocr/jobs", { method: "POST", body: JSON.stringify(body) });
export const getOcrJob = (jobId: string) => api<OcrJob>(`/ocr/jobs/${jobId}`);
export const cancelOcrJob = (jobId: string) => api<OcrJob>(`/ocr/jobs/${jobId}/cancel`, { method: "POST" });
export const retryOcrJob = (jobId: string) => api<OcrJob>(`/ocr/jobs/${jobId}/retry`, { method: "POST" });
export const latestJobOf = (fileId: string) => api<{ job_id: string | null; status: string | null }>(`/ocr-host/files/${fileId}/jobs`);

export const listPages = (jobId: string) => api<OcrPageResult[]>(`/ocr/jobs/${jobId}/pages`);

export const correctPage = (jobId: string, pageNo: number, expectedRevision: number, blocks: unknown[]) =>
  api<OcrPageResult>(`/ocr/jobs/${jobId}/pages/${pageNo}`, {
    method: "PATCH",
    body: JSON.stringify({ expected_revision: expectedRevision, blocks }),
  });

export const exportJob = (jobId: string, format: "txt" | "json" | "csv" | "html" | "xlsx",
  allowPartial = false, pages?: number[], includeCoordinates = true) => {
  const params = new URLSearchParams({ format, allow_partial: String(allowPartial), include_coordinates: String(includeCoordinates) });
  pages?.forEach((page) => params.append("pages", String(page)));
  return apiBlob(`/ocr/jobs/${jobId}/export?${params}`);
};

/** 任务终态后调用，成功页计费、失败页退额度（幂等）。 */
export const settleJob = (jobId: string) => api<Record<string, unknown>>(`/ocr-host/jobs/${jobId}/settle`, { method: "POST" });
