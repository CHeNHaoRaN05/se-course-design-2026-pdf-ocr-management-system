import { useState } from "react";
import { Link } from "react-router-dom";
import { useAuth } from "../../app/AuthProvider";
import { api, ApiError } from "../../shared/http";
import {
  errorText,
  formatBytes,
  formatDate,
  type TrashItem,
} from "../../shared/management";
import {
  EmptyState,
  FileGlyph,
  Icon,
  Loading,
  Modal,
  Notice,
  PageHeading,
  Pagination,
} from "../../shared/ui";
import { useResource } from "../../shared/useResource";
import { forgetTrash, readTrash } from "./trashHistory";
import { purgeFile, restoreFile } from "./filesApi";

export default function TrashPage() {
  const { me } = useAuth();
  const editor = me?.role !== "viewer";
  const resource = useResource(
    async (signal) => {
      try {
        const items: TrashItem[] = [];
        for (let offset = 0; ; offset += 100) {
          const page = await api<TrashItem[]>(
            `/files/trash?limit=100&offset=${offset}`,
            { signal },
          );
          items.push(...page);
          if (page.length < 100) break;
        }
        return { items, local: false };
      } catch (e) {
        if (e instanceof ApiError && [404, 405].includes(e.status))
          return { items: me ? readTrash(me.id) : [], local: true };
        throw e;
      }
    },
    [me?.id],
  );
  const [q, setQ] = useState("");
  const [page, setPage] = useState(1);
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
  const filtered = (resource.data?.items ?? []).filter((file) =>
    file.name.toLowerCase().includes(q.toLowerCase()),
  );
  const current = Math.min(page, Math.max(1, Math.ceil(filtered.length / 12)));
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
        if (me) forgetTrash(me.id, file.id);
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
      {resource.data?.local && (
        <Notice tone="warning">
          当前显示本浏览器、当前账号的删除记录。服务端尚未提供完整回收站列表，其他浏览器删除的文件可凭文档
          ID 还原。实际可恢复状态以服务端返回为准。
        </Notice>
      )}
      {resource.error && <Notice tone="error">{resource.error}</Notice>}
      <section className="panel">
        <div className="panel-heading">
          <h2>
            {resource.data?.local ? "本浏览器删除记录" : "已删除文档"}
            <span className="count-badge">
              {resource.data?.items.length ?? "—"}
            </span>
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
                    <th>{resource.data?.local ? "记录时间" : "删除时间"}</th>
                    <th>操作</th>
                  </tr>
                </thead>
                <tbody>
                  {filtered
                    .slice((current - 1) * 12, current * 12)
                    .map((file) => (
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
              total={filtered.length}
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
