import { useEffect, useState } from "react";
import { api } from "../../shared/http";
import { useAuth } from "../../app/AuthProvider";

interface QuotaOverview {
  files: number;
  storage_bytes: number;
  quota: { month: string; pages_reserved: number; pages_used: number; pages_committed: number };
}

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KiB`;
  return `${(bytes / 1024 / 1024).toFixed(1)} MiB`;
}

export default function StatsPage() {
  const { refresh, adoptToken } = useAuth();
  const [overview, setOverview] = useState<QuotaOverview | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const [oldPwd, setOldPwd] = useState("");
  const [newPwd, setNewPwd] = useState("");
  const [pwdMsg, setPwdMsg] = useState("");

  useEffect(() => {
    api<QuotaOverview>("/quota/overview")
      .then(setOverview)
      .catch((e) => setError(e instanceof Error ? e.message : "加载统计失败"));
  }, []);

  async function onRefresh() {
    setBusy(true);
    setError("");
    try {
      await refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : "刷新令牌失败");
    } finally {
      setBusy(false);
    }
  }

  async function onChangePassword(event: React.FormEvent) {
    event.preventDefault();
    setPwdMsg("");
    setBusy(true);
    try {
      const r = await api<{ access_token: string }>("/auth/change-password", {
        method: "POST",
        body: JSON.stringify({ old_password: oldPwd, new_password: newPwd }),
      });
      adoptToken(r.access_token);
      setPwdMsg("密码已修改，已为您续期登录");
      setOldPwd("");
      setNewPwd("");
    } catch (e) {
      setPwdMsg(e instanceof Error ? e.message : "修改密码失败");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div>
      <h2>统计看板</h2>
      {error && <p className="error">{error}</p>}
      <div className="card">
        <h3>我的资源</h3>
        {overview ? (
          <table>
            <tbody>
              <tr><td>文件数量</td><td>{overview.files}</td></tr>
              <tr><td>存储占用</td><td>{formatBytes(overview.storage_bytes)}</td></tr>
              <tr><td>本月识别额度（已提交）</td><td>{overview.quota.pages_committed} 页</td></tr>
              <tr><td>本月已用 / 已预留</td><td>{overview.quota.pages_used} / {overview.quota.pages_reserved} 页</td></tr>
              <tr><td>统计月份</td><td>{overview.quota.month}</td></tr>
            </tbody>
          </table>
        ) : (
          <p className="muted">加载中…</p>
        )}
      </div>

      <div className="card">
        <h3>账户安全</h3>
        <div className="row">
          <button className="primary" disabled={busy} onClick={onRefresh}>刷新令牌</button>
          <span className="muted">用当前有效令牌换新令牌，旧令牌立即失效</span>
        </div>
        <form onSubmit={onChangePassword} className="row" style={{ flexDirection: "column", alignItems: "stretch" }}>
          <input type="password" placeholder="原密码" value={oldPwd} onChange={(e) => setOldPwd(e.target.value)} />
          <input type="password" placeholder="新密码（至少 8 位）" value={newPwd} onChange={(e) => setNewPwd(e.target.value)} />
          <button className="primary" disabled={busy || newPwd.length < 8} style={{ alignSelf: "flex-start" }}>
            修改密码
          </button>
        </form>
        {pwdMsg && <p className="muted">{pwdMsg}</p>}
      </div>
    </div>
  );
}
