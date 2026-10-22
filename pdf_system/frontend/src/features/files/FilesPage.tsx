import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { useAuth } from "../../app/AuthProvider";
import { startOcrJob } from "../ocr/ocrApi";
import type { FileItem } from "../../shared/types";
import { deleteFile, listFiles, uploadFile } from "./filesApi";

export default function FilesPage() {
  const { me } = useAuth();
  const [files, setFiles] = useState<FileItem[]>([]);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const input = useRef<HTMLInputElement>(null);

  const reload = () => listFiles().then(setFiles).catch((e) => setError(String(e.message ?? e)));
  useEffect(() => { void reload(); }, []);

  async function onUpload() {
    const file = input.current?.files?.[0];
    if (!file) return;
    setBusy(true);
    setError("");
    try {
      await uploadFile(file);
      await reload();
    } catch (e) {
      setError(e instanceof Error ? e.message : "上传失败");
    } finally {
      setBusy(false);
      if (input.current) input.current.value = "";
    }
  }

  async function onOcr(fileId: string) {
    setError("");
    try {
      await startOcrJob({ file_id: fileId, mode: "general", tables: true });
      window.location.href = `/files/${fileId}`;
    } catch (e) {
      // 429 表示本月配额不足（契约 C3）
      setError(e instanceof Error ? e.message : "创建识别任务失败");
    }
  }

  return (
    <div>
      <div className="card row">
        <input ref={input} type="file" accept=".pdf,.png,.jpg,.jpeg" />
        <button className="primary" disabled={busy} onClick={onUpload}>上传</button>
        <span className="muted">上限 20 MiB · PDF 100 页</span>
      </div>
      {error && <p className="error">{error}</p>}
      <div className="card">
        <table>
          <thead>
            <tr><th>文件名</th><th>类型</th><th>页数</th><th>大小</th><th>标签</th><th>操作</th></tr>
          </thead>
          <tbody>
            {files.map((file) => (
              <tr key={file.id}>
                <td><Link to={`/files/${file.id}`}>{file.name}</Link></td>
                <td>{file.media_type === "application/pdf" ? "PDF" : "图片"}</td>
                <td>{file.page_count}</td>
                <td>{(file.size / 1024).toFixed(0)} KiB</td>
                <td>{file.tags.join("、") || "-"}</td>
                <td>
                  <button disabled={me?.role === "viewer"} onClick={() => onOcr(file.id)}>识别</button>{" "}
                  <button disabled={me?.role === "viewer"} onClick={() => deleteFile(file.id).then(reload)}>删除</button>
                </td>
              </tr>
            ))}
            {files.length === 0 && <tr><td colSpan={6} className="muted">暂无文件</td></tr>}
          </tbody>
        </table>
      </div>
    </div>
  );
}
