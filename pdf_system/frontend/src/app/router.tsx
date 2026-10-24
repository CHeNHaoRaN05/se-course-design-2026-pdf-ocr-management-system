import { Navigate, Route, Routes } from "react-router-dom";
import Layout from "./Layout";
import { useAuth } from "./AuthProvider";
import LoginPage from "../features/auth/LoginPage";
import FilesPage from "../features/files/FilesPage";
import ReaderPage from "../features/reader/ReaderPage";
import SearchPage from "../features/search/SearchPage";
import StatsPage from "../features/stats/StatsPage";

function Guard({ children }: { children: JSX.Element }) {
  const { token } = useAuth();
  return token ? children : <Navigate to="/login" replace />;
}

export default function AppRoutes() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route element={<Guard><Layout /></Guard>}>
        <Route path="/files" element={<FilesPage />} />
        <Route path="/files/:fileId" element={<ReaderPage />} />
        <Route path="/search" element={<SearchPage />} />
        <Route path="/stats" element={<StatsPage />} />
      </Route>
      <Route path="*" element={<Navigate to="/files" replace />} />
    </Routes>
  );
}
