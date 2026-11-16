import { useCallback, useEffect, useState } from "react";
import { useOutletContext } from "react-router-dom";
import api, { getErrorMessage } from "../../services/api";
import BlobImage from "../../components/BlobImage";
import Pager from "../../components/Pager";
import { timeAgo } from "../../utils";

const TABS = [["pending", "Pending"], ["approved", "Approved"], ["rejected", "Rejected"], ["", "All"]];

export default function Verifications() {
  const { refreshStats } = useOutletContext();
  const [tab, setTab] = useState("pending");
  const [page, setPage] = useState(1);
  const [data, setData] = useState(null);
  const [error, setError] = useState("");
  const [openId, setOpenId] = useState(null);
  const [rejecting, setRejecting] = useState(false);
  const [note, setNote] = useState("");
  const [busy, setBusy] = useState(false);

  const load = useCallback(() => {
    api.get("/api/admin/verifications", { params: { status: tab || undefined, page, page_size: 10 } })
      .then((r) => setData(r.data)).catch((e) => setError(getErrorMessage(e)));
  }, [tab, page]);
  useEffect(() => { load(); }, [load]);

  const decide = async (id, approve) => {
    setBusy(true); setError("");
    try {
      await api.post(`/api/admin/verifications/${id}/decision`, { approve, note: note || null });
      setOpenId(null); setRejecting(false); setNote(""); load(); refreshStats();
    } catch (e) { setError(getErrorMessage(e)); } finally { setBusy(false); }
  };

  return (
    <div>
      <h2 className="text-2xl font-bold">Artisan verification</h2>
      <p className="mt-1 text-slate-600">Check that the ID matches the artisan, then approve or reject. Documents are private to administrators.</p>
      <div className="mt-4 flex flex-wrap gap-2" role="tablist">
        {TABS.map(([v, l]) => (
          <button key={l} role="tab" aria-selected={tab === v} onClick={() => { setTab(v); setPage(1); setOpenId(null); }}
            className={`rounded-full border px-4 py-1.5 font-semibold ${tab === v ? "border-brand-800 bg-brand-800 text-white" : "border-slate-300 hover:border-brand-600"}`}>{l}</button>
        ))}
      </div>
      {error && <p role="alert" className="mt-4 rounded-xl bg-accent-100 p-3 text-accent-700">{error}</p>}
      {data && data.items.length === 0 && <p className="mt-6 rounded-2xl bg-brand-50 p-6 text-slate-700">No applications here.</p>}

      <ul className="mt-5 space-y-3">
        {data?.items.map((v) => (
          <li key={v.id} className="rounded-2xl border border-slate-200 p-5">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <p className="font-display text-lg font-bold text-brand-900">{v.artisan_name} <span className="font-normal text-slate-600">· {v.category}</span></p>
                <p className="text-sm text-slate-600">{v.artisan_email} · {v.id_type} · applied {timeAgo(v.created_at)}</p>
              </div>
              {v.status === "pending"
                ? <button className="btn-primary" onClick={() => { setOpenId(openId === v.id ? null : v.id); setRejecting(false); setNote(""); }}>{openId === v.id ? "Close" : "Review documents"}</button>
                : <span className={`rounded-full px-3 py-1 text-sm font-bold ${v.status === "approved" ? "bg-green-100 text-green-800" : "bg-slate-100 text-slate-700"}`}>{v.status === "approved" ? "Approved" : "Rejected"}</span>}
            </div>
            {v.status !== "pending" && v.admin_note && <p className="mt-2 text-sm text-slate-600">Note: {v.admin_note}</p>}

            {openId === v.id && (
              <div className="mt-5 space-y-4 border-t border-slate-100 pt-5">
                <div className="grid gap-4 md:grid-cols-2">
                  <div><p className="label">ID document ({v.id_type})</p><BlobImage url={`/api/admin/verifications/${v.id}/document?kind=id`} alt="ID document" /></div>
                  {v.has_certificate && <div><p className="label">Trade certificate</p><BlobImage url={`/api/admin/verifications/${v.id}/document?kind=certificate`} alt="Trade certificate" /></div>}
                </div>
                {rejecting ? (
                  <form className="space-y-3" onSubmit={(e) => { e.preventDefault(); decide(v.id, false); }}>
                    <label htmlFor="note" className="label">Why is it rejected? The artisan will see this.</label>
                    <textarea id="note" required rows={3} maxLength={500} className="field" value={note} onChange={(e) => setNote(e.target.value)} />
                    <div className="flex gap-2"><button className="btn-primary" disabled={busy}>Confirm rejection</button><button type="button" className="btn-outline" onClick={() => setRejecting(false)}>Back</button></div>
                  </form>
                ) : (
                  <div className="flex flex-wrap gap-2">
                    <button className="btn-accent" disabled={busy} onClick={() => decide(v.id, true)}>Approve and verify</button>
                    <button className="btn-outline" onClick={() => setRejecting(true)}>Reject</button>
                  </div>
                )}
              </div>
            )}
          </li>
        ))}
      </ul>
      {data && <Pager page={data.page} pages={data.pages} onChange={setPage} />}
    </div>
  );
}
