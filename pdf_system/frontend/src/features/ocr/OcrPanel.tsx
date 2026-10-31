/** OCR task controls, page-aware proofreading and exports (line 03). */
import { useEffect, useRef, useState } from "react";
import { useParams, useSearchParams } from "react-router-dom";
import { useAuth } from "../../app/AuthProvider";
import { ApiError, api, downloadBlob } from "../../shared/http";
import { TERMINAL, type OcrBlock, type OcrJob, type OcrPageResult } from "../../shared/types";
import { cancelOcrJob, correctPage, exportJob, getOcrJob, listPages, settleJob, startOcrJob } from "./ocrApi";
import { parsePageRange } from "./pageRange";

interface Props {
  jobId: string | null; onJobChange: (jobId: string) => void;
  onBlocks: (blocks: OcrBlock[]) => void; onActive: (id: number | undefined) => void;
}
interface Draft { revision: number; blocks: OcrBlock[] }
type Format = "txt" | "json" | "csv" | "html" | "xlsx";

export default function OcrPanel({ jobId, onJobChange, onBlocks, onActive }: Props) {
  const { me } = useAuth();
  const { fileId = "" } = useParams();
  const [params] = useSearchParams();
  const pageNo = Number(params.get("page") ?? 1);
  const [job, setJob] = useState<OcrJob | null>(null);
  const [pages, setPages] = useState<OcrPageResult[]>([]);
  const [draft, setDraft] = useState<Record<number, Draft>>({});
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [refresh, setRefresh] = useState(0);
  const [range, setRange] = useState("");
  const [tables, setTables] = useState(true);
  const [format, setFormat] = useState<Format>("xlsx");
  const [exportRange, setExportRange] = useState("");
  const [partial, setPartial] = useState(false);
  const [coordinates, setCoordinates] = useState(true);
  const [fileName, setFileName] = useState("ocr");
  const settled = useRef(new Set<string>());
  const identity = useRef(jobId);
  identity.current = jobId;
  const editor = !!me && me.role !== "viewer";
  const active = !!job && !TERMINAL.has(job.status);

  useEffect(() => {
    const controller = new AbortController();
    setFileName("ocr");
    if (fileId) void api<{ name: string }>(`/files/${fileId}`, { signal: controller.signal })
      .then((file) => { if (!controller.signal.aborted) setFileName(file.name); }).catch(() => undefined);
    return () => controller.abort();
  }, [fileId]);
  useEffect(() => {
    setJob(null); setPages([]); setDraft({}); setError(""); setBusy(false);
  }, [jobId]);
  useEffect(() => {
    if (!jobId) return;
    let stopped = false;
    let timer = 0;
    async function tick() {
      let next: OcrJob | null = null;
      try {
        const [nextJob, nextPages] = await Promise.all([getOcrJob(jobId!), listPages(jobId!)]);
        if (stopped) return;
        next = nextJob; setJob(nextJob); setPages(nextPages);
        if (editor && TERMINAL.has(nextJob.status) && !settled.current.has(jobId!)) {
          await settleJob(jobId!);
          if (!stopped) settled.current.add(jobId!);
        }
      } catch (e) {
        if (!stopped) setError(e instanceof Error ? e.message : "查询任务失败");
      }
      if (!stopped && (!next || !TERMINAL.has(next.status))) timer = window.setTimeout(tick, 1500);
    }
    void tick();
    return () => { stopped = true; window.clearTimeout(timer); };
  }, [jobId, refresh, editor]);
  const page = pages.find((item) => item.page_no === pageNo);
  useEffect(() => {
    onBlocks(page?.result?.blocks ?? []); onActive(undefined);
  }, [page, onBlocks, onActive]);

  async function action(operation: () => Promise<unknown>) {
    const captured = jobId;
    setBusy(true); setError("");
    try { await operation(); }
    catch (e) {
      if (identity.current === captured) setError(e instanceof Error ? e.message : "操作失败");
    } finally { if (identity.current === captured) setBusy(false); }
  }
  async function save() {
    if (!page?.result || !jobId) return;
    const captured = jobId;
    const edit = draft[page.page_no] ?? { revision: page.revision, blocks: page.result.blocks };
    await action(async () => {
      try {
        const updated = await correctPage(captured, page.page_no, edit.revision, edit.blocks);
        if (identity.current !== captured) return;
        setPages((previous) => previous.map((item) => item.page_no === page.page_no ? updated : item));
        setDraft((previous) => { const next = { ...previous }; delete next[page.page_no]; return next; });
      } catch (e) {
        if (e instanceof ApiError && e.status === 409) {
          throw new Error("校对冲突：原草稿已保留。请复制需保留的内容，再点“放弃本页草稿并重载”获取最新版本后合并。");
        }
        throw e;
      }
    });
  }
  async function create() {
    const captured = jobId;
    await action(async () => {
      const created = await startOcrJob({ file_id: fileId, pages: parsePageRange(range), tables });
      if (identity.current === captured) onJobChange(created.id);
    });
  }
  async function exportResult() {
    if (!jobId) return;
    await action(async () => {
      const blob = await exportJob(jobId, format, partial, parsePageRange(exportRange), coordinates);
      const stem = fileName.replace(/\.[^.]+$/, "").replace(/[\\/:*?"<>|]/g, "_").slice(0, 100) || "ocr";
      downloadBlob(blob, `${stem}-${new Date().toISOString().replace(/[:.]/g, "-")}.${format}`);
    });
  }
  return <div className="card">
    <h3>OCR 识别与校对</h3>
    {editor && <div>
      <label>识别页码<input placeholder="留空为全部，例如 1-3,5" value={range} onChange={(e) => setRange(e.target.value)} disabled={busy || active} /></label>
      <label><input type="checkbox" checked={tables} onChange={(e) => setTables(e.target.checked)} />还原线框表格</label>
      <button disabled={busy || active || !fileId || (!!jobId && !job)} onClick={() => void create()}>{jobId ? "新建识别任务" : "开始识别"}</button>
    </div>}
    {!jobId && <p className="muted">该文件尚无识别任务。</p>}
    {jobId && <>
      <div className="row" style={{ flexWrap: "wrap", marginTop: 12 }}>
        <strong>任务 {job?.status ?? "加载中…"}</strong>
        <span className="muted">进度 {job?.progress.percent ?? 0}% · 尝试 {job?.attempts ?? 0} 次</span>
        {editor && active && <button disabled={busy} onClick={() => void action(async () => {
          await cancelOcrJob(jobId); setRefresh((value) => value + 1);
        })}>取消任务</button>}
        {editor && job && ["failed", "partial_success"].includes(job.status) && <button disabled={busy}
          onClick={() => void action(async () => {
            // C3 closes quota once per job ID. A fresh job gives the retry its own
            // reservation/settlement; successful pages keep their existing index.
            const captured = jobId;
            await settleJob(captured);
            const failed = job.pages.filter((item) => item.status !== "succeeded").map((item) => item.page_no);
            if (!failed.length) throw new Error("没有需要重试的失败页");
            const created = await startOcrJob({ ...job.options, file_id: job.file_id, pages: failed });
            if (identity.current === captured) onJobChange(created.id);
          })}>重试失败页</button>}
        <button disabled={busy} onClick={() => { setError(""); setRefresh((value) => value + 1); }}>刷新状态</button>
      </div>
      <details style={{ margin: "12px 0" }}><summary>导出识别结果</summary>
        <label>格式<select aria-label="导出格式" value={format} onChange={(e) => setFormat(e.target.value as Format)}>
          {["txt", "json", "csv", "html", "xlsx"].map((item) => <option key={item} value={item}>{item.toUpperCase()}</option>)}
        </select></label>
        <label>导出页码<input placeholder="留空为全部，例如 1-3,5" value={exportRange} onChange={(e) => setExportRange(e.target.value)} /></label>
        <label><input type="checkbox" checked={partial} onChange={(e) => setPartial(e.target.checked)} />允许仅导出成功页</label>
        <label><input type="checkbox" checked={coordinates} onChange={(e) => setCoordinates(e.target.checked)} />包含坐标（JSON/CSV/XLSX）</label>
        <button disabled={busy || !pages.some((item) => item.status === "succeeded")} onClick={() => void exportResult()}>下载结果</button>
      </details>
      <h4>当前第 {pageNo} 页</h4>
      {!page && <p className="muted">当前页不在此任务中，或结果尚未加载。请通过阅读器翻页查看。</p>}
      {page && <>
        <p className="muted">状态 {page.status} · 修订号 {page.revision}{page.error ? ` · ${page.error}` : ""}</p>
        {editor && page.result && <div className="row">
          <button disabled={busy || active} onClick={() => void save()}>保存校对</button>
          <button disabled={busy} onClick={() => {
            setDraft((previous) => { const next = { ...previous }; delete next[pageNo]; return next; });
            setError(""); setRefresh((value) => value + 1);
          }}>放弃本页草稿并重载</button>
        </div>}
        {(draft[pageNo]?.blocks ?? page.result?.blocks ?? []).map((block, index) =>
          <div key={block.id} className="row" style={{ marginTop: 8 }}>
            <span className="muted">#{block.id}</span>
            <input aria-label={`识别框 ${block.id}`} style={{ flex: 1, minWidth: 0 }} value={block.text}
              readOnly={!editor || active || busy} onFocus={() => onActive(block.id)}
              onChange={(e) => {
                const previous = draft[pageNo] ?? { revision: page.revision, blocks: page.result!.blocks };
                const blocks = [...previous.blocks]; blocks[index] = { ...block, text: e.target.value, needs_review: false };
                setDraft((all) => ({ ...all, [pageNo]: { revision: previous.revision, blocks } }));
              }} />
            <span className={block.needs_review ? "error" : "muted"}>{block.confidence.toFixed(2)}{block.needs_review ? " 待复核" : ""}</span>
          </div>)}
        {page.result?.warnings?.map((warning, i) => <p className="muted" key={i}>{warning}</p>)}
        {!!page.result?.tables.length && <p className="muted">修改对应识别框并保存后，单元格文本会同步更新。</p>}
        {page.result?.tables.map((table) => <div key={table.id} style={{ overflowX: "auto", marginTop: 12 }}>
          <strong>表格 {table.id}（已保存版本）</strong>
          <table><tbody>{table.cells.map((row, r) => <tr key={r}>{row.map((cell, c) =>
            <td key={c} style={{ border: "1px solid #ddd", padding: 6, whiteSpace: "pre-wrap" }}>{cell}</td>)}</tr>)}</tbody></table>
        </div>)}
      </>}
    </>}
    {error && <p className="error" role="alert">{error}</p>}
  </div>;
}
