import { onFilesChanged } from "../management/fileEvents";
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { useAuth } from "../../app/AuthProvider";
import { api, downloadBlob } from "../../shared/http";
import type { FileItem } from "../../shared/types";
import {
  errorText,
  formatBytes,
  formatDate,
  statusNames,
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
import { queryFiles, fileBlob } from "./filesApi";
import FileActionDialog, { type FileAction } from "./FileActionDialog";

const PAGE_SIZE = 12;
export default function FilesPage() {
  const { me } = useAuth();
  const editor = me?.role !== "viewer";
  const [q, setQ] = useState("");
  const [folder, setFolder] = useState("");
  const [tag, setTag] = useState("");
  const [type, setType] = useState("");
  const [status, setStatus] = useState("");
  const [sort, setSort] = useState("newest");
  const [page, setPage] = useState(1);
  const [view, setView] = useState("list");
  const [action, setAction] = useState<{
    kind: FileAction;
    file: FileItem;
  } | null>(null);
  const [detail, setDetail] = useState<FileItem | null>(null);
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);
  const [hash, setHash] = useState("");
  const resource = useResource(
    (signal) =>
      queryFiles(
        {
          q,
          folder,
          tag,
          ...(type ? { media_type: type } : {}),
          ...(status ? { status } : {}),
          sort,
          limit: String(PAGE_SIZE),
          offset: String((page - 1) * PAGE_SIZE),
        },
        signal,
      ),
    [q, folder, tag, type, status, sort, page],
  );
  useEffect(() => onFilesChanged(resource.reload), [resource.reload]);
  const metadata = useResource(
    async (signal) => {
      const [folders, tags] = await Promise.all([
        api<string[]>("/files/folders", { signal }),
        api<string[]>("/files/tags", { signal }),
      ]);
      return { folders, tags };
    },
    [resource.data],
  );
  const files = resource.data?.items ?? [];
  const folders = metadata.data?.folders ?? [];
  const tags = metadata.data?.tags ?? [];
  const statusReady = resource.data?.status_available ?? false;
  const filtered = files;
  const currentPage = page;
  const visible = files;
  const hasFilters = !!(
    q ||
    folder ||
    tag ||
    type ||
    status
  );
  useEffect(() => {
    if (
      resource.data &&
      page > 1 &&
      (page - 1) * PAGE_SIZE >= resource.data.total
    )
      setPage(Math.max(1, Math.ceil(resource.data.total / PAGE_SIZE)));
  }, [resource.data, page]);
  useEffect(() => setPage(1), [q, folder, tag, type, status, sort]);
  // 状态服务不可用时仍展示服务端返回的文档；解除旧条件使用户能重新选择。
  useEffect(() => {
    if (resource.data && !resource.data.status_available) {
      if (status) setStatus("");
      if (sort === "status") setSort("newest");
    }
  }, [resource.data, status, sort]);
  function open(kind: FileAction, file: FileItem) {
    if (editor) {
      setMessage("");
      setAction({ kind, file });
    }
  }
  async function download(file: FileItem) {
    if (busy) return;
    setBusy(true);
    setMessage("");
    try {
      downloadBlob(await fileBlob(file.id), file.name);
    } catch (e) {
      setMessage(errorText(e));
    } finally {
      setBusy(false);
    }
  }
  const fileStatus = (file: FileItem) =>
    files.find((item) => item.id === file.id)?.status ?? "unknown";
  const actions = (file: FileItem) => (
    <div className="file-actions">
      <Link className="text-button" to={`/files/${file.id}`}>
        打开
      </Link>
      <details className="action-menu">
        <summary aria-label={`${file.name} 的更多操作`}>
          <Icon name="more" />
        </summary>
        <div>
          <button
            onClick={() => {
              setDetail(file);
              setHash("");
              setMessage("");
            }}
          >
            文档信息
          </button>
          <button disabled={busy} onClick={() => void download(file)}>
            下载原文件
          </button>
          {editor && (
            <>
              <button onClick={() => open("rename", file)}>重命名</button>
              <button onClick={() => open("move", file)}>移动分类</button>
              <button onClick={() => open("tag", file)}>编辑标签</button>
              <Link to={`/shares?file=${file.id}`}>创建分享</Link>
              <button className="error" onClick={() => open("delete", file)}>
                移入回收站
              </button>
            </>
          )}
        </div>
      </details>
    </div>
  );
  return (
    <div className="workspace-page">
      <PageHeading
        eyebrow="YOUR DOCUMENT LIBRARY"
        title="文件库"
        description="有序整理每一份资料，让知识随时可用。"
        actions={
          <>
            <button onClick={resource.reload} disabled={resource.loading}>
              <Icon name="refresh" />
              刷新
            </button>
            {editor && (
              <Link className="button primary" to="/upload">
                <Icon name="plus" />
                上传文档
              </Link>
            )}
          </>
        }
      />
      {(resource.error || message) && (
        <Notice tone="error">
          {resource.error || message}
          {resource.error && (
            <button className="text-button" onClick={resource.reload}>
              重新加载
            </button>
          )}
        </Notice>
      )}
      {resource.data && !statusReady && (
        <Notice tone="warning">
          识别状态暂不可用，当前使用非状态筛选；如选择状态排序，将恢复最新上传排序。
        </Notice>
      )}
      <div className="library-layout">
        <aside className="panel folder-panel">
          <div className="panel-heading">
            <h2>分类目录</h2>
            <Icon name="folder" size={16} />
          </div>
          <div className="folder-tree">
            <button
              className={!folder ? "active" : ""}
              onClick={() => setFolder("")}
            >
              <Icon name="folder" size={17} />
              全部文档
            </button>
            {folders.map((path) => (
              <button
                key={path}
                title={path}
                className={folder === path ? "active" : ""}
                onClick={() => setFolder(path)}
              >
                <Icon name="folder" size={16} />
                <span className="folder-name">{path}</span>
              </button>
            ))}
          </div>
          <div className="folder-note">
            从文档菜单选择“移动分类”，
            <br />
            即可设置或新建分类路径。
          </div>
          <div className="panel-heading">
            <h2>我的标签</h2>
            <Icon name="tag" size={16} />
          </div>
          <div className="tag-cloud">
            {tags.map((value, i) => (
              <button
                className={`tag-chip color-${i % 4} ${tag === value ? "selected" : ""}`}
                key={value}
                onClick={() => setTag(tag === value ? "" : value)}
              >
                {value}
              </button>
            ))}
            {!tags.length && (
              <span className="muted">给文档添加标签，方便筛选</span>
            )}
          </div>
        </aside>
        <section className="panel file-panel">
          <div className="panel-heading">
            <h2>
              {folder ? folder.split("/").pop() : "全部文档"}
              <span className="count-badge">{resource.data?.total ?? 0}</span>
            </h2>
            <div className="segmented">
              <button
                aria-label="列表视图"
                aria-pressed={view === "list"}
                className={view === "list" ? "active" : ""}
                onClick={() => setView("list")}
              >
                <Icon name="list" size={17} />
              </button>
              <button
                aria-label="卡片视图"
                aria-pressed={view === "grid"}
                className={view === "grid" ? "active" : ""}
                onClick={() => setView("grid")}
              >
                <Icon name="grid" size={17} />
              </button>
            </div>
          </div>
          <div className="file-filters">
            <label className="input-icon">
              <Icon name="search" size={17} />
              <input
                aria-label="按文件名搜索"
                maxLength={255}
                placeholder="搜索文件名…"
                value={q}
                onChange={(e) => setQ(e.target.value)}
              />
            </label>
            <select
              aria-label="文件类型"
              value={type}
              onChange={(e) => setType(e.target.value)}
            >
              <option value="">所有类型</option>
              <option value="application/pdf">PDF 文档</option>
              <option value="image/png">PNG 图片</option>
              <option value="image/jpeg">JPEG 图片</option>
            </select>
            <select
              aria-label="识别状态"
              disabled={!statusReady}
              value={status}
              onChange={(e) => setStatus(e.target.value)}
            >
              <option value="">
                {statusReady ? "所有状态" : "识别状态不可用"}
              </option>
              {Object.entries(statusNames)
                .filter(([key]) => key !== "unknown")
                .map(([key, label]) => (
                  <option key={key} value={key}>
                    {label}
                  </option>
                ))}
            </select>
            <select
              aria-label="排序方式"
              value={sort}
              onChange={(e) => setSort(e.target.value)}
            >
              <option value="newest">最新上传</option>
              <option value="name">名称排序</option>
              <option value="size">大小排序</option>
              <option value="pages">页数排序</option>
              <option value="status" disabled={!statusReady}>
                状态排序
              </option>
            </select>
          </div>
          {tag && (
            <div className="active-filter">
              标签：
              <button className="tag-chip selected" onClick={() => setTag("")}>
                {tag}
                <Icon name="close" size={12} />
              </button>
            </div>
          )}
          {resource.loading ? (
            <Loading text="正在加载文档库…" />
          ) : resource.error ? (
            <EmptyState
              title="文档库加载失败"
              description="请检查网络和服务状态后重试。"
              action={<button onClick={resource.reload}>重新加载文档</button>}
            />
          ) : !filtered.length ? (
            <EmptyState
              title={
                hasFilters
                  ? "没有符合条件的文档"
                  : "你的文档空间，等待第一份资料"
              }
              description={
                hasFilters
                  ? "试试调整关键词、分类或筛选条件。"
                  : "上传 PDF 或图片，开始构建自己的资料库。"
              }
              action={
                editor && !hasFilters ? (
                  <Link className="button primary" to="/upload">
                    <Icon name="upload" />
                    上传第一份文档
                  </Link>
                ) : (
                  <button
                    onClick={() => {
                      setQ("");
                      setFolder("");
                      setTag("");
                      setType("");
                      setStatus("");
                    }}
                  >
                    清除筛选
                  </button>
                )
              }
            />
          ) : view === "list" ? (
            <div className="table-scroll">
              <table className="file-table">
                <thead>
                  <tr>
                    <th>文档名称</th>
                    <th>大小 / 页数</th>
                    <th>识别状态</th>
                    <th>上传日期</th>
                    <th>操作</th>
                  </tr>
                </thead>
                <tbody>
                  {visible.map((file) => (
                    <tr key={file.id}>
                      <td>
                        <div className="file-name-cell">
                          <FileGlyph type={file.media_type} />
                          <div>
                            <button
                              className="filename-button"
                              title={file.name}
                              onClick={() => {
                                setDetail(file);
                                setHash("");
                                setMessage("");
                              }}
                            >
                              {file.name}
                            </button>
                            <div className="file-tags">
                              {file.tags.slice(0, 3).map((value, i) => (
                                <button
                                  key={value}
                                  className={`tag-chip color-${i % 4}`}
                                  onClick={() => setTag(value)}
                                >
                                  {value}
                                </button>
                              ))}
                              {file.tags.length > 3 && (
                                <small>+{file.tags.length - 3}</small>
                              )}
                              {!file.tags.length && (
                                <small>
                                  {file.folder === "/" ? "未分类" : file.folder}{" "}
                                </small>
                              )}
                            </div>
                          </div>
                        </div>
                      </td>
                      <td>
                        <span className="nowrap">{formatBytes(file.size)}</span>
                        <small className="cell-sub">{file.page_count} 页</small>
                      </td>
                      <td>
                        <span className={`status-pill ${fileStatus(file)}`}>
                          <i />
                          {statusNames[fileStatus(file)] ?? fileStatus(file)}
                        </span>
                      </td>
                      <td className="date-cell">
                        {formatDate(file.created_at)}
                      </td>
                      <td>{actions(file)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="file-grid">
              {visible.map((file) => (
                <article
                  className="document-card"
                  key={file.id}
                >
                  <div className="row">
                    <FileGlyph type={file.media_type} />
                  </div>
                  <button
                    className="filename-button"
                    title={file.name}
                    onClick={() => {
                      setDetail(file);
                      setHash("");
                    }}
                  >
                    {file.name}
                  </button>
                  <p>
                    {formatBytes(file.size)} · {file.page_count} 页
                  </p>
                  <span className={`status-pill ${fileStatus(file)}`}>
                    {statusNames[fileStatus(file)]}
                  </span>
                  <div className="document-card-footer">
                    <span>{formatDate(file.created_at)}</span>
                    {actions(file)}
                  </div>
                </article>
              ))}
            </div>
          )}
          {!resource.loading && (
            <Pagination
              page={currentPage}
              total={resource.data?.total ?? 0}
              pageSize={PAGE_SIZE}
              onChange={setPage}
            />
          )}
        </section>
      </div>
      {action && (
        <FileActionDialog
          action={action.kind}
          file={action.file}
          onClose={() => {
            setAction(null);
          }}
          onChanged={() => {
            resource.reload();
          }}
        />
      )}
      {detail && (
        <Modal title="文档信息" onClose={() => setDetail(null)} busy={busy}>
          <div className="detail-title">
            <FileGlyph type={detail.media_type} />
            <h3>{detail.name}</h3>
          </div>
          <dl className="detail-list">
            <dt>文档 ID</dt>
            <dd className="mono">{detail.id}</dd>
            <dt>文件类型</dt>
            <dd>{detail.media_type}</dd>
            <dt>文件大小</dt>
            <dd>{formatBytes(detail.size)}</dd>
            <dt>总页数</dt>
            <dd>{detail.page_count} 页</dd>
            <dt>上传时间</dt>
            <dd>{formatDate(detail.created_at, true)}</dd>
            <dt>所属分类</dt>
            <dd>{detail.folder}</dd>
            <dt>标签</dt>
            <dd>{detail.tags.join("、") || "暂无标签"}</dd>
          </dl>
          {message && <Notice tone="error">{message}</Notice>}
          {hash ? (
            <div className="hash-result">
              <small>SHA-256（原文件计算）</small>
              <code>{hash}</code>
            </div>
          ) : (
            <button
              className="text-button"
              disabled={busy}
              onClick={async () => {
                setBusy(true);
                try {
                  if (!crypto.subtle)
                    throw new Error(
                      "请使用 HTTPS 或 localhost 访问，以计算文件校验值。",
                    );
                  const digest = await crypto.subtle.digest(
                    "SHA-256",
                    await (await fileBlob(detail.id)).arrayBuffer(),
                  );
                  setHash(
                    Array.from(new Uint8Array(digest), (byte) =>
                      byte.toString(16).padStart(2, "0"),
                    ).join(""),
                  );
                } catch (e) {
                  setMessage(errorText(e));
                } finally {
                  setBusy(false);
                }
              }}
            >
              计算 SHA-256 校验值
            </button>
          )}
          <div className="modal-actions">
            <button disabled={busy} onClick={() => void download(detail)}>
              <Icon name="download" />
              下载原文件
            </button>
            <Link className="button primary" to={`/files/${detail.id}`}>
              打开文档
              <Icon name="chevron" size={16} />
            </Link>
          </div>
        </Modal>
      )}
    </div>
  );
}
