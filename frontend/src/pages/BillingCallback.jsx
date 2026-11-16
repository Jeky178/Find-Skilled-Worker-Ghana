import { useCallback, useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { CheckCircle2, Clock, XCircle } from "lucide-react";
import api, { getErrorMessage } from "../services/api";

const NEXT = {
  premium_monthly: ["/dashboard/profile", "Add more photos to your profile"], premium_yearly: ["/dashboard/profile", "Add more photos to your profile"],
  verification: ["/dashboard/verification", "Submit your documents"], sponsored_7d: ["/artisans", "See your featured listing"], sponsored_30d: ["/artisans", "See your featured listing"],
};

/** Where the payment page sends the customer back to. We ask the server to confirm; we never trust the URL itself. */
export default function BillingCallback() {
  const [params] = useSearchParams();
  const reference = params.get("reference") || params.get("trxref");
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");
  const [tries, setTries] = useState(0);

  const check = useCallback(() => {
    if (!reference) return;
    api.get(`/api/billing/verify/${encodeURIComponent(reference)}`)
      .then((res) => { setResult(res.data); setError(""); if (res.data.status === "completed") window.dispatchEvent(new Event("notifications:changed")); })
      .catch((e) => setError(e.response?.status === 404 ? "We could not find that payment." : getErrorMessage(e)))
      .finally(() => setTries((n) => n + 1));
  }, [reference]);

  useEffect(() => { check(); }, [check]);

  // Confirmation can take a few seconds: look again a few times before giving up.
  useEffect(() => {
    if (result?.status !== "pending" || tries >= 6) return undefined;
    const t = setTimeout(check, 3000);
    return () => clearTimeout(t);
  }, [result, tries, check]);

  if (!reference) return <section className="mx-auto max-w-xl px-4 py-20 text-center"><h1 className="text-3xl font-bold">No payment to check</h1><Link to="/dashboard/billing" className="btn-primary mt-6">Go to billing</Link></section>;

  const status = result?.status;
  const next = result && NEXT[result.product_code];
  return (
    <section className="mx-auto max-w-xl px-4 py-20 text-center" aria-live="polite">
      {error && <p role="alert" className="rounded-2xl bg-accent-100 p-4 text-accent-700">{error}</p>}
      {!result && !error && <p className="text-slate-500">Confirming your payment…</p>}
      {status === "completed" && (<>
        <CheckCircle2 size={56} className="mx-auto text-green-600" aria-hidden="true" />
        <h1 className="mt-4 text-3xl font-bold">Payment confirmed</h1>
        <p className="mt-2 text-slate-600">{result.message}</p>
        <div className="mt-6 flex flex-wrap justify-center gap-3">
          {next && <Link to={next[0]} className="btn-accent">{next[1]}</Link>}
          <Link to="/dashboard/billing" className="btn-outline">Back to billing</Link>
        </div>
      </>)}
      {status === "pending" && (<>
        <Clock size={56} className="mx-auto text-brand-600" aria-hidden="true" />
        <h1 className="mt-4 text-3xl font-bold">Waiting for confirmation</h1>
        <p className="mt-2 text-slate-600">{result.message}</p>
        <div className="mt-6 flex flex-wrap justify-center gap-3">
          <button className="btn-primary" onClick={() => { setTries(0); check(); }}>Check again</button>
          <Link to="/dashboard/billing" className="btn-outline">Back to billing</Link>
        </div>
      </>)}
      {status === "failed" && (<>
        <XCircle size={56} className="mx-auto text-slate-500" aria-hidden="true" />
        <h1 className="mt-4 text-3xl font-bold">Payment not completed</h1>
        <p className="mt-2 text-slate-600">{result.message}</p>
        <Link to="/dashboard/billing" className="btn-primary mt-6">Try again</Link>
      </>)}
    </section>
  );
}
