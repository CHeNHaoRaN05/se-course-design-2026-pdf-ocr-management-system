import { useState, type FormEvent } from "react";
import { api, downloadBlob } from "../../shared/http";
import {
  formatDate,
  type PageResult,
  type AuditItem,
} from "../management/management";
import {
  EmptyState,
  Icon,
  Loading,
  Notice,
  PageHeading,
  Pagination,
} from "../management/ui";
import { csvCell, validDateRange } from "../management/csv";
import { useResource } from "../management/useResource";

const actions: Record<string, string> = {
  file_uploaded: "上传文档",
  file_updated: "更新文档",
  file_trashed: "移入回收站",
  file_restored: "还原文档",
  file_purged: "彻底删除",
  share_created: "创建分享",
  share_revoked: "撤销分享",
  share_access: "分享访问",
  user_role_changed: "角色调整",
  user_disabled: "禁用账号",
};
const blank = { actor_id: "", action: "", date_from: "", date_to: "" };
export default function AuditPage() {
  const [filters, setFilters] = useState(blank);
  const [submitted, setSubmitted] = useState(blank);
  const [offset, setOffset] = useState(0);
  const [error, setError] = useState("");
  const resource = useResource(
    (signal) => {
      const params = new URLSearchParams({
        limit: "20",
        envelope: "true",
        offset: String(offset),
      });
      Object.entries(submitted).forEach(([key, value]) => {
        if (value) params.set(key, value);
      });
      return api<PageResult<AuditItem>>(`/audit?${params}`, { signal });
    },
    [submitted, offset],
  );
  const rows = resource.data?.items ?? [];
  function submit(event: FormEvent) {
    event.preventDefault();
    setError("");
    if (!validDateRange(filters.date_from, filters.date_to)) {
      setError("开始日期不能晚于结束日期。");
      return;
    }
    setOffset(0);
    setSubmitted({ ...filters, actor_id: filters.actor_id.trim() });
  }
  function exportCsv() {
    const lines = [
      ["时间（UTC，原始值）", "用户 ID", "动作", "资源 ID"],
      ...rows.map((row) => [
        row.created_at,
        row.actor_id,
        row.action,
        row.resource_id ?? "",
      ]),
    ];
    downloadBlob(
      new Blob(
        [
          "\uFEFF",
          lines.map((line) => line.map(csvCell).join(",")).join("\r\n"),
        ],
        { type: "text/csv;charset=utf-8" },
      ),
      `操作日志-${new Date().toISOString().slice(0, 10)}.csv`,
    );
  }
  return (
    <div className="workspace-page">
      <PageHeading
        eyebrow="ACTIVITY & AUDIT"
        title="操作日志"
        description="追踪重要操作，了解谁在何时修改了哪些资源。"
        actions={
          <>
            <button onClick={resource.reload} disabled={resource.loading}>
              <Icon name="refresh" />
              刷新
            </button>
            <button
              disabled={!rows.length || resource.loading}
              onClick={exportCsv}
            >
              <Icon name="download" />
              导出当前页
            </button>
          </>
        }
      />
      {(error || resource.error) && (
        <Notice tone="error">{error || resource.error}</Notice>
      )}
      <section className="panel">
        <form className="audit-filters" onSubmit={submit}>
          <label>
            操作人
            <input
              maxLength={32}
              placeholder="用户 ID"
              value={filters.actor_id}
              onChange={(e) =>
                setFilters({ ...filters, actor_id: e.target.value })
              }
            />
          </label>
          <label>
            操作类型
            <select
              value={filters.action}
              onChange={(e) =>
                setFilters({ ...filters, action: e.target.value })
              }
            >
              <option value="">全部操作</option>
              {Object.entries(actions).map(([key, label]) => (
                <option key={key} value={key}>
                  {label}
                </option>
              ))}
            </select>
          </label>
          <label>
            起始日期（UTC）
            <input
              type="date"
              value={filters.date_from}
              onChange={(e) =>
                setFilters({ ...filters, date_from: e.target.value })
              }
            />
          </label>
          <label>
            结束日期（UTC）
            <input
              type="date"
              value={filters.date_to}
              onChange={(e) =>
                setFilters({ ...filters, date_to: e.target.value })
              }
            />
          </label>
          <button className="primary" disabled={resource.loading}>
            筛选
          </button>
          <button
            type="button"
            onClick={() => {
              setFilters(blank);
              setSubmitted(blank);
              setOffset(0);
              setError("");
            }}
          >
            重置
          </button>
        </form>
        {resource.loading ? (
          <Loading />
        ) : !rows.length ? (
          <EmptyState
            icon="list"
            title={resource.error ? "审计加载失败" : "暂无操作记录"}
            description="请检查权限、筛选条件和服务状态后重试。"
          />
        ) : (
          <div className="table-scroll">
            <table>
              <thead>
                <tr>
                  <th>操作时间（本地时区）</th>
                  <th>用户 ID</th>
                  <th>操作类型</th>
                  <th>资源 ID</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((row) => (
                  <tr key={row.id}>
                    <td>{formatDate(row.created_at, true)}</td>
                    <td className="mono">{row.actor_id}</td>
                    <td>
                      <span className="tag-chip">
                        {actions[row.action] ?? row.action}
                      </span>
                    </td>
                    <td className="mono">{row.resource_id ?? "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        {resource.data && (
          <Pagination
            page={Math.floor(offset / 20) + 1}
            total={resource.data.total}
            pageSize={20}
            onChange={(page) => setOffset((page - 1) * 20)}
          />
        )}
      </section>
      <p className="muted">日志只读；导出仅包含时间、用户、动作和资源标识。</p>
    </div>
  );
}
