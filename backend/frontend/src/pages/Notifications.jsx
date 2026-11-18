import { useCallback, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { BellOff } from "lucide-react";
import api, { getErrorMessage } from "../services/api";
import { timeAgo } from "../utils";

export default function Notifications() {
  const navigate = useNavigate();
  const [data, setData] = useState(null);
  const [page, setPage] = useState(1);
  const [error, setError] = useState("");

  const load = useCallback(() => {
    api.get("/api/notifications", { params: { page, page_size: 15 } })
      .then((res) => setData(res.data))
      .catch((e) => setError(getErrorMessage(e)));
  }, [page]);
  useEffect(() => { load(); }, [load]);

  const changed = () => window.dispatchEvent(new Event("notifications:changed"));

  const open = async (n) => {
    if (!n.is_read) {
      try { await api.post(`/api/notifications/${n.id}/read`); changed(); } catch { /* opening the link matters more */ }
    }
    if (n.link) navigate(n.link); else load();
  };

  const markAll = async () => {
    try { await api.post("/api/notifications/read-all"); changed(); load(); } catch (e) { setError(getErrorMessage(e)); }
  };

  return (
    <section className="mx-auto max-w-3xl px-4 py-10">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <h1 className="text-3xl font-bold">Notifications</h1>
        {data && data.unread > 0 && <button onClick={markAll} className="btn-outline">Mark all as read ({data.unread})</button>}
      </div>

      {error && <p role="alert" className="mt-6 rounded-2xl bg-accent-100 p-4 text-accent-700">{error}</p>}
      {!data && !error && <p className="mt-8 text-slate-500">Loading…</p>}

      {data && data.items.length === 0 && (
        <div className="mt-6 rounded-2xl border border-dashed border-brand-200 bg-brand-50 p-10 text-center">
          <BellOff size={36} className="mx-auto text-brand-600" aria-hidden="true" />
          <h2 className="mt-3 text-xl font-bold">You are all caught up</h2>
          <p className="mt-1 text-slate-600">Updates about your requests and reviews will appear here.</p>
        </div>
      )}

      {data && data.items.length > 0 && (
        <ul className="mt-6 space-y-2">
          {data.items.map((n) => (
            <li key={n.id}>
              <button onClick={() => open(n)} className={`w-full rounded-2xl border p-4 text-left transition-colors hover:border-brand-600 ${n.is_read ? "border-slate-200" : "border-brand-200 bg-brand-50"}`}>
                <span className="flex items-start justify-between gap-3">
                  <span className="font-display font-bold text-brand-900">
                    {!n.is_read && <span className="mr-2 inline-block h-2.5 w-2.5 rounded-full bg-accent-600" aria-label="Unread" />}
                    {n.title}
                  </span>
                  <span className="shrink-0 text-sm text-slate-500">{timeAgo(n.created_at)}</span>
                </span>
                <span className="mt-1 block text-slate-700">{n.message}</span>
              </button>
            </li>
          ))}
        </ul>
      )}

      {data && data.pages > 1 && (
        <nav className="mt-8 flex items-center justify-center gap-4" aria-label="Pagination">
          <button className="btn-outline" disabled={page <= 1} onClick={() => setPage(page - 1)}>Previous</button>
          <span className="font-semibold text-brand-900">Page {data.page} of {data.pages}</span>
          <button className="btn-outline" disabled={page >= data.pages} onClick={() => setPage(page + 1)}>Next</button>
        </nav>
      )}
    </section>
  );
}
