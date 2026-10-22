/** PDF 阅读器（负责人：乙）。
 *  pdf.js 负责渲染与缩放/翻页；OCR 覆盖层由丙的 OcrOverlay 提供（契约 C4）。
 */
import { useEffect, useMemo, useRef, useState } from "react";
import { useParams, useSearchParams } from "react-router-dom";
import * as pdfjs from "pdfjs-dist";
import workerUrl from "pdfjs-dist/build/pdf.worker.min.mjs?url";
import { api, tokenStore } from "../../shared/http";
import type { FileItem, OcrBlock } from "../../shared/types";
import { latestJobOf } from "../ocr/ocrApi";
import OcrOverlay from "../ocr/OcrOverlay";
import OcrPanel from "../ocr/OcrPanel";

pdfjs.GlobalWorkerOptions.workerSrc = workerUrl;

export default function ReaderPage() {
  const { fileId = "" } = useParams();
  const [params, setParams] = useSearchParams();
  const [file, setFile] = useState<FileItem | null>(null);
  const [pageNo, setPageNo] = useState(Number(params.get("page") ?? 1));
  const [scale, setScale] = useState(1.2);
  const [size, setSize] = useState({ width: 0, height: 0 });
  const [blocks, setBlocks] = useState<OcrBlock[]>([]);
  const [activeId, setActiveId] = useState<number | undefined>();
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
      setSize({ width: viewport.width, height: viewport.height });
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
          <button onClick={() => setScale((s) => Math.max(0.5, s - 0.2))}>-</button>
          <button onClick={() => setScale((s) => Math.min(3, s + 0.2))}>+</button>
          <strong>{file?.name ?? "…"}</strong>
        </div>
        <div className="page-canvas-wrap" style={{ marginTop: 12 }}>
          <canvas ref={canvasRef} />
          {size.width > 0 && (
            <OcrOverlay blocks={blocks} width={size.width} height={size.height}
                        activeId={activeId} onPick={(b) => setActiveId(b.id)} />
          )}
        </div>
        <p className="muted">W7 待补：缩略图、页内搜索。</p>
      </div>
      <div style={{ flex: 1 }}>
        <OcrPanel jobId={jobId} onJobChange={setJobId}
                  onBlocks={setBlocks} onActive={setActiveId} />
      </div>
    </div>
  );
}
