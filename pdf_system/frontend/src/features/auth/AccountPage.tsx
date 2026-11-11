import { useState, type FormEvent } from "react";
import { useAuth } from "../../app/AuthProvider";
import { api } from "../../shared/http";
import { errorText, formatDate, roleNames } from "../management/management";
import { Icon, Notice, PageHeading } from "../management/ui";

export default function AccountPage() {
  const { me, refresh, adoptToken } = useAuth();
  const [oldPassword, setOldPassword] = useState("");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  async function changePassword(event: FormEvent) {
    event.preventDefault();
    if (busy) return;
    setError("");
    setMessage("");
    if (!/[a-z]/i.test(password) || !/\d/.test(password)) {
      setError("新密码需要同时包含字母和数字。");
      return;
    }
    if (password !== confirm) {
      setError("两次输入的新密码不一致。");
      return;
    }
    setBusy(true);
    try {
      const result = await api<{ access_token: string }>(
        "/auth/change-password",
        {
          method: "POST",
          body: JSON.stringify({
            old_password: oldPassword,
            new_password: password,
          }),
        },
      );
      adoptToken(result.access_token);
      setMessage("密码已修改，其他会话已失效，当前登录已续期。");
      setOldPassword("");
      setPassword("");
      setConfirm("");
    } catch (e) {
      setError(errorText(e));
    } finally {
      setBusy(false);
    }
  }
  return (
    <div className="workspace-page">
      <PageHeading
        eyebrow="YOUR ACCOUNT"
        title="账户设置"
        description="查看账户信息，管理密码与当前登录会话。"
      />
      {error && <Notice tone="error">{error}</Notice>}
      {message && <Notice tone="success">{message}</Notice>}
      <div className="two-column">
        <section className="panel">
          <div className="panel-heading">
            <h2>个人信息</h2>
            <Icon name="users" />
          </div>
          <div className="panel-body">
            <div className="profile-heading">
              <span className="avatar large">
                {(me?.display_name || me?.email || "U")
                  .slice(0, 1)
                  .toUpperCase()}
              </span>
              <div>
                <h2>{me?.display_name || "未设置显示名称"}</h2>
                <span className="role-badge">{me && roleNames[me.role]}</span>
              </div>
            </div>
            <dl className="detail-list">
              <dt>邮箱地址</dt>
              <dd>{me?.email}</dd>
              <dt>账户 ID</dt>
              <dd className="mono">{me?.id}</dd>
              <dt>注册日期</dt>
              <dd>{formatDate(me?.created_at, true)}</dd>
              <dt>账户状态</dt>
              <dd>
                <span className="status-pill success">正常使用</span>
              </dd>
            </dl>
            <div className="security-session">
              <h3>当前登录会话</h3>
              <p className="muted">
                登录有效期由服务端管理。到期前可手动续期，续期后旧令牌立即失效。
              </p>
              <button
                disabled={busy}
                onClick={async () => {
                  setBusy(true);
                  setError("");
                  try {
                    await refresh();
                    setMessage("当前登录会话已续期。");
                  } catch (e) {
                    setError(errorText(e));
                  } finally {
                    setBusy(false);
                  }
                }}
              >
                <Icon name="refresh" />
                续期当前会话
              </button>
            </div>
          </div>
        </section>
        <section className="panel">
          <div className="panel-heading">
            <h2>修改密码</h2>
            <Icon name="lock" />
          </div>
          <form className="panel-body form-stack" onSubmit={changePassword}>
            <label>
              当前密码
              <input
                type="password"
                autoComplete="current-password"
                required
                maxLength={128}
                value={oldPassword}
                onChange={(e) => setOldPassword(e.target.value)}
              />
            </label>
            <label>
              新密码
              <input
                type="password"
                autoComplete="new-password"
                required
                minLength={8}
                maxLength={128}
                placeholder="至少 8 位，包含字母和数字"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
              />
            </label>
            <label>
              确认新密码
              <input
                type="password"
                autoComplete="new-password"
                required
                minLength={8}
                maxLength={128}
                value={confirm}
                onChange={(e) => setConfirm(e.target.value)}
              />
            </label>
            <p className="muted">
              修改成功后，所有旧会话将失效，当前账号会保持登录。
            </p>
            <button className="primary" disabled={busy}>
              {busy ? "正在提交…" : "保存新密码"}
            </button>
          </form>
        </section>
      </div>
    </div>
  );
}
