import { throwIfAborted, isCancellation } from "../../shared/requests";
import { filesChanged } from "../management/fileEvents";
import { useRef, useState, useEffect } from "react";
import { Link } from "react-router-dom";
import { useAuth } from "../../app/AuthProvider";
import { Icon, Notice, PageHeading, FileGlyph } from "../management/ui";
import {
  errorText,
  formatBytes,
  normalizeFolder,
  parseTags,
  uniqueFilename,
} from "../management/management";
import { allFiles, updateFile, uploadFile, validateUpload } from "./filesApi";

interface UploadRow {
  id: number;
  file: File;
  state: "pending" | "uploading" | "success" | "error";
  message?: string;
  fileId?: string;
}
export default function UploadPage() {
  const { me } = useAuth();
  const input = useRef<HTMLInputElement>(null);
  const sequence = useRef(0);
  const controller = useRef(new AbortController());
  useEffect(() => {
    controller.current = new AbortController();
    return () => controller.current.abort();
  }, []);
  const [rows, setRows] = useState<UploadRow[]>([]);
  const [folder, setFolder] = useState("/");
  const [tags, setTags] = useState("");
  const [busy, setBusy] = useState(false);
  const [dragging, setDragging] = useState(false);
  const [error, setError] = useState("");
  const editor = me?.role !== "viewer";
  const pending = rows.filter(
    (row) => row.state === "pending" || row.state === "error",
  );
  const succeeded = rows.filter((row) => row.state === "success").length;
  const failed = rows.filter((row) => row.state === "error").length;
  function add(files: FileList | File[]) {
    if (!editor || busy) return;
    const incoming = Array.from(files).map((file) => ({
      id: ++sequence.current,
      file,
      state: "pending" as const,
    }));
    setRows((previous) => [...previous, ...incoming]);
    setError("");
  }
  function patch(id: number, fields: Partial<UploadRow>) {
    setRows((previous) =>
      previous.map((row) => (row.id === id ? { ...row, ...fields } : row)),
    );
  }
  async function start() {
    if (busy || !editor) return;
    setError("");
    let path: string;
    let labels: string[];
    try {
      path = normalizeFolder(folder);
      labels = parseTags(tags);
    } catch (e) {
      setError(errorText(e));
      return;
    }
    setBusy(true);
    try {
      const names = new Set(
        (await allFiles(controller.current.signal)).map((file) => file.name),
      );
      for (const row of pending) {
        throwIfAborted(controller.current.signal);
        patch(row.id, { state: "uploading", message: "正在校验并上传…" });
        try {
          let uploadedId = row.fileId;
          if (!uploadedId) {
            await validateUpload(row.file);
            const name = uniqueFilename(row.file.name, names);
            const upload = await uploadFile(
              new File([row.file], name, { type: row.file.type }),
              controller.current.signal,
            );
            uploadedId = upload.id;
            names.add(name);
            patch(row.id, { fileId: uploadedId });
          }
          if (row.fileId || path !== "/" || labels.length)
            await updateFile(
              uploadedId,
              { folder: path, tags: labels },
              controller.current.signal,
            );
          patch(row.id, {
            state: "success",
            message: "已加入文件库",
            fileId: uploadedId,
          });
        } catch (e) {
          if (isCancellation(e)) throw e;
          patch(row.id, { state: "error", message: errorText(e) });
        }
      }
      filesChanged();
    } catch (e) {
      if (!isCancellation(e)) setError(errorText(e));
    } finally {
      setBusy(false);
    }
  }
  return (
    <div className="workspace-page">
      <PageHeading
        eyebrow="DOCUMENT IMPORT"
        title="上传文档"
        description="将资料放入你的文档空间，分类归档，随时查找。"
        actions={
          <Link className="button" to="/files">
            <Icon name="folder" />
            返回文件库
          </Link>
        }
      />
      {error && <Notice tone="error">{error}</Notice>}
      <div className="upload-layout">
        <section className="panel">
          <div className="panel-heading">
            <h2>选择文件</h2>
            <span className="muted">支持多文件上传</span>
          </div>
          <div className="panel-body">
            <input
              ref={input}
              type="file"
              multiple
              accept=".pdf,.png,.jpg,.jpeg"
              className="visually-hidden"
              tabIndex={-1}
              onChange={(e) => {
                if (e.target.files) add(e.target.files);
                e.target.value = "";
              }}
            />
            <button
              type="button"
              disabled={busy || !editor}
              className={`drop-zone ${dragging ? "dragging" : ""}`}
              onClick={() => input.current?.click()}
              onDragOver={(e) => {
                e.preventDefault();
                if (editor && !busy) setDragging(true);
              }}
              onDragLeave={() => setDragging(false)}
              onDrop={(e) => {
                e.preventDefault();
                setDragging(false);
                add(e.dataTransfer.files);
              }}
            >
              <span className="drop-icon">
                <Icon name="upload" size={30} />
              </span>
              <strong>拖拽文件至此，或点击选择</strong>
              <span>PDF、PNG、JPG / JPEG</span>
              <small>每个文件不超过 20 MiB · 每份 PDF 不超过 100 页</small>
            </button>
            <div className="queue-heading">
              <strong>
                上传队列 <span className="count-badge">{rows.length}</span>
              </strong>
              <button
                className="text-button"
                disabled={busy || !rows.length}
                onClick={() => setRows([])}
              >
                清空队列
              </button>
            </div>
            {!rows.length && (
              <p className="queue-placeholder">
                选择文件后，在这里查看上传进度与结果。
              </p>
            )}
            <ul className="upload-queue">
              {rows.map((row) => (
                <li key={row.id}>
                  <FileGlyph type={row.file.type} />
                  <div className="queue-info">
                    <strong>{row.file.name}</strong>
                    <span className={row.state === "error" ? "error" : "muted"}>
                      {row.message ?? formatBytes(row.file.size)}
                    </span>
                    {row.state === "error" && row.fileId && (
                      <small>文件已上传；重试将仅保存分类与标签。</small>
                    )}
                  </div>
                  <span className={`status-pill ${row.state}`}>
                    {
                      {
                        pending: "待上传",
                        uploading: "上传中",
                        success: "已完成",
                        error: "失败",
                      }[row.state]
                    }
                  </span>
                  {row.state === "success" ? (
                    <Link className="text-button" to="/files">
                      查看
                    </Link>
                  ) : (
                    <button
                      className="icon-button"
                      disabled={busy}
                      aria-label={`移除 ${row.file.name}`}
                      onClick={() =>
                        setRows((previous) =>
                          previous.filter((r) => r.id !== row.id),
                        )
                      }
                    >
                      <Icon name="close" size={16} />
                    </button>
                  )}
                </li>
              ))}
            </ul>
            {!!rows.length && (
              <div className="upload-summary" role="status">
                <div className="progress-track">
                  <span
                    style={{
                      width: `${((succeeded + failed) / rows.length) * 100}%`,
                    }}
                  />
                </div>
                <div className="row">
                  <span className="muted">
                    已处理 {succeeded + failed} / {rows.length} 项 · 成功{" "}
                    {succeeded} · 失败 {failed}
                  </span>
                  <span className="spacer" />
                  <button
                    className="primary"
                    disabled={busy || !pending.length || !editor}
                    onClick={() => void start()}
                  >
                    <Icon name="upload" />
                    {busy
                      ? "正在上传…"
                      : failed
                        ? "上传剩余 / 重试失败项"
                        : "开始上传"}
                  </button>
                </div>
              </div>
            )}
          </div>
        </section>
        <aside className="stack">
          <section className="panel">
            <div className="panel-heading">
              <h2>归档设置</h2>
            </div>
            <div className="panel-body form-stack">
              <label>
                保存到分类
                <input
                  disabled={busy || !editor}
                  value={folder}
                  onChange={(e) => setFolder(e.target.value)}
                  placeholder="/课程资料/软件工程"
                  maxLength={255}
                />
                <small>使用 / 分隔层级，最多 5 级。</small>
              </label>
              <label>
                添加标签
                <input
                  disabled={busy || !editor}
                  value={tags}
                  onChange={(e) => setTags(e.target.value)}
                  placeholder="课程资料, 待整理"
                />
                <small>用逗号分隔，最多 20 个标签。</small>
              </label>
            </div>
          </section>
          <section className="upload-guide">
            <Icon name="shield" size={25} />
            <h3>准备好你的文档</h3>
            <p>上传前会检查文件大小、类型与文件头，服务端进一步校验内容。</p>
            <p>加密 PDF 请先解除密码保护；同名文件会自动追加序号。</p>
            <p>文件上传完成后，可从文件库进入已有阅读与识别页面。</p>
          </section>
        </aside>
      </div>
    </div>
  );
}
