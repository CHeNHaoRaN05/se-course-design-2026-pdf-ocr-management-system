import { useEffect, useState, type FormEvent } from "react";
import { Link, useParams } from "react-router-dom";
import { ApiError, downloadBlob, publicFile } from "../../shared/http";
import { errorText, formatBytes } from "../management/management";
import { FileGlyph, Icon, Notice } from "../management/ui";

interface Metadata {
  name: string;
  media_type: string;
  page_count: number;
  size: number;
}
export default function PublicSharePage() {
  const { token = "" } = useParams();
  const [code, setCode] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [meta, setMeta] = useState<Metadata | null>(null);
  const [file, setFile] = useState<{ blob: Blob; filename: string } | null>(
    null,
  );
  useEffect(() => {
    setMeta(null);
    setFile(null);
    setCode("");
    setError("");
  }, [token]);
  async function visit(event: FormEvent) {
    event.preventDefault();
    if (busy) return;
    setBusy(true);
    setError("");
    setMeta(null);
    setFile(null);
    try {
      const result = await publicFile(
        `/share/token/${encodeURIComponent(token)}${code.trim() ? `?code=${encodeURIComponent(code.trim())}` : ""}`,
      );
      if (result.blob.type.includes("application/json"))
        setMeta(JSON.parse(await result.blob.text()) as Metadata);
      else setFile(result);
    } catch (e) {
      setError(
        e instanceof ApiError && [404, 410].includes(e.status)
          ? "无法访问此分享。请检查提取码，或联系分享者确认链接是否有效。"
          : errorText(e),
      );
    } finally {
      setBusy(false);
    }
  }
  return (
    <div className="public-share">
      <header>
        <Link to="/login" className="public-brand">
          <span className="brand-mark">
            <Icon name="file" />
          </span>
          PDF 文档空间
        </Link>
        <span className="role-badge">访客访问</span>
      </header>
      <main>
        <div className="public-share-icon">
          <Icon name="share" size={32} />
        </div>
        <h1>一份文档，与你分享</h1>
        <p className="muted">通过分享链接安全访问，无需登录。</p>
        <section className="panel">
          <div className="panel-body">
            {error && <Notice tone="error">{error}</Notice>}
            {!meta && !file ? (
              <form className="form-stack" onSubmit={visit}>
                <label>
                  提取码 <span className="muted">（如分享者设置）</span>
                  <input
                    maxLength={32}
                    autoComplete="off"
                    placeholder="无提取码可直接访问"
                    value={code}
                    onChange={(e) => setCode(e.target.value)}
                  />
                </label>
                <button className="primary" disabled={busy}>
                  {busy ? "正在验证并获取文档…" : "访问文档"}
                  <Icon name="chevron" size={16} />
                </button>
              </form>
            ) : (
              <>
                <div className="detail-title">
                  <FileGlyph type={meta?.media_type ?? file!.blob.type} />
                  <h2>{meta?.name ?? file?.filename}</h2>
                </div>
                <p>
                  {formatBytes(meta?.size ?? file!.blob.size)}
                  {meta && ` · ${meta.page_count} 页`}
                </p>
                {meta ? (
                  <Notice>
                    分享者仅开放文档信息，未开放原文件访问。如需阅读文件，请联系分享者调整权限。
                  </Notice>
                ) : (
                  <button
                    className="primary"
                    onClick={() =>
                      file && downloadBlob(file.blob, file.filename)
                    }
                  >
                    <Icon name="download" />
                    下载文档
                  </button>
                )}
                <p className="muted">
                  访客不能修改文档、创建任务或更改分享设置。
                </p>
              </>
            )}
          </div>
        </section>
        <p className="public-footer">
          <Icon name="shield" size={15} />
          访问权限由分享者控制
        </p>
      </main>
    </div>
  );
}
