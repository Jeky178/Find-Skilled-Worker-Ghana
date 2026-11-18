import { useCallback, useEffect, useState } from "react";
import { NavLink, Outlet } from "react-router-dom";
import api from "../../services/api";

export default function AdminLayout() {
  const [stats, setStats] = useState(null);
  const refreshStats = useCallback(() => {
    api.get("/api/admin/stats").then((r) => setStats(r.data)).catch(() => {});
  }, []);
  useEffect(() => { refreshStats(); }, [refreshStats]);

  const tabs = [
    ["/admin", "Overview", 0, true],
    ["/admin/verifications", "Verifications", stats?.verification_pending],
    ["/admin/users", "Users"],
    ["/admin/requests", "Requests"],
    ["/admin/reports", "Reports", stats?.open_reports],
    ["/admin/messages", "Messages", stats?.unread_messages],
    ["/admin/payments", "Payments", stats?.payments_pending],
    ["/admin/categories", "Categories"],
    ["/admin/activity", "Activity"],
  ];

  return (
    <section className="mx-auto max-w-6xl px-4 py-8">
      <h1 className="text-3xl font-bold">Administration</h1>
      <nav aria-label="Admin sections" className="-mx-4 mt-5 overflow-x-auto px-4">
        <ul className="flex min-w-max gap-2 border-b border-slate-200 pb-3">
          {tabs.map(([to, label, badge, end]) => (
            <li key={to}>
              <NavLink to={to} end={end}
                className={({ isActive }) => `inline-flex items-center gap-2 rounded-full px-4 py-2 font-semibold transition-colors ${isActive ? "bg-brand-800 text-white" : "text-slate-700 hover:bg-brand-50"}`}>
                {label}
                {badge > 0 && <span className="grid min-w-[1.25rem] place-items-center rounded-full bg-accent-600 px-1.5 text-xs font-bold text-white">{badge}</span>}
              </NavLink>
            </li>
          ))}
        </ul>
      </nav>
      <div className="mt-6"><Outlet context={{ stats, refreshStats }} /></div>
    </section>
  );
}
