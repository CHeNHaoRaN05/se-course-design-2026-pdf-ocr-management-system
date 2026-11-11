import { useState, useEffect, type FormEvent } from "react";
import { Navigate, useLocation } from "react-router-dom";
import { useAuth } from "../../app/AuthProvider";
import { Icon, Loading, Notice } from "../management/ui";
import { errorText } from "../management/management";

export default function LoginPage() {
  const { token, login, register, ready } = useAuth();
  const location = useLocation();
  const [logoutNotice, setLogoutNotice] = useState("");
  useEffect(() => {
    const read = () => {
      try {
        setLogoutNotice(sessionStorage.getItem("pdf_logout_notice") ?? "");
      } catch {
        /* no storage */
      }
    };
    read();
    const timer = window.setInterval(read, 500);
    return () => {
      window.clearInterval(timer);
      try {
        sessionStorage.removeItem("pdf_logout_notice");
      } catch {
        /* no storage */
      }
    };
  }, []);
  const [mode, setMode] = useState<"login" | "register">("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [show, setShow] = useState(false);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const from = (location.state as { from?: string } | null)?.from;
  if (token)
    return (
      <Navigate
        to={
          from?.startsWith("/") &&
          !from.startsWith("//") &&
          !from.startsWith("/login")
            ? from
            : "/files"
        }
        replace
      />
    );
  async function submit(event: FormEvent) {
    event.preventDefault();
    if (busy) return;
    setError("");
    if (
      mode === "register" &&
      (!/[A-Za-z]/.test(password) || !/\d/.test(password))
    ) {
      setError("密码需要同时包含字母和数字。");
      return;
    }
    if (mode === "register" && password !== confirm) {
      setError("两次输入的密码不一致。");
      return;
    }
    setBusy(true);
    try {
      if (mode === "login") await login(email.trim(), password);
      else await register(email.trim(), password, displayName.trim());
    } catch (e) {
      setError(errorText(e));
    } finally {
      setBusy(false);
    }
  }
  return (
    <div className="auth-page">
      <section className="auth-story">
        <div className="brand">
          <span className="brand-mark">
            <Icon name="file" size={27} />
          </span>
          <strong>PDF 文档空间</strong>
        </div>
        <div className="auth-story-body">
          <div className="eyebrow">YOUR KNOWLEDGE, ORGANIZED.</div>
          <h1>
            让每一份文档，
            <br />
            都有迹可循。
          </h1>
          <p>
            从文件归档到内容检索，
            <br />
            让散落的资料成为井然有序的知识。
          </p>
          <div className="document-art" aria-hidden="true">
            <div className="art-folder" />
            <div className="art-sheet">
              <span>DOCUMENT</span>
              <i />
              <i />
              <i />
              <div>
                <Icon name="check" />
                已归档
              </div>
            </div>
            <div className="art-chip">
              <Icon name="search" />
              让内容触手可及
            </div>
          </div>
        </div>
        <div className="auth-security">
          <Icon name="shield" />
          本地部署 · 中文优先 · 安全存储
        </div>
      </section>
      <section className="auth-form-panel">
        <div className="auth-form">
          <div className="eyebrow">欢迎使用文档工作空间</div>
          <h2>{mode === "login" ? "欢迎回来" : "创建你的账号"}</h2>
          <p className="muted">
            {mode === "login"
              ? "登录后，继续整理和探索你的文档。"
              : "只需几步，开启有序的文档管理。"}
          </p>
          <div className="segmented auth-tabs">
            <button
              type="button"
              className={mode === "login" ? "active" : ""}
              disabled={busy}
              onClick={() => {
                setMode("login");
                setError("");
              }}
            >
              登录
            </button>
            <button
              type="button"
              className={mode === "register" ? "active" : ""}
              disabled={busy}
              onClick={() => {
                setMode("register");
                setError("");
              }}
            >
              注册
            </button>
          </div>
          {logoutNotice && <Notice tone="warning">{logoutNotice}</Notice>}
          {error && <Notice tone="error">{error}</Notice>}
          {!ready ? (
            <Loading />
          ) : (
            <form onSubmit={submit} className="form-stack">
              <label>
                邮箱地址
                <input
                  type="email"
                  autoComplete="username"
                  maxLength={190}
                  required
                  placeholder="name@example.com"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                />
              </label>
              {mode === "register" && (
                <label>
                  显示名称 <span className="muted">（可选）</span>
                  <input
                    autoComplete="nickname"
                    maxLength={64}
                    placeholder="如何称呼你"
                    value={displayName}
                    onChange={(e) => setDisplayName(e.target.value)}
                  />
                </label>
              )}
              <label>
                密码
                <div className="password-field">
                  <input
                    aria-label="密码"
                    type={show ? "text" : "password"}
                    autoComplete={
                      mode === "login" ? "current-password" : "new-password"
                    }
                    required
                    minLength={mode === "register" ? 8 : 1}
                    maxLength={128}
                    placeholder={
                      mode === "register"
                        ? "至少 8 位，包含字母和数字"
                        : "输入你的密码"
                    }
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                  />
                  <button
                    type="button"
                    onClick={() => setShow(!show)}
                    aria-label={show ? "隐藏密码" : "显示密码"}
                  >
                    {show ? "隐藏" : "显示"}
                  </button>
                </div>
              </label>
              {mode === "register" && (
                <label>
                  确认密码
                  <input
                    type="password"
                    autoComplete="new-password"
                    required
                    minLength={8}
                    maxLength={128}
                    placeholder="再次输入密码"
                    value={confirm}
                    onChange={(e) => setConfirm(e.target.value)}
                  />
                </label>
              )}
              <button className="primary auth-submit" disabled={busy}>
                {busy
                  ? "正在提交…"
                  : mode === "login"
                    ? "登录工作空间"
                    : "注册并登录"}
                <Icon name="chevron" size={17} />
              </button>
            </form>
          )}
          <p className="auth-footnote">
            <Icon name="lock" size={14} />
            使用团队部署的账号与服务，无需第三方账号
          </p>
        </div>
        <footer>PDF 文件显示与管理系统 · 软件工程课程设计</footer>
      </section>
    </div>
  );
}
