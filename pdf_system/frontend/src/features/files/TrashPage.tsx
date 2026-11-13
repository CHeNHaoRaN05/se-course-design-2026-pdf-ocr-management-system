import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { useAuth } from "../../app/AuthProvider";
import { api } from "../../shared/http";
import {
  errorText,
  formatBytes,
  formatDate,
  type TrashItem,
  type PageResult,
} from "../management/management";
import {
  EmptyState,
  FileGlyph,
  Icon,
  Loading,
  Modal,
  Notice,
  PageHeading,
  Pagination,
} from "../management/ui";
import { useResource } from "../management/useResource";
import { purgeFile, restoreFile } from "./filesApi";

export default function TrashPage() {
  const { me } = useAuth();
  const editor = me?.role !== "viewer";
  const [q, setQ] = useState("");
  const [page, setPage] = useState(1);
  const resource = useResource(
    (signal) =>
      api<PageResult<TrashItem>>(
        `/files/trash?envelope=true&limit=12&offset=${(page - 1) * 12}&q=${encodeURIComponent(q)}`,
        { signal },
      ),
    [me?.id, page, q],
  );
  useEffect(() => {
    if (resource.data && page > 1 && (page - 1) * 12 >= resource.data.total)
      setPage(Math.max(1, Math.ceil(resource.data.total / 12)));
  }, [resource.data, page]);
  const [selected, setSelected] = useState<string[]>([]);
  const [restoreId, setRestoreId] = useState("");
  const [operation, setOperation] = useState<{
    purge: boolean;
    items: { id: string; name: string }[];
  } | null>(null);
  const [busy, setBusy] = useState(false);
  const [confirmed, setConfirmed] = useState(false);
  const [results, setResults] = useState<
    { name: string; ok: boolean; error?: string }[]
  >([]);
  const [done, setDone] = useState(false);
  const filtered = resource.data?.items ?? [];
  const current = page;
  useEffect(() => setSelected([]), [page, q]);
  function begin(purge: boolean, items: { id: string; name: string }[]) {
    setOperation({ purge, items });
    setConfirmed(false);
    setResults([]);
    setDone(false);
  }
  async function run() {
    if (!operation || busy || !editor || (operation.purge && !confirmed))
      return;
    setBusy(true);
    for (const file of operation.items) {
      try {
        if (operation.purge) await purgeFile(file.id);
        else await restoreFile(file.id);
        setResults((old) => [...old, { name: file.name, ok: true }]);
      } catch (e) {
        setResults((old) => [
          ...old,
          { name: file.name, ok: false, error: errorText(e) },
        ]);
      }
    }
    setBusy(false);
    setDone(true);
    setSelected([]);
    resource.reload();
  }
  return (
    <div className="workspace-page">
      <PageHeading
        eyebrow="RECYCLE BIN"
        title="回收站"
        description="找回误删的资料，或彻底删除不再需要的文档。"
        actions={
          <button disabled={resource.loading} onClick={resource.reload}>
            <Icon name="refresh" />
            刷新
          </button>
        }
      />
      {resource.error && <Notice tone="error">{resource.error}</Notice>}
      <section className="panel">
        <div className="panel-heading">
          <h2>
            已删除文档
            <span className="count-badge">{resource.data?.total ?? "—"}</span>
          </h2>
          <label className="input-icon">
            <Icon name="search" size={16} />
            <input
              aria-label="搜索回收站"
              placeholder="搜索文档名称…"
              value={q}
              onChange={(e) => {
                setQ(e.target.value);
                setPage(1);
              }}
            />
          </label>
        </div>
        {selected.length > 0 && editor && (
          <div className="bulk-toolbar">
            <strong>已选 {selected.length} 项</strong>
            <button
              onClick={() =>
                begin(
                  false,
                  filtered.filter((f) => selected.includes(f.id)),
                )
              }
            >
              批量还原
            </button>
            <button
              className="danger"
              onClick={() =>
                begin(
                  true,
                  filtered.filter((f) => selected.includes(f.id)),
                )
              }
            >
              彻底删除
            </button>
            <button className="text-button" onClick={() => setSelected([])}>
              取消选择
            </button>
          </div>
        )}
        {resource.loading ? (
          <Loading />
        ) : resource.error ? (
          <EmptyState
            title="回收站加载失败"
            description="请检查权限和服务状态后重试。"
          />
        ) : !filtered.length ? (
          <EmptyState
            icon="trash"
            title="暂无删除记录"
            description="移入回收站的文档记录将在这里显示。"
            action={
              <Link className="button" to="/files">
                返回文件库
              </Link>
            }
          />
        ) : (
          <>
            <div className="table-scroll">
              <table>
                <thead>
                  <tr>
                    <th>选择</th>
                    <th>文档名称</th>
                    <th>大小</th>
                    <th>删除时间</th>
                    <th>操作</th>
                  </tr>
                </thead>
                <tbody>
                  {filtered.map((file) => (
                    <tr key={file.id}>
                      <td>
                        <input
                          type="checkbox"
                          aria-label={`选择 ${file.name}`}
                          checked={selected.includes(file.id)}
                          onChange={(e) =>
                            setSelected((old) =>
                              e.target.checked
                                ? [...old, file.id]
                                : old.filter((id) => id !== file.id),
                            )
                          }
                        />
                      </td>
                      <td>
                        <div className="file-name-cell">
                          <FileGlyph type={file.media_type} />
                          <div>
                            <strong>{file.name}</strong>
                            <small className="cell-sub mono">{file.id}</small>
                          </div>
                        </div>
                      </td>
                      <td>{formatBytes(file.size)}</td>
                      <td>{formatDate(file.deleted_at, true)}</td>
                      <td>
                        <div className="row">
                          <button
                            disabled={!editor}
                            onClick={() => begin(false, [file])}
                          >
                            还原
                          </button>
                          <button
                            className="danger subtle"
                            disabled={!editor}
                            onClick={() => begin(true, [file])}
                          >
                            彻底删除
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <Pagination
              page={current}
              total={resource.data?.total ?? 0}
              pageSize={12}
              onChange={setPage}
            />
          </>
        )}
      </section>
      {editor && (
        <section className="panel restore-panel">
          <div>
            <h2>按文档 ID 还原</h2>
            <p className="muted">
              找不到记录？输入原文档 ID，服务端会校验归属和删除状态。
            </p>
          </div>
          <form
            className="row"
            onSubmit={(e) => {
              e.preventDefault();
              begin(false, [{ id: restoreId.trim(), name: restoreId.trim() }]);
            }}
          >
            <input
              aria-label="待还原文档 ID"
              required
              pattern="[a-fA-F0-9]{32}"
              placeholder="32 位文档 ID"
              value={restoreId}
              onChange={(e) => setRestoreId(e.target.value)}
            />
            <button type="submit">还原文档</button>
          </form>
        </section>
      )}
      {operation && (
        <Modal
          title={operation.purge ? "彻底删除文档" : "还原文档"}
          onClose={() => setOperation(null)}
          busy={busy}
        >
          {!done && (
            <>
              <p>
                将{operation.purge ? "彻底删除" : "还原"}{" "}
                {operation.items.length} 份文档。
              </p>
              {operation.purge && (
                <Notice tone="warning">
                  文件及相关结果将被永久删除，无法撤销。
                </Notice>
              )}
              {operation.purge && (
                <label className="checkbox-label">
                  <input
                    type="checkbox"
                    checked={confirmed}
                    disabled={busy}
                    onChange={(e) => setConfirmed(e.target.checked)}
                  />
                  我了解彻底删除后无法恢复
                </label>
              )}
            </>
          )}
          {!!results.length && (
            <div className="operation-results" role="status">
              <strong>
                成功 {results.filter((r) => r.ok).length} 项 · 失败{" "}
                {results.filter((r) => !r.ok).length} 项
              </strong>
              {results.map((result, i) => (
                <p key={i} className={result.ok ? "success-text" : "error"}>
                  {result.name}：{result.ok ? "操作成功" : result.error}
                </p>
              ))}
            </div>
          )}
          <div className="modal-actions">
            <button disabled={busy} onClick={() => setOperation(null)}>
              {done ? "完成" : "取消"}
            </button>
            {!done && (
              <button
                className={operation.purge ? "danger" : "primary"}
                disabled={busy || (operation.purge && !confirmed)}
                onClick={() => void run()}
              >
                {busy ? "正在处理…" : "确认"}
              </button>
            )}
          </div>
        </Modal>
      )}
    </div>
  );
}
