import { useState } from "react";
import { Navigate } from "react-router-dom";
import { useAuth } from "../../app/AuthProvider";

export default function LoginPage() {
  const { token, login, register } = useAuth();
  const [mode, setMode] = useState<"login" | "register">("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  if (token) return <Navigate to="/files" replace />;

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    setError("");
    setBusy(true);
    try {
      if (mode === "login") await login(email, password);
      else await register(email, password, displayName);
    } catch (e) {
      setError(e instanceof Error ? e.message : "请求失败");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="card" style={{ maxWidth: 420, margin: "80px auto" }}>
      <h2>{mode === "login" ? "登录" : "注册"}</h2>
      <form onSubmit={submit} className="row" style={{ flexDirection: "column", alignItems: "stretch" }}>
        <input placeholder="邮箱" value={email} onChange={(e) => setEmail(e.target.value)} />
        {mode === "register" && (
          <input placeholder="昵称（可留空）" value={displayName} onChange={(e) => setDisplayName(e.target.value)} />
        )}
        <input type="password" placeholder="密码（至少 8 位）" value={password} onChange={(e) => setPassword(e.target.value)} />
        <button className="primary" disabled={busy}>{mode === "login" ? "登录" : "注册并登录"}</button>
      </form>
      {error && <p className="error">{error}</p>}
      <p className="muted">
        <a href="#" onClick={(e) => { e.preventDefault(); setMode(mode === "login" ? "register" : "login"); }}>
          {mode === "login" ? "没有账号？去注册" : "已有账号？去登录"}
        </a>
      </p>
    </div>
  );
}
