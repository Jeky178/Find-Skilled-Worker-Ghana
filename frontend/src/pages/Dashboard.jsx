import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import api from "../services/api";
import { useAuth } from "../context/AuthContext";

const ROLE_LABEL = { customer: "Customer", artisan: "Artisan", admin: "Administrator" };
const VERIFY_LABEL = {
  unverified: "Not verified yet",
  pending: "Verification under review",
  approved: "Verified",
  rejected: "Verification rejected",
};

export default function Dashboard() {
  const { user } = useAuth();
  const [mine, setMine] = useState(null);
  const [stats, setStats] = useState(null);

  useEffect(() => {
    if (user.role !== "artisan") return;
    api.get("/api/artisan/me").then((res) => setMine(res.data)).catch(() => {});
  }, [user.role]);

  useEffect(() => {
    if (user.role === "admin") return;
    api.get("/api/requests/summary").then((res) => setStats(res.data)).catch(() => {});
  }, [user.role]);

  const profile = mine || user.artisan_profile;

  return (
    <section className="mx-auto max-w-4xl px-4 py-12">
      <h1 className="text-3xl font-bold">Hello, {user.full_name.split(" ")[0]}</h1>
      <p className="mt-1 text-slate-600">{ROLE_LABEL[user.role]} account · {user.email}</p>

      {stats && (
        <div className="mt-8 grid grid-cols-3 gap-3">
          {[[user.role === "artisan" ? "New requests" : "Awaiting reply", stats.pending, "pending"], ["In progress", stats.active, "active"], ["Completed", stats.completed, "completed"]].map(([label, n, key]) => (
            <Link key={key} to={key === "pending" ? "/requests?status=pending" : key === "active" ? "/requests?status=active" : "/requests?status=completed"}
              className={`rounded-2xl border p-4 transition-colors hover:border-brand-600 ${key === "pending" && n > 0 ? "border-accent-400 bg-accent-100" : "border-slate-200"}`}>
              <span className="block font-display text-3xl font-extrabold text-brand-900">{n}</span>
              <span className="text-sm font-semibold text-slate-700">{label}</span>
            </Link>
          ))}
        </div>
      )}

      <div className="mt-6 grid gap-4 md:grid-cols-2">
        {user.role === "artisan" && profile && (
          <div className="rounded-2xl border border-slate-200 p-6">
            <h2 className="text-xl font-bold">Your profile</h2>
            <dl className="mt-3 space-y-2">
              <div className="flex justify-between"><dt className="text-slate-600">Verification</dt><dd className="font-semibold"><Link to="/dashboard/verification" className="hover:underline">{VERIFY_LABEL[profile.verification_status]}</Link></dd></div>
              <div className="flex justify-between"><dt className="text-slate-600">Plan</dt><dd className="font-semibold capitalize">{profile.plan}</dd></div>
            </dl>
            {mine && (
              <div className="mt-4">
                <p className="text-sm font-semibold text-brand-900">Profile {mine.completeness}% complete</p>
                <div className="mt-1 h-2.5 overflow-hidden rounded-full bg-brand-50" role="progressbar" aria-valuenow={mine.completeness} aria-valuemin={0} aria-valuemax={100}>
                  <div className="h-full rounded-full bg-accent-500" style={{ width: `${mine.completeness}%` }} />
                </div>
              </div>
            )}
            <div className="mt-4 flex flex-wrap gap-2">
              <Link to="/dashboard/profile" className="btn-accent">Edit my profile</Link>
              {profile && ["unverified", "rejected"].includes(profile.verification_status) && <Link to="/dashboard/verification" className="btn-outline">Get verified</Link>}
              <Link to="/reviews" className="btn-outline">My reviews</Link>
              <Link to="/dashboard/billing" className="btn-outline">Plans and billing</Link>
              {mine && <Link to={`/artisans/${mine.id}`} className="btn-outline">View public profile</Link>}
            </div>
          </div>
        )}
        {user.role === "customer" && (
          <div className="rounded-2xl border border-slate-200 p-6">
            <h2 className="text-xl font-bold">Find a worker</h2>
            <p className="mt-2 text-slate-600">Search by trade and area to see who is available.</p>
            <div className="mt-4 flex flex-wrap gap-2">
              <Link to="/artisans" className="btn-accent">Browse artisans</Link>
              <Link to="/requests" className="btn-outline">My requests</Link>
              <Link to="/reviews" className="btn-outline">My reviews</Link>
            </div>
          </div>
        )}
        {user.role === "admin" && (
          <div className="rounded-2xl border border-slate-200 p-6">
            <h2 className="text-xl font-bold">Administration</h2>
            <p className="mt-2 text-slate-600">Approve artisans, handle reports, manage users, categories and featured listings.</p>
            <Link to="/admin" className="btn-accent mt-4">Open admin dashboard</Link>
          </div>
        )}
        <div className="rounded-2xl border border-slate-200 p-6">
          <h2 className="text-xl font-bold">Account</h2>
          <dl className="mt-3 space-y-2">
            <div className="flex justify-between"><dt className="text-slate-600">Name</dt><dd className="font-semibold">{user.full_name}</dd></div>
            <div className="flex justify-between"><dt className="text-slate-600">Phone</dt><dd className="font-semibold">{user.phone ? `+${user.phone}` : "Not added"}</dd></div>
          </dl>
        </div>
      </div>
    </section>
  );
}
