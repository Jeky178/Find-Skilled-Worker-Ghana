import { useCallback, useEffect, useState } from "react";
import { Link, useOutletContext } from "react-router-dom";
import api, { getErrorMessage } from "../../services/api";
import Pager from "../../components/Pager";
import { timeAgo } from "../../utils";

const TABS = [["", "All"], ["open", "Open"], ["reviewing", "Reviewing"], ["resolved", "Resolved"], ["dismissed", "Dismissed"]];
const CHIP = { open: "bg-accent-100 text-accent-700", reviewing: "bg-brand-100 text-brand-800", resolved: "bg-green-100 text-green-800", dismissed: "bg-slate-100 text-slate-700" };

function ReportCard({ r, onChange, refreshStats }) {
  const [note, setNote] = useState("");
  const [suspending, setSuspending] = useState(false);
  const [reason, setReason] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const closed = r.status === "resolved" || r.status === "dismissed";

  const run = async (fn) => { setBusy(true); setError(""); try { await fn(); refreshStats(); } catch (e) { setError(getErrorMessage(e)); } finally { setBusy(false); } };
  const setStatus = (status) => run(async () => { onChange((await api.patch(`/api/admin/reports/${r.id}`, { status, admin_note: note || r.admin_note || null })).data); setNote(""); });
  const suspend = () => run(async () => { await api.post(`/api/admin/users/${r.reported_user_id}/suspend`, { reason: reason || r.reason }); onChange({ ...r, reported_suspended: true }); setSuspending(false); });

  return (
    <li className="rounded-2xl border border-slate-200 p-5">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <h3 className="font-display text-lg font-bold text-brand-900">{r.reason}</h3>
        <span className={`rounded-full px-3 py-1 text-sm font-bold capitalize ${CHIP[r.status]}`}>{r.status}</span>
      </div>
      <p className="mt-1 text-slate-700">
        <span className="font-semibold">{r.reporter_name}</span> reported <span className="font-semibold">{r.reported_name}</span> ({r.reported_role})
        {r.reported_suspended && <span className="ml-2 rounded-full bg-accent-600 px-2 py-0.5 text-xs font-bold text-white">Suspended</span>}
      </p>
      {r.details && <p className="mt-2 whitespace-pre-line rounded-xl bg-slate-50 p-3 text-slate-700">{r.details}</p>}
      <p className="mt-2 text-sm text-slate-500">{timeAgo(r.created_at)}{r.request_id && <> · about job <Link className="font-semibold text-brand-700 underline" to={`/requests/${r.request_id}`}>{r.request_title}</Link></>}</p>
      {closed && r.admin_note && <p className="mt-2 text-sm text-slate-700"><span className="font-semibold">Outcome: </span>{r.admin_note}</p>}
      {error && <p role="alert" className="mt-3 rounded-xl bg-accent-100 p-2 text-sm text-accent-700">{error}</p>}

      {!closed && (
        <div className="mt-4 space-y-3 border-t border-slate-100 pt-4">
          <label htmlFor={`n${r.id}`} className="label">Outcome note (required to resolve or dismiss, and sent to the reporter)</label>
          <textarea id={`n${r.id}`} rows={2} maxLength={500} className="field" value={note} onChange={(e) => setNote(e.target.value)} />
          <div className="flex flex-wrap gap-2">
            {r.status === "open" && <button className="btn-outline" disabled={busy} onClick={() => setStatus("reviewing")}>Mark as reviewing</button>}
            <button className="btn-primary" disabled={busy} onClick={() => setStatus("resolved")}>Resolve</button>
            <button className="btn-outline" disabled={busy} onClick={() => setStatus("dismissed")}>Dismiss</button>
            {!r.reported_suspended && r.reported_role !== "admin" && <button className="btn-outline" onClick={() => setSuspending(!suspending)}>Suspend {r.reported_name}</button>}
          </div>
          {suspending && (
            <div className="space-y-2 rounded-xl bg-accent-100/50 p-3">
              <label htmlFor={`s${r.id}`} className="label">Reason shown in the audit log</label>
              <input id={`s${r.id}`} className="field" value={reason} placeholder={r.reason} onChange={(e) => setReason(e.target.value)} />
              <button className="btn-primary" disabled={busy} onClick={suspend}>Confirm suspension</button>
            </div>
          )}
        </div>
      )}
    </li>
  );
}

export default function Reports() {
  const { refreshStats } = useOutletContext();
  const [tab, setTab] = useState("open");
  const [page, setPage] = useState(1);
  const [data, setData] = useState(null);
  const [error, setError] = useState("");

  const load = useCallback(() => {
    api.get("/api/admin/reports", { params: { status: tab || undefined, page, page_size: 10 } })
      .then((r) => setData(r.data)).catch((e) => setError(getErrorMessage(e)));
  }, [tab, page]);
  useEffect(() => { load(); }, [load]);
  // A report that no longer matches the selected tab (e.g. just resolved on the Open tab) leaves the list.
  const replace = (r) => setData((d) => {
    const stays = !tab || r.status === tab;
    return { ...d, total: stays ? d.total : d.total - 1, items: stays ? d.items.map((x) => (x.id === r.id ? r : x)) : d.items.filter((x) => x.id !== r.id) };
  });

  return (
    <div>
      <h2 className="text-2xl font-bold">Reports and complaints</h2>
      <div className="mt-4 flex flex-wrap gap-2" role="tablist">
        {TABS.map(([v, l]) => (
          <button key={l} role="tab" aria-selected={tab === v} onClick={() => { setTab(v); setPage(1); }}
            className={`rounded-full border px-4 py-1.5 font-semibold ${tab === v ? "border-brand-800 bg-brand-800 text-white" : "border-slate-300 hover:border-brand-600"}`}>{l}</button>
        ))}
      </div>
      {error && <p role="alert" className="mt-4 rounded-xl bg-accent-100 p-3 text-accent-700">{error}</p>}
      {data && data.items.length === 0 && <p className="mt-6 rounded-2xl bg-brand-50 p-6 text-slate-700">No reports here.</p>}
      <ul className="mt-5 space-y-3">{data?.items.map((r) => <ReportCard key={r.id} r={r} onChange={replace} refreshStats={refreshStats} />)}</ul>
      {data && <Pager page={data.page} pages={data.pages} onChange={setPage} />}
    </div>
  );
}
