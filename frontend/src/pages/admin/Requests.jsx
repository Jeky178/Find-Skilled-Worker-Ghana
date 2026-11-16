import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import api, { getErrorMessage } from "../../services/api";
import StatusBadge from "../../components/StatusBadge";
import Pager from "../../components/Pager";
import { STATUS, timeAgo } from "../../utils";

export default function Requests() {
  const [status, setStatus] = useState("");
  const [q, setQ] = useState("");
  const [applied, setApplied] = useState("");
  const [page, setPage] = useState(1);
  const [data, setData] = useState(null);
  const [error, setError] = useState("");

  const load = useCallback(() => {
    api.get("/api/admin/requests", { params: { status: status || undefined, q: applied || undefined, page, page_size: 15 } })
      .then((r) => setData(r.data)).catch((e) => setError(getErrorMessage(e)));
  }, [status, applied, page]);
  useEffect(() => { load(); }, [load]);

  return (
    <div>
      <h2 className="text-2xl font-bold">Service requests</h2>
      <p className="mt-1 text-slate-600">A read-only view of every job on the platform. Open one to see the full conversation of events.</p>
      <form className="mt-4 grid gap-3 md:grid-cols-[1fr_auto]" onSubmit={(e) => { e.preventDefault(); setApplied(q); setPage(1); }} role="search">
        <div><label htmlFor="rq" className="sr-only">Search by title</label><input id="rq" className="field" placeholder="Search by title" value={q} onChange={(e) => setQ(e.target.value)} /></div>
        <select aria-label="Status" className="field" value={status} onChange={(e) => { setStatus(e.target.value); setPage(1); }}>
          <option value="">Any status</option>{Object.entries(STATUS).map(([v, s]) => <option key={v} value={v}>{s.label}</option>)}
        </select>
      </form>
      {error && <p role="alert" className="mt-4 rounded-xl bg-accent-100 p-3 text-accent-700">{error}</p>}
      {data && <p className="mt-4 text-slate-600">{data.total} {data.total === 1 ? "request" : "requests"}</p>}
      <ul className="mt-3 space-y-3">
        {data?.items.map((r) => (
          <li key={r.id}>
            <Link to={`/requests/${r.id}`} className="block rounded-2xl border border-slate-200 p-5 hover:border-brand-600">
              <div className="flex flex-wrap items-start justify-between gap-2"><h3 className="font-display text-lg font-bold text-brand-900">{r.title}</h3><StatusBadge status={r.status} /></div>
              <p className="mt-1 text-slate-700">{r.customer_name} → {r.artisan_name} · {r.category} · {r.location}</p>
              <p className="mt-1 text-sm text-slate-500">Updated {timeAgo(r.updated_at)}</p>
            </Link>
          </li>
        ))}
      </ul>
      {data && data.items.length === 0 && <p className="mt-4 rounded-2xl bg-brand-50 p-6 text-slate-700">No requests match.</p>}
      {data && <Pager page={data.page} pages={data.pages} onChange={setPage} />}
    </div>
  );
}
