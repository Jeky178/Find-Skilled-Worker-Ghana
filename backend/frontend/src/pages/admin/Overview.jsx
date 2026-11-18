import { useEffect, useState } from "react";
import { Link, useOutletContext } from "react-router-dom";
import api from "../../services/api";
import { formatMoney } from "../../utils";
import { timeAgo } from "../../utils";

const Card = ({ label, value, to, hot }) => {
  const body = (
    <>
      <span className="block font-display text-3xl font-extrabold text-brand-900">{value ?? "–"}</span>
      <span className="text-sm font-semibold text-slate-700">{label}</span>
    </>
  );
  const cls = `rounded-2xl border p-4 ${hot ? "border-accent-400 bg-accent-100" : "border-slate-200"}`;
  return to ? <Link to={to} className={`${cls} transition-colors hover:border-brand-600`}>{body}</Link> : <div className={cls}>{body}</div>;
};

export default function Overview() {
  const { stats: s } = useOutletContext();
  const [feed, setFeed] = useState([]);
  useEffect(() => { api.get("/api/admin/activity", { params: { limit: 8 } }).then((r) => setFeed(r.data)).catch(() => {}); }, []);
  if (!s) return <p className="text-slate-500">Loading…</p>;

  const todo = [
    [s.verification_pending, "verification application", "/admin/verifications"],
    [s.open_reports, "open report", "/admin/reports"],
    [s.unread_messages, "unread contact message", "/admin/messages"],
  ].filter(([n]) => n > 0);

  const group = (title, cards) => (
    <div>
      <h2 className="text-xl font-bold">{title}</h2>
      <div className="mt-3 grid grid-cols-2 gap-3 md:grid-cols-4">{cards}</div>
    </div>
  );

  return (
    <div className="space-y-8">
      <div className="rounded-2xl bg-brand-50 p-5">
        <h2 className="text-xl font-bold">Needs your attention</h2>
        {todo.length === 0 ? <p className="mt-2 text-slate-700">Nothing is waiting for you right now.</p> : (
          <ul className="mt-3 flex flex-wrap gap-3">
            {todo.map(([n, label, to]) => (
              <li key={to}><Link to={to} className="btn-accent">{n} {label}{n > 1 ? "s" : ""}</Link></li>
            ))}
          </ul>
        )}
      </div>

      {group("People", <>
        <Card label="Customers" value={s.customers} to="/admin/users" />
        <Card label="Artisans" value={s.artisans} to="/admin/users" />
        <Card label="New in the last 7 days" value={s.new_users_7d} />
        <Card label="Suspended accounts" value={s.suspended_users} to="/admin/users" hot={s.suspended_users > 0} />
      </>)}
      {group("Trust and safety", <>
        <Card label="Awaiting verification" value={s.verification_pending} to="/admin/verifications" hot={s.verification_pending > 0} />
        <Card label="Verified artisans" value={s.verification_approved} />
        <Card label="Open reports" value={s.open_reports} to="/admin/reports" hot={s.open_reports > 0} />
        <Card label="Unread messages" value={s.unread_messages} to="/admin/messages" hot={s.unread_messages > 0} />
      </>)}
      {group("Marketplace", <>
        <Card label="Service requests" value={s.requests_total} to="/admin/requests" />
        <Card label="Active jobs" value={s.requests_active} />
        <Card label="Completed jobs" value={s.requests_completed} />
        <Card label="Reviews" value={s.reviews_total} />
        <Card label="Featured artisans" value={s.featured_artisans} to="/admin/users" />
        <Card label="Premium artisans" value={s.premium_artisans} />
        <Card label="Waiting for an answer" value={s.requests_pending} />
        <Card label="Cancelled or declined" value={s.requests_closed} />
        <Card label="Confirmed revenue" value={formatMoney(s.revenue_ghs)} to="/admin/payments" />
        <Card label="Active Premium plans" value={s.active_premium} />
        <Card label="Unconfirmed payments" value={s.payments_pending} to="/admin/payments" />
      </>)}

      <div>
        <div className="flex items-end justify-between"><h2 className="text-xl font-bold">Recent activity</h2><Link to="/admin/activity" className="font-semibold text-brand-700 underline">See all</Link></div>
        <ul className="mt-3 divide-y divide-slate-100 rounded-2xl border border-slate-200">
          {feed.length === 0 && <li className="p-4 text-slate-500">No activity yet.</li>}
          {feed.map((i, k) => <li key={k} className="flex justify-between gap-4 p-4"><span>{i.text}</span><span className="shrink-0 text-sm text-slate-500">{timeAgo(i.at)}</span></li>)}
        </ul>
      </div>
    </div>
  );
}
