import { lazy, Suspense } from "react";
import { Navigate, Route, Routes, useLocation } from "react-router-dom";
import Layout from "./Layout";
import { useAuth } from "./AuthProvider";
import { tokenStore } from "../shared/http";
import { EmptyState, Loading, Notice } from "../features/management/ui";
import LoginPage from "../features/auth/LoginPage";
const FilesPage = lazy(() => import("../features/files/FilesPage"));
const UploadPage = lazy(() => import("../features/files/UploadPage"));
const TrashPage = lazy(() => import("../features/files/TrashPage"));
const ReaderPage = lazy(() => import("../features/reader/ReaderPage"));
const SearchPage = lazy(() => import("../features/search/SearchPage"));
const StatsPage = lazy(() => import("../features/stats/StatsPage"));
const AccountPage = lazy(() => import("../features/auth/AccountPage"));
const SharesPage = lazy(() => import("../features/share/SharesPage"));
const PublicSharePage = lazy(() => import("../features/share/PublicSharePage"));
const UsersPage = lazy(() => import("../features/admin/UsersPage"));
const AuditPage = lazy(() => import("../features/admin/AuditPage"));

function Guard({ children }: { children: JSX.Element }) {
  const { token, me, ready, error, retry } = useAuth();
  const location = useLocation();
  if (!token)
    return (
      <Navigate
        to="/login"
        state={{ from: location.pathname + location.search }}
        replace
      />
    );
  if (!ready && !me) return <Loading text="正在验证登录…" />;
  if (!me)
    return (
      <div className="auth-recovery">
        <Notice tone="error">{error || "无法读取账户信息。"}</Notice>
        <button onClick={retry}>重试</button>
        <button onClick={() => tokenStore.clear()}>返回登录</button>
      </div>
    );
  return children;
}
function AdminGuard({ children }: { children: JSX.Element }) {
  const { me } = useAuth();
  return me?.role === "admin" ? (
    children
  ) : (
    <EmptyState
      icon="shield"
      title="此页面仅管理员可访问"
      description="如需管理权限，请联系管理员。"
    />
  );
}
export default function AppRoutes() {
  return (
    <Suspense fallback={<Loading text="正在打开页面…" />}>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/share/:token" element={<PublicSharePage />} />
        <Route
          element={
            <Guard>
              <Layout />
            </Guard>
          }
        >
          <Route path="/files" element={<FilesPage />} />
          <Route path="/upload" element={<UploadPage />} />
          <Route path="/trash" element={<TrashPage />} />
          <Route
            path="/files/:fileId"
            element={
              <div className="reader-area">
                <ReaderPage />
              </div>
            }
          />
          <Route path="/search" element={<SearchPage />} />
          <Route path="/stats" element={<StatsPage />} />
          <Route path="/shares" element={<SharesPage />} />
          <Route path="/account" element={<AccountPage />} />
          <Route
            path="/admin/users"
            element={
              <AdminGuard>
                <UsersPage />
              </AdminGuard>
            }
          />
          <Route
            path="/admin/audit"
            element={
              <AdminGuard>
                <AuditPage />
              </AdminGuard>
            }
          />
        </Route>
        <Route path="*" element={<Navigate to="/files" replace />} />
      </Routes>
    </Suspense>
  );
}
