import { useEffect, useState } from "react";
import { CheckCircle2, X } from "lucide-react";
import api, { getErrorMessage } from "../services/api";

/** Lets a customer or artisan report a profile (artisanId) or a job (requestId) to the admin team. */
export default function ReportDialog({ artisanId, requestId, targetName, onClose }) {
  const [reasons, setReasons] = useState([]);
  const [reason, setReason] = useState("");
  const [details, setDetails] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [done, setDone] = useState(false);

  useEffect(() => { api.get("/api/reports/reasons").then((r) => setReasons(r.data)).catch(() => {}); }, []);
  useEffect(() => {
    const onKey = (e) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  const submit = async (e) => {
    e.preventDefault();
    setError(""); setBusy(true);
    try {
      await api.post("/api/reports", { artisan_id: artisanId ?? null, request_id: requestId ?? null, reason, details: details || null });
      setDone(true);
    } catch (err) { setError(getErrorMessage(err)); } finally { setBusy(false); }
  };

  return (
    <div role="dialog" aria-modal="true" aria-label="Report a problem" className="fixed inset-0 z-50 grid place-items-center bg-brand-900/70 p-4" onClick={onClose}>
      <div className="relative w-full max-w-md rounded-3xl bg-white p-6" onClick={(e) => e.stopPropagation()}>
        <button className="absolute right-4 top-4 rounded-full p-1 hover:bg-slate-100" onClick={onClose} aria-label="Close"><X size={20} /></button>
        {done ? (
          <div className="py-6 text-center" role="status">
            <CheckCircle2 size={44} className="mx-auto text-green-600" aria-hidden="true" />
            <h2 className="mt-3 text-2xl font-bold">Report sent</h2>
            <p className="mt-2 text-slate-600">Thank you. Our team will review it and let you know the outcome.</p>
            <button className="btn-primary mt-5" onClick={onClose}>Close</button>
          </div>
        ) : (
          <form onSubmit={submit} className="space-y-4">
            <h2 className="pr-8 text-2xl font-bold">Report {targetName || "a problem"}</h2>
            <p className="text-sm text-slate-600">Your report is private. The person you report will not see who sent it.</p>
            {error && <p role="alert" className="rounded-xl bg-accent-100 p-3 text-accent-700">{error}</p>}
            <div>
              <label htmlFor="reason" className="label">What went wrong?</label>
              <select id="reason" required className="field" value={reason} onChange={(e) => setReason(e.target.value)}>
                <option value="">Choose a reason</option>
                {reasons.map((r) => <option key={r}>{r}</option>)}
              </select>
            </div>
            <div>
              <label htmlFor="details" className="label">Tell us more (optional)</label>
              <textarea id="details" rows={4} maxLength={2000} className="field resize-y" value={details} onChange={(e) => setDetails(e.target.value)} />
            </div>
            <button className="btn-accent w-full" disabled={busy || !reason}>{busy ? "Sending…" : "Send report"}</button>
          </form>
        )}
      </div>
    </div>
  );
}
