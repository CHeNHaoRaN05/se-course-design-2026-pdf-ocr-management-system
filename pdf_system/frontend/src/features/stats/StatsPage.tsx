import { api } from "../../shared/http";
import {
  formatBytes,
  statusNames,
  type QuotaOverview,
} from "../../shared/management";
import {
  EmptyState,
  Icon,
  Loading,
  Notice,
  PageHeading,
} from "../../shared/ui";
import { useResource } from "../../shared/useResource";

export default function StatsPage() {
  const overview = useResource((signal) =>
    api<QuotaOverview>("/quota/overview", { signal }),
  );
  const caps = useResource((signal) =>
    api<{ quota_per_month: number; mounted: boolean }>(
      "/ocr-host/capabilities",
      { signal },
    ),
  );
  const usage = useResource((signal) =>
    api<{
      ocr: {
        jobs_by_status: Record<string, number>;
        recognized_page_results: number;
      };
    }>("/ocr-host/usage", { signal }),
  );
  const data = overview.data;
  const limit = caps.data?.quota_per_month;
  const committed = data?.quota.pages_committed ?? 0;
  const remaining = limit === undefined ? null : Math.max(0, limit - committed);
  const percent = limit ? Math.min(100, (committed / limit) * 100) : 0;
  const statuses = usage.data?.ocr.jobs_by_status ?? {};
  const total = Object.values(statuses).reduce((sum, value) => sum + value, 0);
  const completed =
    (statuses.succeeded ?? 0) +
    (statuses.partial_success ?? 0) +
    (statuses.failed ?? 0);
  const successRate = completed
    ? `${(((statuses.succeeded ?? 0) / completed) * 100).toFixed(1)}%`
    : "—";
  function reload() {
    overview.reload();
    caps.reload();
    usage.reload();
  }
  return (
    <div className="workspace-page">
      <PageHeading
        eyebrow="WORKSPACE INSIGHTS"
        title="配额与统计"
        description="了解自己的文档用量与处理情况，合理安排工作。"
        actions={
          <button onClick={reload} disabled={overview.loading}>
            <Icon name="refresh" />
            刷新数据
          </button>
        }
      />
      {overview.error && <Notice tone="error">{overview.error}</Notice>}
      <div className="metric-grid">
        <article className="metric-card">
          <div>
            <span>我的文档</span>
            <span className="stat-icon blue">
              <Icon name="folder" />
            </span>
          </div>
          <strong>
            {data?.files ?? "—"}
            <small>份</small>
          </strong>
          <p>当前账号未删除文档</p>
        </article>
        <article className="metric-card">
          <div>
            <span>存储占用</span>
            <span className="stat-icon amber">
              <Icon name="chart" />
            </span>
          </div>
          <strong>{data ? formatBytes(data.storage_bytes) : "—"}</strong>
          <p>当前账号文档总大小</p>
        </article>
        <article className="metric-card">
          <div>
            <span>本月已用额度</span>
            <span className="stat-icon green">
              <Icon name="file" />
            </span>
          </div>
          <strong>
            {data?.quota.pages_used ?? "—"}
            <small>页</small>
          </strong>
          <p>成功结算的识别页数</p>
        </article>
        <article className="metric-card">
          <div>
            <span>整任务成功率</span>
            <span className="stat-icon purple">
              <Icon name="check" />
            </span>
          </div>
          <strong>{usage.data ? successRate : "—"}</strong>
          <p>全部成功 / 已完成任务，不含取消</p>
        </article>
      </div>
      <div className="two-column">
        <section className="panel">
          <div className="panel-heading">
            <h2>本月识别配额</h2>
            <span className="role-badge">{data?.quota.month ?? "—"}</span>
          </div>
          <div className="panel-body">
            {overview.loading ? (
              <Loading />
            ) : data ? (
              <>
                <div className="quota-summary">
                  <strong>
                    {committed}
                    <small> / {limit ?? "—"} 页</small>
                  </strong>
                  <span>
                    {remaining === null
                      ? "额度上限暂不可用"
                      : `还可使用 ${remaining} 页`}
                  </span>
                </div>
                <div
                  className={`quota-track ${percent >= 90 ? "near-limit" : ""}`}
                  role="progressbar"
                  aria-label="本月配额占用"
                  aria-valuemin={0}
                  aria-valuemax={limit ?? 0}
                  aria-valuenow={committed}
                >
                  <span
                    style={{
                      width: `${limit ? Math.min(100, (data.quota.pages_used / limit) * 100) : 0}%`,
                    }}
                  />
                  <i
                    style={{
                      width: `${limit ? Math.min(100 - Math.min(100, (data.quota.pages_used / limit) * 100), (data.quota.pages_reserved / limit) * 100) : 0}%`,
                    }}
                  />
                </div>
                <div className="quota-legend">
                  <span>
                    <i />
                    已使用 {data.quota.pages_used} 页
                  </span>
                  <span>
                    <i />
                    已预留 {data.quota.pages_reserved} 页
                  </span>
                  <span>
                    <i />
                    剩余 {remaining ?? "—"} 页
                  </span>
                </div>
                {remaining === 0 && (
                  <Notice tone="warning">
                    本月额度已用完，新的识别任务将受到限制。
                  </Notice>
                )}
                <div className="info-box">
                  <Icon name="info" />
                  <p>
                    任务提交时预留额度，完成后结算成功页。未完成的预留量也会计入当月占用。
                  </p>
                </div>
              </>
            ) : (
              <EmptyState
                title="统计暂不可用"
                description="检查服务状态后重新加载。"
              />
            )}
          </div>
        </section>
        <section className="panel">
          <div className="panel-heading">
            <h2>任务状态分布</h2>
            <span className="muted">当前账号 · 全部时间</span>
          </div>
          <div className="panel-body">
            {usage.loading ? (
              <Loading />
            ) : !usage.data ? (
              <EmptyState
                icon="chart"
                title="任务统计暂不可用"
                description={
                  caps.data?.mounted === false
                    ? "OCR 服务未挂载，文档管理仍可正常使用。"
                    : "无法获取任务统计，请稍后重试。"
                }
              />
            ) : !total ? (
              <EmptyState
                icon="chart"
                title="还没有处理记录"
                description="文档开始识别后，将在这里看到状态分布。"
              />
            ) : (
              <div className="status-chart">
                {Object.entries(statuses).map(([status, count]) => (
                  <div key={status}>
                    <span>{statusNames[status] ?? status}</span>
                    <div className="chart-track">
                      <i
                        className={status}
                        style={{ width: `${(count / total) * 100}%` }}
                      />
                    </div>
                    <strong>{count}</strong>
                  </div>
                ))}
                <p className="muted">
                  共 {total} 个任务 · 已产生{" "}
                  {usage.data.ocr.recognized_page_results} 页成功结果
                </p>
              </div>
            )}
          </div>
        </section>
      </div>
      <section className="panel stats-notes">
        <Icon name="info" />
        <div>
          <h3>关于数据口径</h3>
          <p>
            本页使用服务端真实用量，管理员也仅显示自己的配额。当前接口尚未提供存储容量上限、每日识别趋势和平均耗时，因此未估算这些指标。
          </p>
          {caps.error && (
            <p className="error">配额上限读取失败：{caps.error}</p>
          )}
        </div>
      </section>
    </div>
  );
}
