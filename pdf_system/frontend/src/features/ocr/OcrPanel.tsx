/** OCR tasks, read-only page results and exports. */
import { useEffect, useRef, useState } from "react";
import { useParams, useSearchParams } from "react-router-dom";
import { useAuth } from "../../app/AuthProvider";
import { throwIfAborted, isCancellation } from "../../shared/requests";
import { ApiError, api, downloadBlob } from "../../shared/http";
import { TERMINAL, type OcrJob, type OcrPageResult } from "../../shared/types";
import { cancelOcrJob, exportJob, getOcrJob, listPages, settleJob, startOcrJob } from "./ocrApi";
import { parsePageRange } from "./pageRange";

interface Props {
  jobId: string | null; onJobChange: (jobId: string) => void;
}
type Format = "txt" | "json" | "csv" | "html" | "xlsx";

export default function OcrPanel({ jobId, onJobChange }: Props) {
  const { me } = useAuth();
  const { fileId = "" } = useParams();
  const [params] = useSearchParams();
  const pageNo = Number(params.get("page") ?? 1);
  const [job, setJob] = useState<OcrJob | null>(null);
  const [pages, setPages] = useState<OcrPageResult[]>([]);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [refresh, setRefresh] = useState(0);
  const [range, setRange] = useState("");
  const [format, setFormat] = useState<Format>("xlsx");
  const [partial, setPartial] = useState(false);
  const [coordinates, setCoordinates] = useState(true);
  const [fileName, setFileName] = useState("ocr");
  const settled = useRef(new Set<string>());
  const manual = useRef(new AbortController());
  useEffect(()=>{manual.current=new AbortController();return()=>manual.current.abort();},[fileId,jobId]);
  const identity = useRef(jobId);
  identity.current = jobId;
  const editor = !!me && me.role !== "viewer";
  const active = !!jobId && (!job || !TERMINAL.has(job.status));

  useEffect(() => {
    const controller = new AbortController();
    setFileName("ocr");
    if (fileId) void api<{ name: string }>(`/files/${fileId}`, { signal: controller.signal })
      .then((file) => { if (!controller.signal.aborted) setFileName(file.name); }).catch(() => undefined);
    return () => controller.abort();
  }, [fileId]);
  useEffect(() => {
    setJob(null); setPages([]); setError(""); setBusy(false);
  }, [jobId]);
  useEffect(() => {
    if (!jobId) return;
    let stopped = false;
    let failures = 0;
    const controller = new AbortController();
    let timer = 0;
    async function tick() {
      let next: OcrJob | null = null;
      try {
        const [nextJob, nextPages] = await Promise.all([getOcrJob(jobId!, controller.signal), listPages(jobId!, controller.signal)]);
        if (stopped) return;
        setError("");
        next = nextJob; setJob(nextJob); setPages(nextPages);
        if (TERMINAL.has(nextJob.status) && !settled.current.has(jobId!)) {
          await settleJob(jobId!, controller.signal);
          if (!stopped) settled.current.add(jobId!);
        }
        failures = 0;
      } catch (e) {
        if (stopped) return;
        failures++;
        const fatal = e instanceof ApiError && [401,403,404].includes(e.status);
        setError(`${e instanceof Error ? e.message : "查询任务失败"}${failures >= 3 || fatal ? "；已停止自动重试，请手动刷新状态。" : ""}`);
        if (failures >= 3 || fatal) return;
      }
      if (!stopped && (!next || !TERMINAL.has(next.status) || !settled.current.has(jobId!))) timer = window.setTimeout(tick, 1500);
    }
    void tick();
    return () => { stopped = true; controller.abort(); window.clearTimeout(timer); };
  }, [jobId, refresh, editor]);
  const page = pages.find((item) => item.page_no === pageNo);
  async function action(operation: (signal:AbortSignal) => Promise<unknown>) {
    const captured = jobId;
    const signal=manual.current.signal;
    setBusy(true); setError("");
    try { throwIfAborted(signal); await operation(signal); }
    catch (e) {
      if (!signal.aborted && !isCancellation(e) && identity.current === captured) setError(e instanceof Error ? e.message : "操作失败");
    } finally { if (!signal.aborted && identity.current === captured) setBusy(false); }
  }
  async function create() {
    const captured = jobId;
    await action(async (signal) => {
      const created = await startOcrJob({ file_id: fileId, pages: parsePageRange(range), tables: false }, signal);
      if (!signal.aborted && identity.current === captured) onJobChange(created.id);
    });
  }
  async function exportResult() {
    if (!jobId) return;
    await action(async (signal) => {
      const blob = await exportJob(jobId, format, partial, undefined, coordinates, signal);
      const stem = fileName.replace(/\.[^.]+$/, "").replace(/[\\/:*?"<>|]/g, "_").slice(0, 100) || "ocr";
      downloadBlob(blob, `${stem}-${new Date().toISOString().replace(/[:.]/g, "-")}.${format}`);
    });
  }
  return <div className="card">
    <h3>OCR 识别</h3>
    {editor && <div>
      <label>识别页码<input placeholder="留空为全部，例如 1-3,5" value={range} onChange={(e) => setRange(e.target.value)} disabled={busy || active} /></label>
      <button disabled={busy || active || !fileId || (!!jobId && !job)} onClick={() => void create()}>{jobId ? "新建识别任务" : "开始识别"}</button>
    </div>}
    {!jobId && <p className="muted">该文件尚无识别任务。</p>}
    {jobId && <>
      <div className="row" style={{ flexWrap: "wrap", marginTop: 12 }}>
        <strong>任务 {job?.status ?? "加载中…"}</strong>
        <span className="muted">进度 {job?.progress.percent ?? 0}% · 尝试 {job?.attempts ?? 0} 次</span>
        {editor && active && <button disabled={busy} onClick={() => void action(async (signal) => {
          await cancelOcrJob(jobId,signal); setRefresh((value) => value + 1);
        })}>取消任务</button>}
        {editor && job && ["failed", "partial_success"].includes(job.status) && <button disabled={busy}
          onClick={() => void action(async (signal) => {
            // C3 closes quota once per job ID. A fresh job gives the retry its own
            // reservation/settlement; successful pages keep their existing index.
            const captured = jobId;
            await settleJob(captured,signal);
            const failed = job.pages.filter((item) => item.status !== "succeeded").map((item) => item.page_no);
            if (!failed.length) throw new Error("没有需要重试的失败页");
            const created = await startOcrJob({ file_id: job.file_id, pages: failed, tables: false },signal);
            if (!signal.aborted && identity.current === captured) onJobChange(created.id);
          })}>重试失败页</button>}
        <button disabled={busy} onClick={() => { setError(""); setRefresh((value) => value + 1); }}>刷新状态</button>
      </div>
      <details style={{ margin: "12px 0" }}><summary>导出识别结果</summary>
        <label>格式<select aria-label="导出格式" value={format} onChange={(e) => setFormat(e.target.value as Format)}>
          {["txt", "json", "csv", "html", "xlsx"].map((item) => <option key={item} value={item}>{item.toUpperCase()}</option>)}
        </select></label>
        <label><input type="checkbox" checked={partial} onChange={(e) => setPartial(e.target.checked)} />允许仅导出成功页</label>
        <label><input type="checkbox" checked={coordinates} onChange={(e) => setCoordinates(e.target.checked)} />包含坐标（JSON/CSV/XLSX）</label>
        <button disabled={busy || !pages.some((item) => item.status === "succeeded")} onClick={() => void exportResult()}>下载结果</button>
      </details>
      <h4>当前第 {pageNo} 页</h4>
      {!page && <p className="muted">当前页不在此任务中，或结果尚未加载。请通过阅读器翻页查看。</p>}
      {page && <>
        <p className="muted">状态 {page.status} · 修订号 {page.revision}{page.error ? ` · ${page.error}` : ""}</p>
        {page.result && <p style={{ whiteSpace: "pre-wrap" }}>{page.result.text}</p>}
      </>}
    </>}
    {error && <p className="error" role="alert">{error}</p>}
  </div>;
}
