import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import api, { getErrorMessage } from "../../services/api";
import { timeAgo } from "../../utils";

const LABEL = { user: "Sign-up", request: "Request", review: "Review", report: "Report", verification: "Verification", admin: "Admin action" };
const COLOR = { user: "bg-brand-50 text-brand-800", request: "bg-brand-100 text-brand-800", review: "bg-green-100 text-green-800", report: "bg-accent-100 text-accent-700", verification: "bg-brand-100 text-brand-800", admin: "bg-slate-200 text-slate-800" };

export default function Activity() {
  const [items, setItems] = useState(null);
  const [error, setError] = useState("");
  useEffect(() => { api.get("/api/admin/activity", { params: { limit: 100 } }).then((r) => setItems(r.data)).catch((e) => setError(getErrorMessage(e))); }, []);

  return (
    <div>
      <h2 className="text-2xl font-bold">Platform activity</h2>
      <p className="mt-1 text-slate-600">The latest sign-ups, jobs, reviews, reports and admin actions. Admin actions form the audit trail.</p>
      {error && <p role="alert" className="mt-4 rounded-xl bg-accent-100 p-3 text-accent-700">{error}</p>}
      {items && items.length === 0 && <p className="mt-6 rounded-2xl bg-brand-50 p-6 text-slate-700">Nothing has happened yet.</p>}
      <ul className="mt-5 divide-y divide-slate-100 rounded-2xl border border-slate-200">
        {items?.map((i, k) => (
          <li key={k} className="flex flex-wrap items-center gap-3 p-4">
            <span className={`w-28 shrink-0 rounded-full px-3 py-1 text-center text-xs font-bold ${COLOR[i.kind]}`}>{LABEL[i.kind]}</span>
            <span className="min-w-0 flex-1">{i.link ? <Link to={i.link} className="hover:underline">{i.text}</Link> : i.text}</span>
            <span className="shrink-0 text-sm text-slate-500">{timeAgo(i.at)}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}
