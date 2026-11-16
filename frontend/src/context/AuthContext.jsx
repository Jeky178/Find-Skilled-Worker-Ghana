import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import api, { tokenStore } from "../services/api";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(Boolean(tokenStore.get()));

  const logout = useCallback(() => {
    tokenStore.clear();
    setUser(null);
  }, []);

  // Restore the session on page load.
  useEffect(() => {
    if (!tokenStore.get()) return;
    api.get("/api/auth/me")
      .then((res) => setUser(res.data))
      .catch(() => tokenStore.clear())
      .finally(() => setLoading(false));
  }, []);

  // The API client fires this when a token is rejected.
  useEffect(() => {
    window.addEventListener("auth:expired", logout);
    return () => window.removeEventListener("auth:expired", logout);
  }, [logout]);

  const startSession = (data) => {
    tokenStore.set(data.access_token);
    setUser(data.user);
    return data.user;
  };

  const login = async (email, password) =>
    startSession((await api.post("/api/auth/login", { email, password })).data);

  const register = async (payload) =>
    startSession((await api.post("/api/auth/register", payload)).data);

  const value = useMemo(() => ({ user, loading, login, register, logout }), [user, loading, logout]);
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export const useAuth = () => {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used inside <AuthProvider>");
  return ctx;
};
