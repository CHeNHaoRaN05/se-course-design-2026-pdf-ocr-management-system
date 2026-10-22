/** OCR 结果面板：轮询 → 校对 → 导出 → 结算（负责人：丙）。 */
import { useCallback, useEffect, useRef, useState } from "react";
import { useAuth } from "../../app/AuthProvider";
import { downloadBlob } from "../../shared/http";
import { TERMINAL, type OcrBlock, type OcrJob, type OcrPageResult } from "../../shared/types";
import { cancelOcrJob, correctPage, exportJob, getOcrJob, listPages, settleJob } from "./ocrApi";

interface Props {
  jobId: string | null;
  onJobChange: (jobId: string) => void;
  onBlocks: (blocks: OcrBlock[]) => void;
  onActive: (id: number | undefined) => void;
}

export default function OcrPanel({ jobId, onJobChange, onBlocks, onActive }: Props) {
  const { me } = useAuth();
  const [job, setJob] = useState<OcrJob | null>(null);
  const [pages, setPages] = useState<OcrPageResult[]>([]);
  const [error, setError] = useState("");
  const [draft, setDraft] = useState<Record<number, OcrBlock[]>>({});
  const settled = useRef<string | null>(null);

  const refresh = useCallback(async () => {
    if (!jobId) return;
    const [nextJob, nextPages] = await Promise.all([getOcrJob(jobId), listPages(jobId)]);
    setJob(nextJob);
    setPages(nextPages);
    const first = nextPages.find((page) => page.status === "succeeded" && page.result);
    if (first?.result) onBlocks(first.result.blocks);
    // 终态后结算一次配额（后端幂等）
    if (TERMINAL.has(nextJob.status) && settled.current !== jobId) {
      settled.current = jobId;
      await settleJob(jobId).catch(() => undefined);
    }
  }, [jobId, onBlocks]);

  useEffect(() => {
    if (!jobId) return;
    let timer = 0;
    let stop = false;
    const tick = async () => {
      try {
        await refresh();
      } catch (e) {
        setError(e instanceof Error ? e.message : "查询任务失败");
      }
      const current = await getOcrJob(jobId).catch(() => null);
      if (!stop && current && !TERMINAL.has(current.status)) timer = window.setTimeout(tick, 1500);
    };
    void tick();
    return () => { stop = true; window.clearTimeout(timer); };
  }, [jobId, refresh]);

  async function onExport(format: "txt" | "json" | "csv" | "html" | "xlsx") {
    if (!jobId) return;
    try {
      const blob = await exportJob(jobId, format, true);
      downloadBlob(blob, `ocr-${jobId}.${format}`);
    } catch (e) {
      setError(e instanceof Error ? e.message : "导出失败");
    }
  }

  async function onSave(page: OcrPageResult) {
    if (!jobId || !page.result) return;
    const blocks = draft[page.page_no] ?? page.result.blocks;
    try {
      const updated = await correctPage(jobId, page.page_no, page.revision, blocks);
      setDraft((prev) => ({ ...prev, [page.page_no]: updated.result?.blocks ?? [] }));
      await refresh();
      setError("");
    } catch (e) {
      // 409：版本冲突或页面已被新任务替代，必须重新读取后由用户合并
      setError(e instanceof Error && e.message.includes("409")
        ? "结果已被更新（409），请刷新后重新合并修改"
        : e instanceof Error ? e.message : "保存失败");
    }
  }

  if (!jobId) return <p className="muted">该文件尚无识别任务。</p>;

  return (
    <div className="card">
      <div className="row">
        <strong>任务 {job?.status ?? "…"}</strong>
        <span className="muted">进度 {job?.progress.percent ?? 0}% · 尝试 {job?.attempts ?? 0} 次</span>
        {me?.role !== "viewer" && job && !TERMINAL.has(job.status) && (
          <button onClick={() => cancelOcrJob(jobId).then(() => onJobChange(jobId))}>取消</button>
        )}
        <select defaultValue="xlsx" onChange={(e) => onExport(e.target.value as "xlsx")}>
          <option value="">导出为…</option>
          <option value="txt">TXT</option>
          <option value="json">JSON</option>
          <option value="csv">CSV</option>
          <option value="html">HTML</option>
          <option value="xlsx">XLSX</option>
        </select>
      </div>
      {error && <p className="error">{error}</p>}
      {pages.map((page) => (
        <div key={page.page_no} className="card">
          <div className="row">
            <strong>第 {page.page_no} 页</strong>
            <span className="muted">修订号 {page.revision}{page.status === "failed" ? ` · ${page.error}` : ""}</span>
            {me?.role !== "viewer" && page.status === "succeeded" && (
              <button onClick={() => onSave(page)}>保存校对</button>
            )}
          </div>
          {(draft[page.page_no] ?? page.result?.blocks ?? []).map((block, index) => (
            <div key={block.id} className="row" style={{ marginBottom: 4 }}>
              <span className="muted">#{block.id}</span>
              <input
                style={{ flex: 1 }}
                value={block.text}
                onChange={(e) => {
                  const blocks = [...(draft[page.page_no] ?? page.result?.blocks ?? [])];
                  blocks[index] = { ...block, text: e.target.value };
                  setDraft((prev) => ({ ...prev, [page.page_no]: blocks }));
                }}
                onFocus={() => onActive(block.id)}
              />
              <span className="muted">{block.confidence.toFixed(2)}</span>
              {block.needs_review && <span className="error">待复核</span>}
            </div>
          ))}
        </div>
      ))}
    </div>
  );
}
