import { NavLink, Outlet } from "react-router-dom";
import { useAuth } from "./AuthProvider";

export default function Layout() {
  const { me, logout } = useAuth();
  return (
    <div className="layout">
      <header className="topbar">
        <strong>PDF 文件显示与管理系统</strong>
        <nav>
          <NavLink to="/files">文件</NavLink>
          <NavLink to="/search">全文检索</NavLink>
        </nav>
        <span className="spacer" />
        <span>{me ? `${me.display_name}（${me.role}）` : "未登录"}</span>
        <button onClick={logout}>退出</button>
      </header>
      <main>
        <Outlet />
      </main>
    </div>
  );
}
