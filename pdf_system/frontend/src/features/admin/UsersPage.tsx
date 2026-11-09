import { useState, type FormEvent } from "react";
import { useAuth } from "../../app/AuthProvider";
import { api, ApiError } from "../../shared/http";
import {
  errorText,
  formatDate,
  roleNames,
  type Role,
  type UserInfo,
} from "../../shared/management";
import { Icon, Loading, Modal, Notice, PageHeading } from "../../shared/ui";
import { useResource } from "../../shared/useResource";

export default function UsersPage() {
  const { me } = useAuth();
  const [known, setKnown] = useState<UserInfo[]>([]);
  const users = useResource(async (signal) => {
    try {
      const items: UserInfo[] = [];
      for (let offset = 0; ; offset += 100) {
        const page = await api<UserInfo[]>(
          `/auth/users?limit=100&offset=${offset}`,
          { signal },
        );
        items.push(...page);
        if (page.length < 100) break;
      }
      return { items, limited: false };
    } catch (e) {
      if (e instanceof ApiError && [404, 405].includes(e.status))
        return { items: me ? [me] : [], limited: true };
      throw e;
    }
  });
  const [id, setId] = useState("");
  const [operation, setOperation] = useState("role");
  const [role, setRole] = useState<Role>("user");
  const [disabled, setDisabled] = useState("true");
  const [pending, setPending] = useState<{
    id: string;
    operation: string;
    role: Role;
    disabled: boolean;
  } | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [q, setQ] = useState("");
  const records = [
    ...new Map(
      [...(users.data?.items ?? []), ...known].map((user) => [user.id, user]),
    ).values(),
  ].filter((user) =>
    `${user.email} ${user.display_name} ${user.id}`
      .toLowerCase()
      .includes(q.toLowerCase()),
  );
  function prepare(event: FormEvent) {
    event.preventDefault();
    setError("");
    setMessage("");
    if (id.trim() === me?.id) {
      setError("请使用其他管理员账号修改当前账号，避免失去管理权限。");
      return;
    }
    setPending({
      id: id.trim(),
      operation,
      role,
      disabled: disabled === "true",
    });
  }
  async function save() {
    if (!pending || busy) return;
    setBusy(true);
    setError("");
    try {
      const user = await api<UserInfo>(
        `/auth/users/${encodeURIComponent(pending.id)}/${pending.operation}`,
        {
          method: "PATCH",
          body: JSON.stringify(
            pending.operation === "role"
              ? { role: pending.role }
              : { disabled: pending.disabled },
          ),
        },
      );
      setKnown((old) => [...old.filter((item) => item.id !== user.id), user]);
      setPending(null);
      setMessage(`已更新 ${user.display_name || user.email} 的账户设置。`);
      users.reload();
    } catch (e) {
      setError(errorText(e));
    } finally {
      setBusy(false);
    }
  }
  return (
    <div className="workspace-page">
      <PageHeading
        eyebrow="WORKSPACE ADMINISTRATION"
        title="用户与角色"
        description="管理协作成员的访问权限和账号状态。"
        actions={
          <button onClick={users.reload} disabled={users.loading}>
            <Icon name="refresh" />
            刷新
          </button>
        }
      />
      {users.data?.limited && (
        <Notice tone="warning">
          当前后端尚未开放用户列表。下方显示当前账号及本次已操作账号；输入目标用户
          ID，仍可使用现有接口调整角色或启用状态。
        </Notice>
      )}
      {(error || users.error) && (
        <Notice tone="error">{error || users.error}</Notice>
      )}
      {message && <Notice tone="success">{message}</Notice>}
      <section className="panel">
        <div className="panel-heading">
          <h2>{users.data?.limited ? "已知账号" : "用户列表"}</h2>
          <input
            aria-label="搜索用户"
            value={q}
            placeholder="搜索名称、邮箱或 ID…"
            onChange={(e) => setQ(e.target.value)}
          />
        </div>
        {users.loading ? (
          <Loading />
        ) : (
          <div className="table-scroll">
            <table>
              <thead>
                <tr>
                  <th>用户</th>
                  <th>角色</th>
                  <th>状态</th>
                  <th>注册日期</th>
                  <th>操作</th>
                </tr>
              </thead>
              <tbody>
                {records.map((user) => (
                  <tr key={user.id}>
                    <td>
                      <strong>
                        {user.display_name || user.email}
                        {user.id === me?.id && (
                          <span className="count-badge">我</span>
                        )}
                      </strong>
                      <small className="cell-sub">{user.email}</small>
                      <small className="cell-sub mono">{user.id}</small>
                    </td>
                    <td>
                      <span className="role-badge">{roleNames[user.role]}</span>
                    </td>
                    <td>
                      <span
                        className={`status-pill ${user.disabled ? "failed" : "success"}`}
                      >
                        {user.disabled ? "已禁用" : "正常"}
                      </span>
                    </td>
                    <td>{formatDate(user.created_at)}</td>
                    <td>
                      <button
                        disabled={user.id === me?.id}
                        onClick={() => {
                          setId(user.id);
                          setRole(user.role);
                          setDisabled(user.disabled ? "false" : "true");
                          document
                            .getElementById("user-management-id")
                            ?.focus();
                        }}
                      >
                        管理
                      </button>
                    </td>
                  </tr>
                ))}
                {!records.length && (
                  <tr>
                    <td colSpan={5}>
                      <p className="muted">没有符合条件的账号。</p>
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        )}
      </section>
      <div className="two-column section-gap">
        <section className="panel">
          <div className="panel-heading">
            <h2>账号权限调整</h2>
            <Icon name="shield" />
          </div>
          <form className="panel-body form-stack" onSubmit={prepare}>
            <label>
              用户 ID
              <input
                id="user-management-id"
                required
                pattern="[a-fA-F0-9]{32}"
                maxLength={32}
                placeholder="输入目标用户的 32 位 ID"
                value={id}
                onChange={(e) => setId(e.target.value)}
              />
            </label>
            <label>
              操作
              <select
                value={operation}
                onChange={(e) => setOperation(e.target.value)}
              >
                <option value="role">更改角色</option>
                <option value="disabled">启用 / 禁用账号</option>
              </select>
            </label>
            {operation === "role" ? (
              <label>
                目标角色
                <select
                  value={role}
                  onChange={(e) => setRole(e.target.value as Role)}
                >
                  {Object.entries(roleNames).map(([value, label]) => (
                    <option key={value} value={value}>
                      {label}
                    </option>
                  ))}
                </select>
              </label>
            ) : (
              <label>
                目标状态
                <select
                  value={disabled}
                  onChange={(e) => setDisabled(e.target.value)}
                >
                  <option value="true">禁用账号</option>
                  <option value="false">启用账号</option>
                </select>
              </label>
            )}
            <button className="primary" disabled={busy}>
              检查并确认修改
            </button>
          </form>
        </section>
        <section className="panel">
          <div className="panel-heading">
            <h2>角色权限</h2>
          </div>
          <div className="table-scroll">
            <table className="permission-matrix">
              <thead>
                <tr>
                  <th>能力</th>
                  <th>普通用户</th>
                  <th>只读用户</th>
                  <th>管理员</th>
                </tr>
              </thead>
              <tbody>
                {[
                  ["阅读与检索", true, true, true],
                  ["上传与文件管理", true, false, true],
                  ["下载文档", true, true, true],
                  ["创建 / 撤销分享", true, false, true],
                  ["用户与角色管理", false, false, true],
                  ["全局审计", false, false, true],
                ].map(([label, ...permissions]) => (
                  <tr key={String(label)}>
                    <td>{label}</td>
                    {permissions.map((allowed, i) => (
                      <td
                        key={i}
                        className={allowed ? "success-text" : "muted"}
                      >
                        {allowed ? "允许" : "—"}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p className="panel-body muted">
            角色控制界面入口，资源归属与操作权限由服务端再次校验。
          </p>
        </section>
      </div>
      {pending && (
        <Modal
          title="确认调整账号"
          onClose={() => setPending(null)}
          busy={busy}
        >
          <dl className="detail-list">
            <dt>用户 ID</dt>
            <dd className="mono">{pending.id}</dd>
            <dt>变更为</dt>
            <dd>
              {pending.operation === "role"
                ? roleNames[pending.role]
                : pending.disabled
                  ? "禁用"
                  : "启用"}
            </dd>
          </dl>
          {pending.operation === "disabled" && pending.disabled && (
            <Notice tone="warning">禁用后，此用户现有登录会话将失效。</Notice>
          )}
          {error && <Notice tone="error">{error}</Notice>}
          <div className="modal-actions">
            <button disabled={busy} onClick={() => setPending(null)}>
              取消
            </button>
            <button
              className="primary"
              disabled={busy}
              onClick={() => void save()}
            >
              {busy ? "正在保存…" : "确认修改"}
            </button>
          </div>
        </Modal>
      )}
    </div>
  );
}
