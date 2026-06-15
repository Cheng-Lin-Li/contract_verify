// Auth context: holds the current user, exposes login/logout, and gates routes.
import { createContext, useContext, useEffect, useMemo, useState, ReactNode } from "react";
import { api, getToken, setToken } from "../api/client";
import type { Role, User } from "../types";

interface AuthState {
  user: User | null;
  loading: boolean;
  login: (username: string, password: string) => Promise<void>;
  logout: () => void;
}

const AuthCtx = createContext<AuthState | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState<boolean>(true);

  useEffect(() => {
    if (!getToken()) { setLoading(false); return; }
    api.me().then(setUser).catch(() => setToken(null)).finally(() => setLoading(false));
  }, []);

  const value = useMemo<AuthState>(() => ({
    user,
    loading,
    async login(username, password) {
      await api.login(username, password);
      setUser(await api.me());
    },
    logout() { api.logout(); setUser(null); },
  }), [user, loading]);

  return <AuthCtx.Provider value={value}>{children}</AuthCtx.Provider>;
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthCtx);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}

export function hasRole(user: User | null, ...roles: Role[]): boolean {
  return !!user && roles.includes(user.role);
}
