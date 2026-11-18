import { useEffect, useState } from "react";
import api from "../services/api";

/** "checking" | "online" | "offline" — pings the backend so problems are explained clearly. */
export default function useServerStatus() {
  const [status, setStatus] = useState("checking");
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    let cancelled = false;
    setStatus("checking");
    api.get("/api/health", { timeout: 6000 })
      .then(() => !cancelled && setStatus("online"))
      .catch(() => !cancelled && setStatus("offline"));
    return () => { cancelled = true; };
  }, [attempt]);

  return { status, recheck: () => setAttempt((n) => n + 1) };
}
