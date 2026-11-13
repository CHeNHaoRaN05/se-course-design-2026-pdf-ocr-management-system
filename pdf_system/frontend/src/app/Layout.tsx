import { useState } from "react";
import {
  Link,
  NavLink,
  Outlet,
  useLocation,
  useNavigate,
} from "react-router-dom";
import { useAuth } from "./AuthProvider";
import { Icon, Notice } from "../features/management/ui";
import { errorText, roleNames } from "../features/management/management";

const groups = [
  {
    label: "文档空间",
    items: [
      ["/files", "folder", "文件库"],
      ["/upload", "upload", "上传文档"],
      ["/trash", "trash", "回收站"],
    ],
  },
  {
    label: "发现与协作",
    items: [
      ["/search", "search", "全文检索"],
      ["/shares", "share", "我的分享"],
    ],
  },
  {
    label: "工作空间",
    items: [
      ["/stats", "chart", "配额与统计"],
      ["/account", "settings", "账户设置"],
    ],
  },
];
export default function Layout() {
  const { me, logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [query, setQuery] = useState("");
  const [menu, setMenu] = useState(false);
  const [error, setError] = useState("");
  const [leaving, setLeaving] = useState(false);
  const title =
    [
      ...groups.flatMap((group) => group.items),
      ["/admin/users", "", "用户与角色"],
      ["/admin/audit", "", "操作日志"],
    ].find(([path]) => location.pathname === path)?.[2] ?? "文档阅读";
  return (
    <div className={`workspace ${menu ? "menu-open" : ""}`}>
      <a className="skip-link" href="#main-content">
        跳到主要内容
      </a>
      {menu && (
        <button
          className="sidebar-backdrop"
          aria-label="关闭导航"
          onClick={() => setMenu(false)}
        />
      )}
      <aside className="sidebar">
        <Link to="/files" className="brand">
          <span className="brand-mark">
            <Icon name="file" size={25} />
          </span>
          <span>
            <strong>PDF 文档空间</strong>
            <small>LOCAL DOCUMENT WORKSPACE</small>
          </span>
        </Link>
        <div className="workspace-label">
          <span className="workspace-dot" />
          我的工作空间<span className="local-tag">本地</span>
        </div>
        <nav aria-label="主导航">
          {groups.map((group) => (
            <div className="nav-group" key={group.label}>
              <p>{group.label}</p>
              {group.items.map(([path, icon, label]) => (
                <NavLink
                  key={path}
                  to={path}
                  end={path === "/files"}
                  onClick={() => setMenu(false)}
                >
                  <Icon name={icon} />
                  {label}
                </NavLink>
              ))}
            </div>
          ))}
          {me?.role === "admin" && (
            <div className="nav-group">
              <p>系统管理</p>
              <NavLink to="/admin/users" onClick={() => setMenu(false)}>
                <Icon name="users" />
                用户与角色
              </NavLink>
              <NavLink to="/admin/audit" onClick={() => setMenu(false)}>
                <Icon name="list" />
                操作日志
              </NavLink>
            </div>
          )}
        </nav>
        <div className="sidebar-bottom">
          <div className="local-note">
            <Icon name="shield" size={21} />
            <div>
              <strong>文档存储在本地服务</strong>
              <small>上传、管理、检索，一处完成</small>
            </div>
          </div>
          <Link className="sidebar-user" to="/account">
            <span className="avatar">
              {(me?.display_name || me?.email || "U").slice(0, 1).toUpperCase()}
            </span>
            <span>
              <strong>{me?.display_name || me?.email}</strong>
              <small>{me && roleNames[me.role]}</small>
            </span>
            <Icon name="settings" size={17} />
          </Link>
        </div>
      </aside>
      <div className="workspace-body">
        <header className="topbar">
          <button
            className="icon-button mobile-menu"
            aria-label="展开导航"
            onClick={() => setMenu(true)}
          >
            <Icon name="menu" />
          </button>
          <div className="breadcrumb">
            工作空间
            <Icon name="chevron" size={13} />
            <strong>{title}</strong>
          </div>
          <div className="spacer" />
          <form
            className="global-search"
            onSubmit={(event) => {
              event.preventDefault();
              if (query.trim()) {
                navigate(`/search?q=${encodeURIComponent(query.trim())}`);
                setQuery("");
              }
            }}
          >
            <Icon name="search" size={17} />
            <input
              aria-label="全局文档搜索"
              maxLength={100}
              placeholder="搜索文档内容…"
              value={query}
              onChange={(event) => setQuery(event.target.value)}
            />
            <kbd>↵</kbd>
          </form>
          <span className="role-badge">{me && roleNames[me.role]}</span>
          <button
            className="icon-button"
            title="退出登录"
            aria-label="退出登录"
            disabled={leaving}
            onClick={async () => {
              setLeaving(true);
              setError("");
              try {
                await logout();
              } catch (e) {
                setError(errorText(e));
              } finally {
                setLeaving(false);
              }
            }}
          >
            <Icon name="logout" />
          </button>
        </header>
        <main id="main-content" className="main-content" key={me?.id}>
          {error && <Notice tone="error">{error}</Notice>}
          {me?.role === "viewer" && (
            <Notice>
              当前为只读账号，可以浏览、检索和下载有权访问的文档。
            </Notice>
          )}
          <Outlet />
        </main>
        <footer className="workspace-footer">
          PDF 文件显示与管理系统<span>软件工程课程设计 · 2026</span>
        </footer>
      </div>
    </div>
  );
}
