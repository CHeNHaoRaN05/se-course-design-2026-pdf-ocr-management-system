import { useState, type FormEvent } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { useAuth } from "../../app/AuthProvider";
import { api } from "../../shared/http";
import {
  errorText,
  formatDate,
  type ShareItem,
} from "../management/management";
import {
  EmptyState,
  Icon,
  Loading,
  Modal,
  Notice,
  PageHeading,
  Pagination,
} from "../management/ui";
import { useResource } from "../management/useResource";
import { allFiles } from "../files/filesApi";

export const sharePageUrl = (token: string) =>
  `${window.location.origin}/share/${encodeURIComponent(token)}`;
export default function SharesPage() {
  const { me } = useAuth();
  const [params] = useSearchParams();
  const editor = me?.role !== "viewer";
  const shares = useResource((signal) =>
    api<ShareItem[]>("/share", { signal }),
  );
  const files = useResource((signal) => allFiles(signal));
  const [fileId, setFileId] = useState(params.get("file") ?? "");
  const [days, setDays] = useState("7");
  const [code, setCode] = useState("");
  const [download, setDownload] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [created, setCreated] = useState<ShareItem | null>(null);
  const [revoke, setRevoke] = useState<ShareItem | null>(null);
  const [q, setQ] = useState("");
  const [page, setPage] = useState(1);
  const names = new Map(files.data?.map((file) => [file.id, file.name]));
  const items = (shares.data ?? []).filter((share) =>
    (names.get(share.file_id) ?? share.file_id)
      .toLowerCase()
      .includes(q.toLowerCase()),
  );
  const current = Math.min(page, Math.max(1, Math.ceil(items.length / 8)));
  async function create(event: FormEvent) {
    event.preventDefault();
    if (busy || !editor) return;
    setError("");
    setMessage("");
    if (code && !/^[A-Za-z0-9]{1,32}$/.test(code)) {
      setError("提取码只允许1至32位字母和数字。");
      return;
    }
    setBusy(true);
    try {
      const share = await api<ShareItem>("/share", {
        method: "POST",
        body: JSON.stringify({
          file_id: fileId,
          expires_in_days: Number(days),
          access_code: code.trim() || null,
          allow_download: download,
        }),
      });
      setCreated(share);
      shares.reload();
      setMessage("分享链接已创建。");
    } catch (e) {
      setError(errorText(e));
    } finally {
      setBusy(false);
    }
  }
  async function copy(share: ShareItem) {
    try {
      await navigator.clipboard.writeText(sharePageUrl(share.token));
      setMessage("分享链接已复制。");
    } catch {
      setCreated(share);
      setMessage("请在下方链接框中手动选择并复制。");
    }
  }
  return (
    <div className="workspace-page">
      <PageHeading
        eyebrow="SHARE & COLLABORATE"
        title="我的分享"
        description="分享有价值的资料，自主控制有效期与访问权限。"
        actions={
          <button onClick={shares.reload} disabled={shares.loading}>
            <Icon name="refresh" />
            刷新
          </button>
        }
      />
      {(error || shares.error || files.error) && (
        <Notice tone="error">{error || shares.error || files.error}</Notice>
      )}
      {message && <Notice tone="success">{message}</Notice>}
      <div className="share-layout">
        <section className="panel">
          <div className="panel-heading">
            <h2>创建分享</h2>
            <Icon name="share" />
          </div>
          <form className="panel-body form-stack" onSubmit={create}>
            <label>
              选择文档
              <select
                required
                disabled={!editor || files.loading || busy}
                value={fileId}
                onChange={(e) => setFileId(e.target.value)}
              >
                <option value="">请选择文档</option>
                {files.data?.map((file) => (
                  <option key={file.id} value={file.id}>
                    {file.name}
                  </option>
                ))}
              </select>
            </label>
            <label>
              有效期
              <select
                disabled={!editor || busy}
                value={days}
                onChange={(e) => setDays(e.target.value)}
              >
                <option value="1">1 天</option>
                <option value="7">7 天</option>
                <option value="30">30 天</option>
              </select>
            </label>
            <label>
              提取码 <span className="muted">（可选）</span>
              <input
                disabled={!editor || busy}
                maxLength={32}
                autoComplete="off"
                placeholder="不填写则无需提取码"
                value={code}
                onChange={(e) => setCode(e.target.value)}
              />
            </label>
            <label className="checkbox-label">
              <input
                type="checkbox"
                checked={download}
                disabled={!editor || busy}
                onChange={(e) => setDownload(e.target.checked)}
              />
              允许访问与下载原文件
            </label>
            <p className="muted">
              关闭后，当前服务仅向访客展示文档信息，不提供原文件。分享可随时撤销。
            </p>
            <button className="primary" disabled={!editor || busy || !fileId}>
              <Icon name="share" />
              {busy ? "正在创建…" : "生成分享链接"}
            </button>
          </form>
          {created && (
            <div className="created-share">
              <strong>分享已就绪</strong>
              <label className="visually-hidden" htmlFor="created-link">
                生成的分享链接
              </label>
              <input
                id="created-link"
                readOnly
                value={sharePageUrl(created.token)}
                onFocus={(e) => e.target.select()}
              />
              <div className="row">
                <button onClick={() => void copy(created)}>复制链接</button>
                <Link className="text-button" to={`/share/${created.token}`}>
                  访问分享页
                </Link>
              </div>
              {created.access_code && (
                <p>
                  提取码：<code>{created.access_code}</code>
                </p>
              )}
            </div>
          )}
        </section>
        <section className="panel">
          <div className="panel-heading">
            <h2>
              分享记录
              <span className="count-badge">{shares.data?.length ?? "—"}</span>
            </h2>
            <input
              aria-label="搜索分享文档"
              placeholder="搜索分享文档…"
              value={q}
              onChange={(e) => {
                setQ(e.target.value);
                setPage(1);
              }}
            />
          </div>
          {shares.loading ? (
            <Loading />
          ) : !items.length ? (
            <EmptyState
              icon="share"
              title="暂无分享记录"
              description="选择文档创建一条分享链接，开始协作。"
            />
          ) : (
            <>
              <div className="share-list">
                {items.slice((current - 1) * 8, current * 8).map((share) => {
                  const expired = share.expired;
                  return (
                    <article className="share-card" key={share.id}>
                      <div className="row">
                        <span className="stat-icon blue">
                          <Icon name="file" />
                        </span>
                        <div className="grow">
                          <h3>
                            {names.get(share.file_id) ??
                              `文档 ${share.file_id.slice(0, 8)}`}
                          </h3>
                          <p className="muted">
                            创建于 {formatDate(share.created_at)}
                          </p>
                        </div>
                        <span
                          className={`status-pill ${expired ? "unknown" : "success"}`}
                        >
                          {expired ? "已过期" : "分享中"}
                        </span>
                      </div>
                      <div className="share-meta">
                        <span>
                          <Icon name="clock" size={15} />
                          {share.expires_at
                            ? `${formatDate(share.expires_at, true)} 到期`
                            : "永久有效"}
                        </span>
                        <span>{share.visit_count} 次访问</span>
                        <span>
                          {share.allow_download ? "可下载" : "仅文档信息"}
                        </span>
                        {share.access_code && (
                          <span>提取码：{share.access_code}</span>
                        )}
                      </div>
                      <div className="share-card-actions">
                        <button
                          disabled={!!expired}
                          onClick={() => void copy(share)}
                        >
                          复制链接
                        </button>
                        <Link
                          className="text-button"
                          to={`/share/${share.token}`}
                        >
                          查看分享
                        </Link>
                        <span className="spacer" />
                        {editor && (
                          <button
                            className="text-button error"
                            onClick={() => {
                              setRevoke(share);
                              setError("");
                            }}
                          >
                            撤销分享
                          </button>
                        )}
                      </div>
                    </article>
                  );
                })}
              </div>
              <Pagination
                page={current}
                total={items.length}
                pageSize={8}
                onChange={setPage}
              />
            </>
          )}
        </section>
      </div>
      {revoke && (
        <Modal title="撤销分享" onClose={() => setRevoke(null)} busy={busy}>
          <p>撤销后，此链接将立即失效。已经下载的文件无法收回。</p>
          {error && <Notice tone="error">{error}</Notice>}
          <div className="modal-actions">
            <button disabled={busy} onClick={() => setRevoke(null)}>
              保留分享
            </button>
            <button
              className="danger"
              disabled={busy}
              onClick={async () => {
                setBusy(true);
                setError("");
                try {
                  await api(`/share/${revoke.id}`, { method: "DELETE" });
                  if (created?.id === revoke.id) setCreated(null);
                  setRevoke(null);
                  shares.reload();
                  setMessage("分享已撤销。");
                } catch (e) {
                  setError(errorText(e));
                } finally {
                  setBusy(false);
                }
              }}
            >
              {busy ? "正在撤销…" : "确认撤销"}
            </button>
          </div>
        </Modal>
      )}
    </div>
  );
}
