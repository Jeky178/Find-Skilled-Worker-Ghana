import { useCallback, useEffect, useState } from "react";
import { useOutletContext } from "react-router-dom";
import api, { getErrorMessage } from "../../services/api";
import { timeAgo } from "../../utils";

export default function Messages() {
  const { refreshStats } = useOutletContext();
  const [unreadOnly, setUnreadOnly] = useState(false);
  const [items, setItems] = useState(null);
  const [error, setError] = useState("");

  const load = useCallback(() => {
    api.get("/api/contact", { params: { unread_only: unreadOnly || undefined, limit: 100 } }).then((r) => setItems(r.data)).catch((e) => setError(getErrorMessage(e)));
  }, [unreadOnly]);
  useEffect(() => { load(); }, [load]);

  const markRead = async (id) => {
    try { await api.patch(`/api/contact/${id}/read`); setItems((xs) => xs.map((m) => (m.id === id ? { ...m, is_read: true } : m))); refreshStats(); } catch (e) { setError(getErrorMessage(e)); }
  };

  return (
    <div>
      <div className="flex flex-wrap items-end justify-between gap-3">
        <h2 className="text-2xl font-bold">Contact messages</h2>
        <label className="flex items-center gap-2 font-semibold text-brand-900"><input type="checkbox" className="h-4 w-4 accent-brand-800" checked={unreadOnly} onChange={(e) => setUnreadOnly(e.target.checked)} /> Unread only</label>
      </div>
      {error && <p role="alert" className="mt-4 rounded-xl bg-accent-100 p-3 text-accent-700">{error}</p>}
      {items && items.length === 0 && <p className="mt-6 rounded-2xl bg-brand-50 p-6 text-slate-700">No messages.</p>}
      <ul className="mt-5 space-y-3">
        {items?.map((m) => (
          <li key={m.id} className={`rounded-2xl border p-5 ${m.is_read ? "border-slate-200" : "border-brand-200 bg-brand-50"}`}>
            <div className="flex flex-wrap items-start justify-between gap-2">
              <p className="font-display font-bold text-brand-900">{!m.is_read && <span className="mr-2 inline-block h-2.5 w-2.5 rounded-full bg-accent-600" aria-label="Unread" />}{m.name} <span className="font-normal text-slate-600">· {m.topic}</span></p>
              <span className="text-sm text-slate-500">{timeAgo(m.created_at)}</span>
            </div>
            <p className="mt-1 text-sm"><a className="font-semibold text-brand-700 underline" href={`mailto:${m.email}`}>{m.email}</a>{m.phone && <> · +{m.phone}</>}</p>
            <p className="mt-3 whitespace-pre-line text-slate-700">{m.message}</p>
            {!m.is_read && <button className="btn-outline mt-3" onClick={() => markRead(m.id)}>Mark as read</button>}
          </li>
        ))}
      </ul>
    </div>
  );
}
