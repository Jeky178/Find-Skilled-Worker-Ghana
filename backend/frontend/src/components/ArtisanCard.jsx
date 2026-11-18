import { Link } from "react-router-dom";
import { Briefcase, MapPin } from "lucide-react";
import Avatar from "./Avatar";
import Stars from "./Stars";
import Badges from "./Badges";
import { formatPrice } from "../utils";

export default function ArtisanCard({ artisan }) {
  const price = formatPrice(artisan.price_min, artisan.price_max);
  return (
    <Link
      to={`/artisans/${artisan.id}`}
      className="flex flex-col rounded-2xl border border-slate-200 p-5 transition-colors hover:border-brand-600 hover:bg-brand-50/40"
    >
      <div className="flex items-start gap-4">
        <Avatar name={artisan.name} src={artisan.profile_image} />
        <div className="min-w-0">
          <h3 className="truncate font-display text-lg font-bold text-brand-900">{artisan.name}</h3>
          <p className="font-semibold text-accent-700">{artisan.category.name}</p>
          <Stars rating={artisan.avg_rating} count={artisan.review_count} size={14} />
        </div>
      </div>

      {artisan.headline && <p className="mt-3 line-clamp-2 text-slate-700">{artisan.headline}</p>}

      <ul className="mt-3 space-y-1 text-sm text-slate-600">
        {artisan.locations.length > 0 && (
          <li className="flex items-start gap-2"><MapPin size={16} className="mt-0.5 shrink-0" aria-hidden="true" />{artisan.locations.slice(0, 3).join(", ")}{artisan.locations.length > 3 ? ` +${artisan.locations.length - 3}` : ""}</li>
        )}
        {artisan.years_experience > 0 && (
          <li className="flex items-center gap-2"><Briefcase size={16} className="shrink-0" aria-hidden="true" />{artisan.years_experience} years experience</li>
        )}
      </ul>

      <div className="mt-4 flex flex-wrap items-center justify-between gap-2 border-t border-slate-100 pt-3">
        <span className="font-display font-bold text-brand-900">{price || "Ask for a quote"}</span>
        <Badges artisan={artisan} />
      </div>
    </Link>
  );
}
