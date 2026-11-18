import { Star } from "lucide-react";

export default function Stars({ rating = 0, count = 0, size = 16, showCount = true }) {
  const value = Number(rating) || 0;
  if (!count) return <span className="text-sm text-slate-500">No reviews yet</span>;
  return (
    <span className="inline-flex items-center gap-1.5" aria-label={showCount ? `Rated ${value.toFixed(1)} out of 5 from ${count} ${count === 1 ? "review" : "reviews"}` : `Rated ${value.toFixed(0)} out of 5`}>
      <span className="flex" aria-hidden="true">
        {[1, 2, 3, 4, 5].map((n) => (
          <Star key={n} size={size} className={n <= Math.round(value) ? "fill-accent-500 text-accent-500" : "text-slate-300"} />
        ))}
      </span>
      <span className="text-sm font-semibold text-brand-900">{value.toFixed(1)}</span>
      {showCount && <span className="text-sm text-slate-500">({count})</span>}
    </span>
  );
}
