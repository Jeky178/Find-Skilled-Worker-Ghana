import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { BadgeCheck, Check, Crown, Megaphone, Smartphone, CreditCard } from "lucide-react";
import api, { getErrorMessage } from "../services/api";
import StatusBadge from "../components/StatusBadge";
import { formatDay, formatMoney, timeAgo } from "../utils";

const PAY_STATUS = { pending: ["Unconfirmed", "bg-accent-100 text-accent-700"], completed: ["Paid", "bg-green-100 text-green-800"], failed: ["Not completed", "bg-slate-100 text-slate-700"], refunded: ["Refunded", "bg-slate-100 text-slate-700"] };
const FREE = ["Basic profile and listing", "5 portfolio photos", "Receive and answer requests", "Reviews and ratings"];
const PREMIUM = ["Priority position in search results", "Premium badge on your profile", "30 portfolio photos", "Everything in Free"];

export default function Billing() {
  const [plans, setPlans] = useState(null);
  const [me, setMe] = useState(null);
  const [history, setHistory] = useState([]);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState("");
  const [channel, setChannel] = useState("");

  const load = useCallback(() => {
    Promise.all([api.get("/api/billing/plans"), api.get("/api/billing/me"), api.get("/api/billing/history")])
      .then(([p, m, h]) => { setPlans(p.data); setMe(m.data); setHistory(h.data); })
      .catch((e) => setError(getErrorMessage(e)));
  }, []);
  useEffect(() => { load(); }, [load]);

  const buy = async (code) => {
    setBusy(code); setError("");
    try {
      const res = await api.post("/api/billing/checkout", { product_code: code, channel: channel || null });
      window.location.assign(res.data.authorization_url);          // hand over to the payment page
    } catch (e) { setError(getErrorMessage(e)); setBusy(""); }
  };

  if (!plans || !me) return error ? <p role="alert" className="mx-auto my-16 max-w-xl rounded-2xl bg-accent-100 p-4 text-accent-700">{error}</p> : <p className="p-16 text-center text-slate-500">Loading…</p>;

  const product = (code) => plans.products.find((p) => p.code === code);
  const BuyButton = ({ code, label, className = "btn-accent" }) => {
    const p = product(code);
    if (!p) return null;
    return (
      <button className={`${className} w-full`} disabled={!p.purchasable || busy === code} onClick={() => buy(code)}>
        {busy === code ? "Opening payment page…" : label || `Buy for ${formatMoney(p.price_ghs)}`}
      </button>
    );
  };
  const isPremium = me.plan === "premium";
  const monthly = product("premium_monthly"), yearly = product("premium_yearly");
  const verification = product("verification"), s7 = product("sponsored_7d"), s30 = product("sponsored_30d");

  return (
    <section className="mx-auto max-w-4xl px-4 py-10">
      <h1 className="text-3xl font-bold">Plans and billing</h1>

      {!plans.payments_enabled && (
        <p role="status" className="mt-5 rounded-2xl bg-brand-50 p-4 text-brand-900">
          <span className="font-bold">Online payments are not switched on yet.</span> The plans below show what will be available. Nothing can be bought, and you will not be charged.
        </p>
      )}
      {error && <p role="alert" className="mt-5 rounded-2xl bg-accent-100 p-4 text-accent-700">{error}</p>}

      <div className="mt-6 grid gap-4 sm:grid-cols-3">
        <div className="rounded-2xl border border-slate-200 p-5">
          <p className="text-sm text-slate-600">Your plan</p>
          <p className="mt-1 flex items-center gap-2 font-display text-2xl font-extrabold text-brand-900">{isPremium && <Crown size={22} className="text-accent-600" aria-hidden="true" />}{isPremium ? "Premium" : "Free"}</p>
          {me.premium_until && <p className="text-sm text-slate-600">Until {formatDay(me.premium_until)}</p>}
        </div>
        <div className="rounded-2xl border border-slate-200 p-5">
          <p className="text-sm text-slate-600">Sponsored listing</p>
          <p className="mt-1 font-display text-2xl font-extrabold text-brand-900">{me.sponsored_until ? "Active" : "Not active"}</p>
          {me.sponsored_until && <p className="text-sm text-slate-600">Until {formatDay(me.sponsored_until)}</p>}
        </div>
        <div className="rounded-2xl border border-slate-200 p-5">
          <p className="text-sm text-slate-600">Verification</p>
          <p className="mt-1 font-display text-2xl font-extrabold capitalize text-brand-900">{me.verification_status === "approved" ? "Verified" : me.verification_status}</p>
          <Link to="/dashboard/verification" className="text-sm font-semibold text-brand-700 underline">Manage verification</Link>
        </div>
      </div>

      {plans.payments_enabled && (
        <fieldset className="mt-8">
          <legend className="label">How would you like to pay?</legend>
          <div className="flex flex-wrap gap-2">
            {[["", "Any method", null], ["mobile_money", "Mobile Money", Smartphone], ["card", "Card", CreditCard]].map(([v, l, Icon]) => (
              <label key={v} className={`flex cursor-pointer items-center gap-2 rounded-full border px-4 py-2 font-semibold ${channel === v ? "border-brand-800 bg-brand-50 text-brand-900" : "border-slate-300"}`}>
                <input type="radio" name="channel" className="sr-only" checked={channel === v} onChange={() => setChannel(v)} />
                {Icon && <Icon size={16} aria-hidden="true" />}{l}
              </label>
            ))}
          </div>
        </fieldset>
      )}

      <div className="mt-8 grid gap-5 md:grid-cols-2">
        <div className="rounded-3xl border border-slate-200 p-6">
          <h2 className="text-2xl font-bold">Free</h2>
          <p className="mt-1 font-display text-3xl font-extrabold text-brand-900">GH₵0</p>
          <ul className="mt-4 space-y-2">{FREE.map((f) => <li key={f} className="flex gap-2"><Check size={18} className="mt-0.5 shrink-0 text-green-700" aria-hidden="true" />{f}</li>)}</ul>
          {!isPremium && <p className="mt-5 rounded-xl bg-slate-50 p-3 text-center font-semibold text-slate-700">Your current plan</p>}
        </div>
        <div className="rounded-3xl border-2 border-accent-500 p-6">
          <h2 className="flex items-center gap-2 text-2xl font-bold"><Crown size={22} className="text-accent-600" aria-hidden="true" />Premium</h2>
          <p className="mt-1 font-display text-3xl font-extrabold text-brand-900">{monthly ? formatMoney(monthly.price_ghs) : "–"}<span className="text-base font-semibold text-slate-600"> / month</span></p>
          <ul className="mt-4 space-y-2">{PREMIUM.map((f) => <li key={f} className="flex gap-2"><Check size={18} className="mt-0.5 shrink-0 text-green-700" aria-hidden="true" />{f}</li>)}</ul>
          <div className="mt-5 space-y-2">
            <BuyButton code="premium_monthly" label={`${isPremium ? "Renew" : "Get Premium"}: 1 month, ${monthly ? formatMoney(monthly.price_ghs) : ""}`} />
            {yearly?.price_ghs > 0 && <BuyButton code="premium_yearly" className="btn-outline" label={`12 months, ${formatMoney(yearly.price_ghs)}`} />}
          </div>
        </div>
      </div>

      <div className="mt-6 grid gap-5 md:grid-cols-2">
        <div className="rounded-3xl border border-slate-200 p-6">
          <h2 className="flex items-center gap-2 text-xl font-bold"><Megaphone size={20} className="text-accent-600" aria-hidden="true" />Sponsored listing</h2>
          <p className="mt-2 text-slate-600">Be featured at the top of search results and on the homepage for a set time.</p>
          <div className="mt-4 space-y-2">
            {s7?.price_ghs > 0 && <BuyButton code="sponsored_7d" className="btn-primary" label={`7 days, ${formatMoney(s7.price_ghs)}`} />}
            {s30?.price_ghs > 0 && <BuyButton code="sponsored_30d" className="btn-primary" label={`30 days, ${formatMoney(s30.price_ghs)}`} />}
          </div>
        </div>
        <div className="rounded-3xl border border-slate-200 p-6">
          <h2 className="flex items-center gap-2 text-xl font-bold"><BadgeCheck size={20} className="text-brand-700" aria-hidden="true" />Verified badge</h2>
          <p className="mt-2 text-slate-600">{Number(verification?.price_ghs) > 0 ? `Our team checks your ID once per application. Fee: ${formatMoney(verification.price_ghs)}.` : "Verification is free. Submit your ID and our team will review it."}</p>
          <Link to="/dashboard/verification" className="btn-outline mt-4 w-full">{Number(verification?.price_ghs) > 0 ? "Go to verification" : "Get verified"}</Link>
        </div>
      </div>

      <h2 className="mt-10 text-2xl font-bold">Payment history</h2>
      {history.length === 0 ? <p className="mt-3 text-slate-600">No payments yet.</p> : (
        <ul className="mt-3 divide-y divide-slate-100 rounded-2xl border border-slate-200">
          {history.map((h) => {
            const [label, cls] = PAY_STATUS[h.status] || [h.status, "bg-slate-100"];
            return (
              <li key={h.reference} className="flex flex-wrap items-center justify-between gap-3 p-4">
                <div><p className="font-display font-bold text-brand-900">{h.product_name}</p><p className="text-sm text-slate-500">{timeAgo(h.created_at)} · ref {h.reference}</p></div>
                <div className="flex items-center gap-3"><span className="font-semibold">{formatMoney(h.amount)}</span><span className={`rounded-full px-3 py-1 text-sm font-bold ${cls}`}>{label}</span></div>
              </li>
            );
          })}
        </ul>
      )}
    </section>
  );
}
