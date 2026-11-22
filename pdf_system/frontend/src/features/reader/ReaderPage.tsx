/** PDF 阅读、翻页与缩放。 */
import { useEffect, useMemo, useRef, useState } from "react";
import { useParams, useSearchParams } from "react-router-dom";
import * as pdfjs from "pdfjs-dist";
import workerUrl from "pdfjs-dist/build/pdf.worker.min.mjs?url";
import { api, tokenStore } from "../../shared/http";
import type { FileItem } from "../../shared/types";
import { latestJobOf } from "../ocr/ocrApi";
import OcrPanel from "../ocr/OcrPanel";
import ReaderNotes from "./ReaderNotes";

pdfjs.GlobalWorkerOptions.workerSrc = workerUrl;

export default function ReaderPage() {
  const { fileId = "" } = useParams();
  const [params, setParams] = useSearchParams();
  const [file, setFile] = useState<FileItem | null>(null);
  const [pageNo, setPageNo] = useState(Number(params.get("page") ?? 1));
  const [scale, setScale] = useState(1.2);
  const [jobId, setJobId] = useState<string | null>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => { void api<FileItem>(`/files/${fileId}`).then(setFile); }, [fileId]);
  useEffect(() => { void latestJobOf(fileId).then((r) => setJobId(r.job_id)); }, [fileId]);

  useEffect(() => {
    if (!file || file.media_type !== "application/pdf") return;
    let cancelled = false;
    (async () => {
      // pdf.js 直连后端原文件，必须携带 JWT
      const doc = await pdfjs.getDocument({
        url: `/api/v1/files/${fileId}/content`,
        httpHeaders: { Authorization: `Bearer ${tokenStore.get()}` },
      }).promise;
      if (cancelled) return;
      const page = await doc.getPage(pageNo);
      const viewport = page.getViewport({ scale });
      const canvas = canvasRef.current;
      if (!canvas) return;
      canvas.width = Math.floor(viewport.width);
      canvas.height = Math.floor(viewport.height);
      await page.render({ canvasContext: canvas.getContext("2d")!, viewport }).promise;
    })().catch(() => undefined);
    return () => { cancelled = true; };
  }, [file, fileId, pageNo, scale]);

  const maxPage = useMemo(() => file?.page_count ?? 1, [file]);

  function goto(next: number) {
    const clamped = Math.min(Math.max(1, next), maxPage);
    setPageNo(clamped);
    setParams({ page: String(clamped) });
  }

  return (
    <div className="row" style={{ alignItems: "flex-start" }}>
      <div className="card" style={{ flex: 2 }}>
        <div className="row">
          <button disabled={pageNo <= 1} onClick={() => goto(pageNo - 1)}>上一页</button>
          <span>{pageNo} / {maxPage}</span>
          <button disabled={pageNo >= maxPage} onClick={() => goto(pageNo + 1)}>下一页</button>
          <form onSubmit={(event) => {
            event.preventDefault();
            goto(Number(new FormData(event.currentTarget).get("page")));
          }}>
            <input key={pageNo} name="page" type="number" aria-label="跳转页码"
              defaultValue={pageNo} min={1} max={maxPage} required style={{ width: "5em" }} />
            <button type="submit">跳转</button>
          </form>
          <button onClick={() => setScale((s) => Math.max(0.5, s - 0.2))}>-</button>
          <button onClick={() => setScale((s) => Math.min(3, s + 0.2))}>+</button>
          <strong>{file?.name ?? "…"}</strong>
        </div>
        <div className="page-canvas-wrap" style={{ marginTop: 12 }}>
          <canvas ref={canvasRef} />
        </div>
      </div>
      <div style={{ flex: 1 }}>
        <OcrPanel jobId={jobId} onJobChange={setJobId} />
        {file && <ReaderNotes key={fileId} fileId={fileId} pageNo={pageNo} onPageChange={goto} />}
      </div>
    </div>
  );
}
