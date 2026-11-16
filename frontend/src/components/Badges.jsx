import { BadgeCheck, Crown } from "lucide-react";

export default function Badges({ artisan }) {
  return (
    <span className="inline-flex flex-wrap items-center gap-2">
      {artisan.verification_status === "approved" && (
        <span className="inline-flex items-center gap-1 rounded-full bg-brand-50 px-2.5 py-1 text-xs font-bold text-brand-800">
          <BadgeCheck size={14} aria-hidden="true" /> Verified
        </span>
      )}
      {artisan.plan === "premium" && (
        <span className="inline-flex items-center gap-1 rounded-full bg-accent-100 px-2.5 py-1 text-xs font-bold text-accent-700">
          <Crown size={14} aria-hidden="true" /> Premium
        </span>
      )}
      {!artisan.is_available && (
        <span className="rounded-full bg-slate-100 px-2.5 py-1 text-xs font-bold text-slate-600">Currently unavailable</span>
      )}
    </span>
  );
}
