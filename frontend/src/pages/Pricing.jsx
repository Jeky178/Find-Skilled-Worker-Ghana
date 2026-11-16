import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Check, Crown } from "lucide-react";
import api from "../services/api";
import { formatMoney } from "../utils";

const FREE = ["Professional profile and directory listing", "5 portfolio photos", "Receive and answer customer requests", "Customer reviews and ratings", "WhatsApp contact button"];
const PREMIUM = ["Priority position in search results", "Premium badge on your profile", "30 portfolio photos", "Everything in Free"];

export default function Pricing() {
  const [plans, setPlans] = useState(null);
  useEffect(() => { api.get("/api/billing/plans").then((r) => setPlans(r.data)).catch(() => {}); }, []);
  const price = (code) => plans?.products.find((p) => p.code === code)?.price_ghs;
  const sponsored7 = price("sponsored_7d"), verification = Number(price("verification") || 0);

  return (
    <>
      <section className="bg-brand-50"><div className="mx-auto max-w-6xl px-4 py-14">
        <h1 className="text-4xl font-extrabold">Simple pricing for artisans</h1>
        <p className="mt-3 max-w-2xl text-lg text-slate-700">Customers always search and request for free. Artisans start free and can upgrade to be seen by more people.</p>
      </div></section>
      <section className="mx-auto grid max-w-4xl gap-5 px-4 py-12 md:grid-cols-2">
        <div className="rounded-3xl border border-slate-200 p-7">
          <h2 className="text-2xl font-bold">Free</h2>
          <p className="mt-1 font-display text-4xl font-extrabold text-brand-900">GH₵0</p>
          <ul className="mt-5 space-y-2">{FREE.map((f) => <li key={f} className="flex gap-2"><Check size={18} className="mt-0.5 shrink-0 text-green-700" aria-hidden="true" />{f}</li>)}</ul>
          <Link to="/register?role=artisan" className="btn-outline mt-6 w-full">Create a free profile</Link>
        </div>
        <div className="rounded-3xl border-2 border-accent-500 p-7">
          <h2 className="flex items-center gap-2 text-2xl font-bold"><Crown size={22} className="text-accent-600" aria-hidden="true" />Premium</h2>
          <p className="mt-1 font-display text-4xl font-extrabold text-brand-900">{price("premium_monthly") ? formatMoney(price("premium_monthly")) : "–"}<span className="text-base font-semibold text-slate-600"> / month</span></p>
          {Number(price("premium_yearly")) > 0 && <p className="text-sm text-slate-600">or {formatMoney(price("premium_yearly"))} for 12 months</p>}
          <ul className="mt-5 space-y-2">{PREMIUM.map((f) => <li key={f} className="flex gap-2"><Check size={18} className="mt-0.5 shrink-0 text-green-700" aria-hidden="true" />{f}</li>)}</ul>
          <Link to="/dashboard/billing" className="btn-accent mt-6 w-full">Get Premium</Link>
        </div>
      </section>
      <section className="mx-auto max-w-4xl px-4 pb-16">
        <h2 className="text-2xl font-bold">Extras</h2>
        <ul className="mt-4 grid gap-4 md:grid-cols-2">
          <li className="rounded-2xl border border-slate-200 p-5"><h3 className="text-lg font-bold">Sponsored listing</h3><p className="mt-1 text-slate-600">Be featured at the top of results and on the homepage{sponsored7 && Number(sponsored7) > 0 ? `, from ${formatMoney(sponsored7)} for 7 days` : ""}.</p></li>
          <li className="rounded-2xl border border-slate-200 p-5"><h3 className="text-lg font-bold">Verified badge</h3><p className="mt-1 text-slate-600">{verification > 0 ? `Our team checks your ID. One-time fee of ${formatMoney(verification)} per application.` : "Our team checks your ID. Currently free."}</p></li>
        </ul>
        <p className="mt-6 text-sm text-slate-500">Pay with Mobile Money (MTN, Telecel, AirtelTigo) or card through Paystack, when online payments are switched on.</p>
      </section>
    </>
  );
}
