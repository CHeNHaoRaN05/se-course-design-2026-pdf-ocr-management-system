import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import type { ReactNode } from "react";
import { ApiError, api, tokenStore } from "../shared/http";

interface Me {
  id: string;
  email: string;
  display_name: string;
  role: "user" | "viewer" | "admin";
  created_at: string;
}

interface AuthState {
  token: string;
  me: Me | null;
  ready: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string, displayName: string) => Promise<void>;
  logout: () => void;
  refresh: () => Promise<void>;
  adoptToken: (token: string) => void;
}

const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setToken] = useState(tokenStore.get());
  const [me, setMe] = useState<Me | null>(null);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    if (!token) {
      setMe(null);
      setReady(true);
      return;
    }
    api<Me>("/auth/me", {}, token)
      .then(setMe)
      .catch((error) => {
        if (error instanceof ApiError && error.status === 401) {
          tokenStore.clear();
          setToken("");
        }
      })
      .finally(() => setReady(true));
  }, [token]);

  const apply = useCallback(async (path: string, body: unknown) => {
    const result = await api<{ access_token: string }>(path, { method: "POST", body: JSON.stringify(body) });
    tokenStore.set(result.access_token);
    setToken(result.access_token);
  }, []);

  const refresh = useCallback(async () => {
    const result = await api<{ access_token: string }>("/auth/refresh", { method: "POST" });
    tokenStore.set(result.access_token);
    setToken(result.access_token);
  }, []);

  const adoptToken = useCallback((value: string) => {
    tokenStore.set(value);
    setToken(value);
  }, []);

  const value = useMemo<AuthState>(() => ({
    token,
    me,
    ready,
    login: (email, password) => apply("/auth/login", { email, password }),
    register: (email, password, display_name) => apply("/auth/register", { email, password, display_name }),
    logout: () => {
      api("/auth/logout", { method: "POST" }).catch(() => {});
      tokenStore.clear();
      setToken("");
      setMe(null);
    },
    refresh,
    adoptToken,
  }), [token, me, ready, apply, refresh, adoptToken]);

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthState {
  const value = useContext(AuthContext);
  if (!value) throw new Error("useAuth 必须在 AuthProvider 内使用");
  return value;
}
