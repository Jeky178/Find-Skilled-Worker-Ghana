import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { Briefcase, CalendarDays, MapPin, MessageCircle, Phone, ShieldCheck, X } from "lucide-react";
import api, { getErrorMessage, mediaUrl } from "../services/api";
import { useAuth } from "../context/AuthContext";
import ArtisanReviews from "../components/ArtisanReviews";
import ReportDialog from "../components/ReportDialog";
import Avatar from "../components/Avatar";
import Stars from "../components/Stars";
import Badges from "../components/Badges";
import { formatDate, formatPrice } from "../utils";

export default function ArtisanDetails() {
  const { id } = useParams();
  const { user } = useAuth();
  const [artisan, setArtisan] = useState(null);
  const [error, setError] = useState("");
  const [notFound, setNotFound] = useState(false);
  const [photo, setPhoto] = useState(null);
  const [reporting, setReporting] = useState(false);

  useEffect(() => {
    let cancelled = false;
    setArtisan(null); setError(""); setNotFound(false);
    api.get(`/api/artisans/${id}`)
      .then((res) => { if (!cancelled) setArtisan(res.data); })
      .catch((e) => {
        if (cancelled) return;
        if (e.response?.status === 404 || e.response?.status === 422) setNotFound(true);
        else setError(getErrorMessage(e));
      });
    return () => { cancelled = true; };
  }, [id]);

  // Close the photo viewer with the Escape key.
  useEffect(() => {
    if (!photo) return undefined;
    const onKey = (e) => e.key === "Escape" && setPhoto(null);
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [photo]);

  if (notFound) {
    return (
      <section className="mx-auto max-w-xl px-4 py-24 text-center">
        <h1 className="text-3xl font-bold">Artisan not found</h1>
        <p className="mt-2 text-slate-600">This profile does not exist or is no longer available.</p>
        <Link to="/artisans" className="btn-primary mt-6">Browse artisans</Link>
      </section>
    );
  }
  if (error) return <p role="alert" className="mx-auto my-16 max-w-xl rounded-2xl bg-accent-100 p-4 text-accent-700">{error}</p>;
  if (!artisan) return <p className="p-16 text-center text-slate-500">Loading profile…</p>;

  const price = formatPrice(artisan.price_min, artisan.price_max);

  return (
    <>
      <section className="bg-brand-50">
        <div className="mx-auto max-w-6xl px-4 py-10">
          <Link to="/artisans" className="text-sm font-semibold text-brand-700 underline">Back to all artisans</Link>
          <div className="mt-5 flex flex-col gap-5 sm:flex-row sm:items-center">
            <Avatar name={artisan.name} src={artisan.profile_image} size="h-28 w-28" text="text-4xl" />
            <div>
              <h1 className="text-3xl font-extrabold md:text-4xl">{artisan.name}</h1>
              <p className="mt-1 text-lg font-semibold text-accent-700">{artisan.category.name}</p>
              <div className="mt-2 flex flex-wrap items-center gap-3">
                <Stars rating={artisan.avg_rating} count={artisan.review_count} />
                <Badges artisan={artisan} />
              </div>
            </div>
          </div>
        </div>
      </section>

      <div className="mx-auto grid max-w-6xl gap-10 px-4 py-10 lg:grid-cols-[1fr_340px]">
        <div className="space-y-10">
          {artisan.headline && <p className="font-display text-2xl font-bold text-brand-900">{artisan.headline}</p>}

          <section>
            <h2 className="text-2xl font-bold">About</h2>
            {artisan.bio
              ? <p className="mt-3 max-w-prose whitespace-pre-line text-lg text-slate-700">{artisan.bio}</p>
              : <p className="mt-3 text-slate-500">This artisan has not added a description yet.</p>}
            <ul className="mt-5 space-y-2 text-slate-700">
              {artisan.years_experience > 0 && <li className="flex items-center gap-2"><Briefcase size={18} aria-hidden="true" />{artisan.years_experience} years of experience</li>}
              {artisan.locations.length > 0 && <li className="flex items-start gap-2"><MapPin size={18} className="mt-0.5" aria-hidden="true" />Works in {artisan.locations.join(", ")}</li>}
              <li className="flex items-center gap-2"><CalendarDays size={18} aria-hidden="true" />Member since {formatDate(artisan.member_since)}</li>
            </ul>
          </section>

          <section>
            <h2 className="text-2xl font-bold">Previous work</h2>
            {artisan.portfolio.length === 0 ? (
              <p className="mt-3 text-slate-500">No photos of completed work yet.</p>
            ) : (
              <ul className="mt-4 grid grid-cols-2 gap-3 md:grid-cols-3">
                {artisan.portfolio.map((p) => (
                  <li key={p.id}>
                    <button onClick={() => setPhoto(p)} className="group block w-full overflow-hidden rounded-2xl" aria-label={`View photo${p.caption ? `: ${p.caption}` : ""}`}>
                      <img src={mediaUrl(p.image_url)} alt={p.caption || "Completed work"} loading="lazy" className="aspect-square w-full object-cover transition-transform group-hover:scale-105" />
                    </button>
                    {p.caption && <p className="mt-1 text-sm text-slate-600">{p.caption}</p>}
                  </li>
                ))}
              </ul>
            )}
          </section>

          <ArtisanReviews artisanId={artisan.id} />
        </div>

        <aside className="lg:sticky lg:top-24 lg:self-start">
          <div className="rounded-3xl border border-slate-200 p-6 shadow-lg shadow-brand-900/5">
            <p className="text-sm text-slate-600">Price</p>
            <p className="font-display text-2xl font-bold text-brand-900">{price || "Ask for a quote"}</p>
            {artisan.price_note && <p className="text-sm text-slate-600">{artisan.price_note}</p>}
            <p className={`mt-3 font-semibold ${artisan.is_available ? "text-green-700" : "text-slate-500"}`}>
              {artisan.is_available ? "Available for new jobs" : "Currently unavailable"}
            </p>

            <div className="mt-5 space-y-3">
              {(!user || user.role === "customer") && (
                artisan.is_available ? (
                  <Link to={`/artisans/${artisan.id}/request`} state={{ from: `/artisans/${artisan.id}/request` }} className="btn-primary w-full py-3">
                    Request this artisan
                  </Link>
                ) : (
                  <p className="rounded-xl bg-slate-50 p-3 text-sm text-slate-600">{artisan.name} is not taking new requests right now.</p>
                )
              )}
              {artisan.whatsapp_url ? (
                <a href={artisan.whatsapp_url} target="_blank" rel="noreferrer" className="btn-accent w-full py-3">
                  <MessageCircle size={20} aria-hidden="true" /> Chat on WhatsApp
                </a>
              ) : (
                <p className="rounded-xl bg-slate-50 p-3 text-sm text-slate-600">This artisan has not added a WhatsApp number yet.</p>
              )}
              {artisan.phone && (
                <a href={`tel:+${artisan.phone}`} className="btn-outline w-full py-3"><Phone size={20} aria-hidden="true" /> Call +{artisan.phone}</a>
              )}
            </div>

            <p className="mt-5 flex gap-2 text-sm text-slate-600">
              <ShieldCheck size={18} className="mt-0.5 shrink-0 text-brand-700" aria-hidden="true" />
              Agree on the price and the work before you start, and pay for finished work only.
            </p>
            {user?.role === "customer" && (
              <button onClick={() => setReporting(true)} className="mt-4 text-sm font-semibold text-slate-600 underline hover:text-brand-800">Report this profile</button>
            )}
          </div>
        </aside>
      </div>

      {reporting && <ReportDialog artisanId={artisan.id} targetName={artisan.name} onClose={() => setReporting(false)} />}

      {photo && (
        <div role="dialog" aria-modal="true" aria-label="Photo viewer" className="fixed inset-0 z-50 grid place-items-center bg-brand-900/90 p-4" onClick={() => setPhoto(null)}>
          <button className="absolute right-4 top-4 rounded-full bg-white p-2" onClick={() => setPhoto(null)} aria-label="Close photo"><X size={20} /></button>
          <figure onClick={(e) => e.stopPropagation()} className="max-h-full">
            <img src={mediaUrl(photo.image_url)} alt={photo.caption || "Completed work"} className="max-h-[80vh] rounded-2xl" />
            {photo.caption && <figcaption className="mt-2 text-center text-white">{photo.caption}</figcaption>}
          </figure>
        </div>
      )}
    </>
  );
}
