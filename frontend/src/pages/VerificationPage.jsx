import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { BadgeCheck, Clock, Lock, ShieldX } from "lucide-react";
import api, { getErrorMessage } from "../services/api";
import { formatMoney, timeAgo } from "../utils";

const ID_TYPES = ["Ghana Card", "Driver's Licence", "Passport", "Voter ID"];

export default function VerificationPage() {
  const [info, setInfo] = useState(null);
  const [billing, setBilling] = useState(null);
  const [paying, setPaying] = useState(false);
  const [loadError, setLoadError] = useState("");
  const [idType, setIdType] = useState(ID_TYPES[0]);
  const [doc, setDoc] = useState(null);
  const [cert, setCert] = useState(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const load = useCallback(() => {
    api.get("/api/artisan/me/verification").then((r) => setInfo(r.data)).catch((e) => setLoadError(getErrorMessage(e)));
    api.get("/api/billing/me").then((r) => setBilling(r.data)).catch(() => {});
  }, []);
  useEffect(() => { load(); }, [load]);

  const submit = async (e) => {
    e.preventDefault();
    if (!doc) { setError("Please choose a photo of your ID."); return; }
    setError(""); setBusy(true);
    try {
      const fd = new FormData();
      fd.append("id_type", idType); fd.append("document", doc); if (cert) fd.append("certificate", cert);
      setInfo((await api.post("/api/artisan/me/verification", fd)).data);
      setDoc(null); setCert(null);
    } catch (err) { setError(getErrorMessage(err)); } finally { setBusy(false); }
  };

  if (loadError) return <p role="alert" className="mx-auto my-16 max-w-xl rounded-2xl bg-accent-100 p-4 text-accent-700">{loadError}</p>;
  if (!info) return <p className="p-16 text-center text-slate-500">Loading…</p>;

  const canApply = info.status === "unverified" || info.status === "rejected";
  const mustPay = billing && billing.payments_enabled && Number(billing.verification_fee_ghs) > 0 && !billing.verification_credit;

  const payFee = async () => {
    setPaying(true); setError("");
    try { window.location.assign((await api.post("/api/billing/checkout", { product_code: "verification" })).data.authorization_url); }
    catch (err) { setError(getErrorMessage(err)); setPaying(false); }
  };

  return (
    <section className="mx-auto max-w-2xl px-4 py-10">
      <h1 className="text-3xl font-bold">Get verified</h1>
      <p className="mt-2 text-slate-600">A Verified badge shows customers that our team has checked your identity. Verified artisans are chosen more often.</p>

      {info.status === "approved" && (
        <div className="mt-6 flex gap-3 rounded-2xl bg-green-50 p-5 text-green-900"><BadgeCheck className="shrink-0" aria-hidden="true" />
          <p><span className="font-bold">You are verified.</span> Your profile shows the Verified badge.</p></div>
      )}
      {info.status === "pending" && (
        <div className="mt-6 flex gap-3 rounded-2xl bg-brand-50 p-5 text-brand-900"><Clock className="shrink-0" aria-hidden="true" />
          <p><span className="font-bold">Your application is being reviewed.</span> You applied {info.submitted_at ? timeAgo(info.submitted_at) : "recently"}. We will notify you of the decision.</p></div>
      )}
      {info.status === "rejected" && (
        <div role="alert" className="mt-6 flex gap-3 rounded-2xl bg-accent-100 p-5 text-accent-700"><ShieldX className="shrink-0" aria-hidden="true" />
          <p><span className="font-bold">Your last application was not approved.</span>{info.admin_note && <> Reason: {info.admin_note}.</>} You can apply again below.</p></div>
      )}

      {canApply && mustPay && (
        <div className="mt-6 rounded-3xl border border-slate-200 p-6">
          {error && <p role="alert" className="mb-4 rounded-xl bg-accent-100 p-3 text-accent-700">{error}</p>}
          <h2 className="text-xl font-bold">Verification fee: {formatMoney(billing.verification_fee_ghs)}</h2>
          <p className="mt-2 text-slate-600">The fee covers one review of your documents by our team. Pay first, then you will be able to submit your ID.</p>
          <button className="btn-accent mt-4" disabled={paying} onClick={payFee}>{paying ? "Opening payment page…" : `Pay ${formatMoney(billing.verification_fee_ghs)}`}</button>
        </div>
      )}
      {canApply && billing?.verification_credit && Number(billing.verification_fee_ghs) > 0 && (
        <p role="status" className="mt-6 rounded-2xl bg-green-50 p-4 text-green-900">Your verification fee is paid. Submit your documents below.</p>
      )}
      {canApply && !mustPay && (
        <form onSubmit={submit} className="mt-6 space-y-5 rounded-3xl border border-slate-200 p-6">
          {error && <p role="alert" className="rounded-xl bg-accent-100 p-3 text-accent-700">{error}</p>}
          <div>
            <label htmlFor="id_type" className="label">Type of ID</label>
            <select id="id_type" className="field" value={idType} onChange={(e) => setIdType(e.target.value)}>
              {ID_TYPES.map((t) => <option key={t}>{t}</option>)}
            </select>
          </div>
          <div>
            <label htmlFor="doc" className="label">Clear photo of your ID</label>
            <input id="doc" type="file" accept="image/jpeg,image/png,image/webp" className="field" onChange={(e) => setDoc(e.target.files?.[0] || null)} />
            <p className="mt-1 text-sm text-slate-500">All details must be readable. JPG, PNG or WebP, up to 5 MB.</p>
          </div>
          <div>
            <label htmlFor="cert" className="label">Trade certificate (optional)</label>
            <input id="cert" type="file" accept="image/jpeg,image/png,image/webp" className="field" onChange={(e) => setCert(e.target.files?.[0] || null)} />
          </div>
          <p className="flex gap-2 rounded-xl bg-slate-50 p-3 text-sm text-slate-600"><Lock size={16} className="mt-0.5 shrink-0" aria-hidden="true" />
            Your documents are stored privately. Only our administrators can see them, and they are never shown on your profile.</p>
          <button className="btn-accent w-full py-3" disabled={busy}>{busy ? "Submitting…" : "Submit for verification"}</button>
        </form>
      )}
      <Link to="/dashboard" className="mt-6 inline-block font-semibold text-brand-700 underline">Back to dashboard</Link>
    </section>
  );
}
