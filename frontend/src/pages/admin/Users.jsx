import { useCallback, useEffect, useState } from "react";
import { Link, useOutletContext } from "react-router-dom";
import api, { getErrorMessage } from "../../services/api";
import Pager from "../../components/Pager";
import { formatDay } from "../../utils";

const VERIFY = { unverified: "Not verified", pending: "Verification pending", approved: "Verified", rejected: "Verification rejected" };

function UserRow({ u, onChange, refreshStats }) {
  const [mode, setMode] = useState(null);         // "suspend" | "feature"
  const [reason, setReason] = useState("");
  const [until, setUntil] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const run = async (fn) => {
    setBusy(true); setError("");
    try { await fn(); setMode(null); setReason(""); setUntil(""); refreshStats(); } catch (e) { setError(getErrorMessage(e)); } finally { setBusy(false); }
  };
  const suspend = () => run(async () => onChange((await api.post(`/api/admin/users/${u.id}/suspend`, { reason })).data));
  const unsuspend = () => run(async () => onChange((await api.post(`/api/admin/users/${u.id}/unsuspend`)).data));
  const feature = (on) => run(async () => {
    const r = (await api.post(`/api/admin/artisans/${u.artisan_id}/feature`, { featured: on, until: on && until ? until : null })).data;
    onChange({ ...u, is_featured: r.is_featured, featured_until: r.featured_until });
  });
  const setPlan = (plan) => run(async () => { await api.post(`/api/admin/artisans/${u.artisan_id}/plan`, { plan }); onChange({ ...u, plan }); });

  const isArtisan = u.role === "artisan";
  const badge = "rounded-full px-2.5 py-0.5 text-xs font-bold";
  return (
    <li className={`rounded-2xl border p-5 ${u.is_suspended ? "border-accent-400 bg-accent-100/40" : "border-slate-200"}`}>
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="font-display text-lg font-bold text-brand-900">
            {isArtisan ? <Link to={`/artisans/${u.artisan_id}`} className="hover:underline">{u.full_name}</Link> : u.full_name}
            <span className={`${badge} ml-2 bg-brand-50 capitalize text-brand-800`}>{u.role}</span>
            {u.is_suspended && <span className={`${badge} ml-2 bg-accent-600 text-white`}>Suspended</span>}
          </p>
          <p className="text-sm text-slate-600">{u.email}{u.phone ? ` · +${u.phone}` : ""} · joined {formatDay(u.created_at)}</p>
          {isArtisan && (
            <p className="mt-2 flex flex-wrap gap-2 text-sm">
              <span className={`${badge} bg-slate-100 text-slate-700`}>{u.category}</span>
              <span className={`${badge} ${u.verification_status === "approved" ? "bg-green-100 text-green-800" : "bg-slate-100 text-slate-700"}`}>{VERIFY[u.verification_status]}</span>
              <span className={`${badge} ${u.plan === "premium" ? "bg-accent-100 text-accent-700" : "bg-slate-100 text-slate-700"}`}>{u.plan === "premium" ? "Premium" : "Free plan"}</span>
              {u.is_featured && <span className={`${badge} bg-brand-100 text-brand-800`}>Featured{u.featured_until ? ` until ${formatDay(u.featured_until)}` : ""}</span>}
            </p>
          )}
          {u.is_suspended && u.suspended_reason && <p className="mt-2 text-sm text-accent-700">Reason: {u.suspended_reason}</p>}
        </div>

        {u.role !== "admin" && mode === null && (
          <div className="flex flex-wrap gap-2">
            {isArtisan && (u.is_featured
              ? <button className="btn-outline" disabled={busy} onClick={() => feature(false)}>Remove featured</button>
              : <button className="btn-outline" onClick={() => setMode("feature")}>Feature</button>)}
            {isArtisan && <button className="btn-outline" disabled={busy} onClick={() => setPlan(u.plan === "premium" ? "free" : "premium")}>{u.plan === "premium" ? "Set to Free" : "Give Premium"}</button>}
            {u.is_suspended
              ? <button className="btn-primary" disabled={busy} onClick={unsuspend}>Reinstate</button>
              : <button className="btn-outline" onClick={() => setMode("suspend")}>Suspend</button>}
          </div>
        )}
      </div>

      {error && <p role="alert" className="mt-3 rounded-xl bg-accent-100 p-2 text-sm text-accent-700">{error}</p>}

      {mode === "suspend" && (
        <form className="mt-4 space-y-3 border-t border-slate-100 pt-4" onSubmit={(e) => { e.preventDefault(); suspend(); }}>
          <label htmlFor={`r${u.id}`} className="label">Reason for suspending {u.full_name}</label>
          <textarea id={`r${u.id}`} required minLength={3} maxLength={500} rows={2} className="field" value={reason} onChange={(e) => setReason(e.target.value)} />
          <p className="text-sm text-slate-600">They will be signed out and hidden from the directory straight away.</p>
          <div className="flex gap-2"><button className="btn-primary" disabled={busy}>Suspend account</button><button type="button" className="btn-outline" onClick={() => setMode(null)}>Cancel</button></div>
        </form>
      )}
      {mode === "feature" && (
        <form className="mt-4 flex flex-wrap items-end gap-3 border-t border-slate-100 pt-4" onSubmit={(e) => { e.preventDefault(); feature(true); }}>
          <div><label htmlFor={`f${u.id}`} className="label">Featured until (optional)</label>
            <input id={`f${u.id}`} type="date" min={new Date(Date.now() + 86400000).toISOString().slice(0, 10)} className="field" value={until} onChange={(e) => setUntil(e.target.value)} /></div>
          <button className="btn-accent" disabled={busy}>Feature this artisan</button>
          <button type="button" className="btn-outline" onClick={() => setMode(null)}>Cancel</button>
        </form>
      )}
    </li>
  );
}

export default function Users() {
  const { refreshStats } = useOutletContext();
  const [f, setF] = useState({ q: "", role: "", state: "", verification: "" });
  const [applied, setApplied] = useState(f);
  const [page, setPage] = useState(1);
  const [data, setData] = useState(null);
  const [error, setError] = useState("");

  const load = useCallback(() => {
    api.get("/api/admin/users", { params: { ...Object.fromEntries(Object.entries(applied).filter(([, v]) => v)), page, page_size: 15 } })
      .then((r) => setData(r.data)).catch((e) => setError(getErrorMessage(e)));
  }, [applied, page]);
  useEffect(() => { load(); }, [load]);

  const replace = (u) => setData((d) => ({ ...d, items: d.items.map((x) => (x.id === u.id ? u : x)) }));
  const set = (k) => (e) => { const next = { ...f, [k]: e.target.value }; setF(next); if (k !== "q") { setApplied(next); setPage(1); } };

  return (
    <div>
      <h2 className="text-2xl font-bold">Customers and artisans</h2>
      <form className="mt-4 grid gap-3 md:grid-cols-[1fr_auto_auto_auto]" onSubmit={(e) => { e.preventDefault(); setApplied(f); setPage(1); }} role="search">
        <div><label htmlFor="uq" className="sr-only">Search by name or email</label><input id="uq" className="field" placeholder="Search by name or email" value={f.q} onChange={set("q")} /></div>
        <select aria-label="Role" className="field" value={f.role} onChange={set("role")}><option value="">All roles</option><option value="customer">Customers</option><option value="artisan">Artisans</option><option value="admin">Admins</option></select>
        <select aria-label="Account state" className="field" value={f.state} onChange={set("state")}><option value="">Any state</option><option value="active">Active</option><option value="suspended">Suspended</option></select>
        <select aria-label="Verification" className="field" value={f.verification} onChange={set("verification")}><option value="">Any verification</option><option value="unverified">Not verified</option><option value="pending">Pending</option><option value="approved">Verified</option><option value="rejected">Rejected</option></select>
      </form>
      {error && <p role="alert" className="mt-4 rounded-xl bg-accent-100 p-3 text-accent-700">{error}</p>}
      {data && <p className="mt-4 text-slate-600">{data.total} {data.total === 1 ? "account" : "accounts"}</p>}
      <ul className="mt-3 space-y-3">{data?.items.map((u) => <UserRow key={u.id} u={u} onChange={replace} refreshStats={refreshStats} />)}</ul>
      {data && data.items.length === 0 && <p className="mt-4 rounded-2xl bg-brand-50 p-6 text-slate-700">No accounts match.</p>}
      {data && <Pager page={data.page} pages={data.pages} onChange={setPage} />}
    </div>
  );
}
