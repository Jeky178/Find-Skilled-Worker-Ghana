import { Star } from "lucide-react";

const LABELS = ["Poor", "Fair", "Good", "Very good", "Excellent"];

/** Clickable 1-5 star selector. */
export default function StarInput({ value, onChange }) {
  return (
    <div>
      <div role="radiogroup" aria-label="Your rating" className="flex gap-1">
        {[1, 2, 3, 4, 5].map((n) => (
          <button key={n} type="button" role="radio" aria-checked={value === n} aria-label={`${n} star${n > 1 ? "s" : ""}: ${LABELS[n - 1]}`}
            onClick={() => onChange(n)} className="rounded p-1">
            <Star size={32} className={n <= value ? "fill-accent-500 text-accent-500" : "text-slate-300 hover:text-accent-400"} />
          </button>
        ))}
      </div>
      <p className="mt-1 h-5 text-sm font-semibold text-brand-900" aria-live="polite">{value ? LABELS[value - 1] : ""}</p>
    </div>
  );
}
