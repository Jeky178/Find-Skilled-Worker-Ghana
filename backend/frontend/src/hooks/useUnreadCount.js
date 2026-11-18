import { useCallback, useEffect, useState } from "react";
import { useLocation } from "react-router-dom";
import api from "../services/api";
import { useAuth } from "../context/AuthContext";

/** Unread notification count for the bell. Refreshes every 30 s, on navigation, and when notifications change. */
export default function useUnreadCount() {
  const { user } = useAuth();
  const { pathname } = useLocation();
  const [count, setCount] = useState(0);

  const refresh = useCallback(() => {
    if (!user) { setCount(0); return; }
    api.get("/api/notifications/unread-count").then((res) => setCount(res.data.unread)).catch(() => {});
  }, [user]);

  useEffect(() => { refresh(); }, [refresh, pathname]);

  useEffect(() => {
    const timer = setInterval(refresh, 30000);
    window.addEventListener("notifications:changed", refresh);
    return () => {
      clearInterval(timer);
      window.removeEventListener("notifications:changed", refresh);
    };
  }, [refresh]);

  return count;
}
