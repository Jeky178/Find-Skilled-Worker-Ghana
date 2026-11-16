import { useCallback, useEffect, useState } from "react";
import api, { getErrorMessage } from "../../services/api";
import Pager from "../../components/Pager";
import { formatMoney, timeAgo } from "../../utils";

const CHIP = { pending: "bg-accent-100 text-accent-700", completed: "bg-green-100 text-green-800", failed: "bg-slate-100 text-slate-700", refunded: "bg-slate-100 text-slate-700" };
const LABEL = { pending: "Unconfirmed", completed: "Paid", failed: "Not completed", refunded: "Refunded" };

export default function Payments() {
  const [status, setStatus] = useState("");
  const [purpose, setPurpose] = useState("");
  const [page, setPage] = useState(1);
  const [data, setData] = useState(null);
  const [error, setError] = useState("");

  const load = useCallback(() => {
    api.get("/api/admin/payments", { params: { status: status || undefined, purpose: purpose || undefined, page, page_size: 15 } })
      .then((r) => setData(r.data)).catch((e) => setError(getErrorMessage(e)));
  }, [status, purpose, page]);
  useEffect(() => { load(); }, [load]);

  return (
    <div>
      <h2 className="text-2xl font-bold">Payments</h2>
      <p className="mt-1 text-slate-600">Only the payment provider can confirm a payment. Nobody here can mark one as paid, so revenue below is money that was actually confirmed.</p>
      {data && (
        <div className="mt-4 grid grid-cols-2 gap-3 md:max-w-md">
          <div className="rounded-2xl border border-slate-200 p-4"><span className="block font-display text-3xl font-extrabold text-brand-900">{formatMoney(data.revenue_ghs)}</span><span className="text-sm font-semibold text-slate-700">Confirmed revenue</span></div>
          <div className="rounded-2xl border border-slate-200 p-4"><span className="block font-display text-3xl font-extrabold text-brand-900">{data.completed_count}</span><span className="text-sm font-semibold text-slate-700">Paid orders</span></div>
        </div>
      )}
      <div className="mt-4 grid gap-3 sm:grid-cols-2 md:max-w-lg">
        <select aria-label="Status" className="field" value={status} onChange={(e) => { setStatus(e.target.value); setPage(1); }}>
          <option value="">Any status</option>{Object.entries(LABEL).map(([v, l]) => <option key={v} value={v}>{l}</option>)}
        </select>
        <select aria-label="Type" className="field" value={purpose} onChange={(e) => { setPurpose(e.target.value); setPage(1); }}>
          <option value="">Any type</option><option value="subscription">Premium plans</option><option value="verification">Verification fees</option><option value="sponsored_listing">Sponsored listings</option>
        </select>
      </div>
      {error && <p role="alert" className="mt-4 rounded-xl bg-accent-100 p-3 text-accent-700">{error}</p>}
      {data && data.items.length === 0 && <p className="mt-6 rounded-2xl bg-brand-50 p-6 text-slate-700">No payments yet. They will appear here once online payments are switched on and artisans buy plans.</p>}
      <ul className="mt-5 divide-y divide-slate-100 rounded-2xl border border-slate-200">
        {data?.items.map((p) => (
          <li key={p.id} className="flex flex-wrap items-center justify-between gap-3 p-4">
            <div><p className="font-display font-bold text-brand-900">{p.user_name} <span className="font-normal text-slate-600">· {p.product_code.replace(/_/g, " ")}</span></p>
              <p className="text-sm text-slate-500">{p.user_email} · {timeAgo(p.created_at)} · {p.reference}{p.status === "completed" && !p.fulfilled ? " · NOT DELIVERED" : ""}</p></div>
            <div className="flex items-center gap-3"><span className="font-semibold">{formatMoney(p.amount)}</span><span className={`rounded-full px-3 py-1 text-sm font-bold ${CHIP[p.status]}`}>{LABEL[p.status]}</span></div>
          </li>
        ))}
      </ul>
      {data && <Pager page={data.page} pages={data.pages} onChange={setPage} />}
    </div>
  );
}
