import { useEffect, useState } from "react";
import api, { getErrorMessage } from "../services/api";
import ReviewCard from "./ReviewCard";

/** Real customer reviews on an artisan's public page. */
export default function ArtisanReviews({ artisanId }) {
  const [items, setItems] = useState([]);
  const [page, setPage] = useState(1);
  const [pages, setPages] = useState(1);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    api.get(`/api/artisans/${artisanId}/reviews`, { params: { page, page_size: 5 } })
      .then((res) => {
        if (cancelled) return;
        setItems((prev) => (page === 1 ? res.data.items : [...prev, ...res.data.items]));
        setPages(res.data.pages);
      })
      .catch((e) => { if (!cancelled) setError(getErrorMessage(e)); })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [artisanId, page]);

  return (
    <section>
      <h2 className="text-2xl font-bold">Reviews</h2>
      {error && <p role="alert" className="mt-3 text-accent-700">{error}</p>}
      {!error && !loading && items.length === 0 && (
        <p className="mt-3 text-slate-500">No reviews yet. Reviews appear after customers complete a job.</p>
      )}
      <div className="mt-4 space-y-3">{items.map((r) => <ReviewCard key={r.id} review={r} />)}</div>
      {page < pages && (
        <button className="btn-outline mt-4" disabled={loading} onClick={() => setPage((p) => p + 1)}>{loading ? "Loading…" : "Show more reviews"}</button>
      )}
    </section>
  );
}
