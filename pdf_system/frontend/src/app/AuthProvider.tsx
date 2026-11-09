import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react";
import { api, tokenStore, TOKEN_KEY, TOKEN_CHANGED } from "../shared/http";
import { errorText, type UserInfo } from "../shared/management";

interface AuthState {
  token: string;
  me: UserInfo | null;
  ready: boolean;
  error: string;
  login: (email: string, password: string) => Promise<void>;
  register: (
    email: string,
    password: string,
    displayName: string,
  ) => Promise<void>;
  logout: () => Promise<void>;
  refresh: () => Promise<void>;
  adoptToken: (token: string) => void;
  retry: () => void;
}
const AuthContext = createContext<AuthState | null>(null);
export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setToken] = useState(tokenStore.get);
  const [me, setMe] = useState<UserInfo | null>(null);
  const [ready, setReady] = useState(false);
  const [error, setError] = useState("");
  const [revision, setRevision] = useState(0);
  const refreshing = useRef<Promise<void> | null>(null);
  useEffect(() => {
    const sync = () => setToken(tokenStore.get());
    const storage = (event: StorageEvent) => {
      if (event.key === TOKEN_KEY || event.key === null) {
        setMe(null);
        setReady(false);
        sync();
      }
    };
    window.addEventListener(TOKEN_CHANGED, sync);
    window.addEventListener("storage", storage);
    return () => {
      window.removeEventListener(TOKEN_CHANGED, sync);
      window.removeEventListener("storage", storage);
    };
  }, []);
  useEffect(() => {
    const controller = new AbortController();
    setError("");
    setReady(false);
    if (!token) {
      setMe(null);
      setReady(true);
      return;
    }
    void api<UserInfo>("/auth/me", { signal: controller.signal }, token)
      .then((user) => {
        if (!controller.signal.aborted) setMe(user);
      })
      .catch((e) => {
        if (!controller.signal.aborted) {
          setMe(null);
          setError(errorText(e));
        }
      })
      .finally(() => {
        if (!controller.signal.aborted) setReady(true);
      });
    return () => controller.abort();
  }, [token, revision]);
  const adoptToken = useCallback((value: string) => {
    tokenStore.set(value);
    setToken(value);
  }, []);
  const apply = useCallback(
    async (path: string, body: unknown) => {
      const result = await api<{ access_token: string }>(
        path,
        { method: "POST", body: JSON.stringify(body) },
        "",
      );
      adoptToken(result.access_token);
    },
    [adoptToken],
  );
  const refresh = useCallback(() => {
    if (refreshing.current) return refreshing.current;
    const current = tokenStore.get();
    refreshing.current = api<{ access_token: string }>(
      "/auth/refresh",
      { method: "POST" },
      current,
    )
      .then((result) => {
        if (tokenStore.get() === current) adoptToken(result.access_token);
      })
      .finally(() => {
        refreshing.current = null;
      });
    return refreshing.current;
  }, [adoptToken]);
  const logout = useCallback(async () => {
    // 吊销失败时保留会话并报告失败，避免误称已在服务器退出。
    await api("/auth/logout", { method: "POST" });
    tokenStore.clear();
    setToken("");
    setMe(null);
  }, []);
  const value = useMemo<AuthState>(
    () => ({
      token,
      me,
      ready,
      error,
      login: (email, password) => apply("/auth/login", { email, password }),
      register: (email, password, display_name) =>
        apply("/auth/register", { email, password, display_name }),
      logout,
      refresh,
      adoptToken,
      retry: () => setRevision((n) => n + 1),
    }),
    [token, me, ready, error, apply, logout, refresh, adoptToken],
  );
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
export function useAuth(): AuthState {
  const context = useContext(AuthContext);
  if (!context) throw new Error("useAuth 必须在 AuthProvider 内使用");
  return context;
}
