import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { Camera, Inbox, MapPin } from "lucide-react";
import api, { getErrorMessage } from "../services/api";
import { useAuth } from "../context/AuthContext";
import StatusBadge from "../components/StatusBadge";
import { timeAgo } from "../utils";

const TABS = [["", "All"], ["active", "Active"], ["completed", "Completed"], ["cancelled", "Cancelled"], ["rejected", "Declined"]];

export default function MyRequests() {
  const { user } = useAuth();
  const [params, setParams] = useSearchParams();
  const tab = params.get("status") || "";
  const page = Math.max(1, Number(params.get("page")) || 1);
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const isArtisan = user.role === "artisan";

  useEffect(() => {
    let cancelled = false;
    setLoading(true); setError("");
    api.get("/api/requests/mine", { params: { status: tab || undefined, page, page_size: 10 } })
      .then((res) => { if (!cancelled) setData(res.data); })
      .catch((e) => { if (!cancelled) setError(getErrorMessage(e)); })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [tab, page]);

  const go = (changes) => {
    const next = new URLSearchParams(params);
    Object.entries(changes).forEach(([k, v]) => (v ? next.set(k, v) : next.delete(k)));
    setParams(next);
  };

  return (
    <section className="mx-auto max-w-4xl px-4 py-10">
      <h1 className="text-3xl font-bold">{isArtisan ? "Customer requests" : "My service requests"}</h1>
      <p className="mt-1 text-slate-600">{isArtisan ? "Accept the jobs you want and keep customers updated." : "Track your requests and rate the work when it is done."}</p>

      <div className="mt-6 flex flex-wrap gap-2" role="tablist" aria-label="Filter requests">
        {TABS.map(([value, label]) => (
          <button key={label} role="tab" aria-selected={tab === value} onClick={() => go({ status: value, page: "" })}
            className={`rounded-full border px-4 py-1.5 font-semibold transition-colors ${tab === value ? "border-brand-800 bg-brand-800 text-white" : "border-slate-300 text-slate-700 hover:border-brand-600"}`}>
            {label}
          </button>
        ))}
      </div>

      {error && <p role="alert" className="mt-6 rounded-2xl bg-accent-100 p-4 text-accent-700">{error}</p>}
      {loading && !data && <div className="mt-6 space-y-3" aria-busy="true">{[1, 2, 3].map((i) => <div key={i} className="h-24 animate-pulse rounded-2xl bg-slate-100" />)}</div>}

      {data && data.items.length === 0 && !error && (
        <div className="mt-6 rounded-2xl border border-dashed border-brand-200 bg-brand-50 p-10 text-center">
          <Inbox size={36} className="mx-auto text-brand-600" aria-hidden="true" />
          <h2 className="mt-3 text-xl font-bold">{tab ? "Nothing here" : "No requests yet"}</h2>
          <p className="mt-1 text-slate-600">{isArtisan ? "New requests from customers will appear here." : "Find a skilled worker and send your first request."}</p>
          {!isArtisan && <Link to="/artisans" className="btn-accent mt-4">Browse artisans</Link>}
        </div>
      )}

      {data && data.items.length > 0 && (
        <ul className={`mt-6 space-y-3 ${loading ? "opacity-60" : ""}`}>
          {data.items.map((r) => (
            <li key={r.id}>
              <Link to={`/requests/${r.id}`} className="block rounded-2xl border border-slate-200 p-5 transition-colors hover:border-brand-600 hover:bg-brand-50/40">
                <div className="flex flex-wrap items-start justify-between gap-2">
                  <h2 className="font-display text-lg font-bold text-brand-900">{r.title}</h2>
                  <StatusBadge status={r.status} />
                </div>
                <p className="mt-1 text-slate-700">{isArtisan ? "From" : "To"} <span className="font-semibold">{r.other_party.name}</span> · {r.category}</p>
                <p className="mt-2 flex flex-wrap items-center gap-x-4 gap-y-1 text-sm text-slate-500">
                  <span className="inline-flex items-center gap-1"><MapPin size={14} aria-hidden="true" />{r.location}</span>
                  {r.photo_count > 0 && <span className="inline-flex items-center gap-1"><Camera size={14} aria-hidden="true" />{r.photo_count} photo{r.photo_count > 1 ? "s" : ""}</span>}
                  <span>Updated {timeAgo(r.updated_at)}</span>
                </p>
              </Link>
            </li>
          ))}
        </ul>
      )}

      {data && data.pages > 1 && (
        <nav className="mt-8 flex items-center justify-center gap-4" aria-label="Pagination">
          <button className="btn-outline" disabled={page <= 1} onClick={() => go({ page: page - 1 > 1 ? String(page - 1) : "" })}>Previous</button>
          <span className="font-semibold text-brand-900">Page {data.page} of {data.pages}</span>
          <button className="btn-outline" disabled={page >= data.pages} onClick={() => go({ page: String(page + 1) })}>Next</button>
        </nav>
      )}
    </section>
  );
}
