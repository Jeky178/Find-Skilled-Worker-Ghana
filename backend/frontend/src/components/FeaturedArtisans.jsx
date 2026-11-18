import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import api from "../services/api";
import ArtisanCard from "./ArtisanCard";

/** Shows nothing until at least one artisan is featured, so the homepage never shows empty or fake listings. */
export default function FeaturedArtisans() {
  const [items, setItems] = useState([]);

  useEffect(() => {
    let cancelled = false;
    api.get("/api/artisans", { params: { featured_only: true, page_size: 4 } })
      .then((res) => { if (!cancelled) setItems(res.data.items); })
      .catch(() => {});
    return () => { cancelled = true; };
  }, []);

  if (items.length === 0) return null;
  return (
    <section className="mx-auto max-w-6xl px-4 pb-16">
      <div className="flex items-end justify-between gap-4">
        <h2 className="text-3xl font-bold">Featured artisans</h2>
        <Link to="/artisans" className="font-semibold text-brand-700 underline">See all artisans</Link>
      </div>
      <div className="mt-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {items.map((a) => <ArtisanCard key={a.id} artisan={a} />)}
      </div>
    </section>
  );
}
