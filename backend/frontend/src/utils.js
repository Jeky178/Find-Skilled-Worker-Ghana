export const formatMoney = (n) => `GH₵${Number(n).toLocaleString("en-GH", { maximumFractionDigits: 2 })}`;

/** "GH₵80 – GH₵300", "From GH₵80", or "" when no price is set. */
export function formatPrice(min, max) {
  const hasMin = min !== null && min !== undefined && min !== "";
  const hasMax = max !== null && max !== undefined && max !== "";
  if (hasMin && hasMax) return Number(min) === Number(max) ? formatMoney(min) : `${formatMoney(min)} – ${formatMoney(max)}`;
  if (hasMin) return `From ${formatMoney(min)}`;
  if (hasMax) return `Up to ${formatMoney(max)}`;
  return "";
}

export const initials = (name = "") =>
  name.split(" ").filter(Boolean).slice(0, 2).map((w) => w[0].toUpperCase()).join("");

export const formatDate = (iso) =>
  new Date(iso).toLocaleDateString("en-GB", { month: "long", year: "numeric" });

/** The API sends UTC times; SQLite omits the timezone marker, so add it before parsing. */
export const parseDate = (iso) => new Date(/[zZ]|[+-]\d\d:?\d\d$/.test(iso) ? iso : `${iso}Z`);

export function timeAgo(iso) {
  const seconds = Math.max(0, (Date.now() - parseDate(iso).getTime()) / 1000);
  if (seconds < 60) return "just now";
  if (seconds < 3600) return `${Math.floor(seconds / 60)} min ago`;
  if (seconds < 86400) return `${Math.floor(seconds / 3600)} h ago`;
  if (seconds < 7 * 86400) return `${Math.floor(seconds / 86400)} days ago`;
  return parseDate(iso).toLocaleDateString("en-GB", { day: "numeric", month: "short", year: "numeric" });
}

export const formatDay = (value) =>
  new Date(value).toLocaleDateString("en-GB", { weekday: "short", day: "numeric", month: "short", year: "numeric" });

export const STATUS = {
  pending: { label: "Awaiting response", cls: "bg-accent-100 text-accent-700" },
  accepted: { label: "Accepted", cls: "bg-brand-100 text-brand-800" },
  in_progress: { label: "In progress", cls: "bg-brand-100 text-brand-800" },
  completed: { label: "Completed", cls: "bg-green-100 text-green-800" },
  rejected: { label: "Declined", cls: "bg-slate-100 text-slate-700" },
  cancelled: { label: "Cancelled", cls: "bg-slate-100 text-slate-700" },
};
