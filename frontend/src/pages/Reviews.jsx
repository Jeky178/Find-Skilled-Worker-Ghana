import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { MessageSquareText } from "lucide-react";
import api, { getErrorMessage } from "../services/api";
import { useAuth } from "../context/AuthContext";
import ReviewCard from "../components/ReviewCard";
import Stars from "../components/Stars";

export default function Reviews() {
  const { user } = useAuth();
  const isArtisan = user.role === "artisan";
  const [data, setData] = useState(null);
  const [page, setPage] = useState(1);
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;
    api.get("/api/reviews/mine", { params: { page, page_size: 10 } })
      .then((res) => { if (!cancelled) setData(res.data); })
      .catch((e) => { if (!cancelled) setError(getErrorMessage(e)); });
    return () => { cancelled = true; };
  }, [page]);

  return (
    <section className="mx-auto max-w-3xl px-4 py-10">
      <h1 className="text-3xl font-bold">{isArtisan ? "Reviews from customers" : "Reviews you have written"}</h1>
      {isArtisan && data && (
        <div className="mt-4 rounded-2xl bg-brand-50 p-5">
          <p className="font-display text-4xl font-extrabold text-brand-900">{Number(data.avg_rating || 0).toFixed(1)}</p>
          <Stars rating={data.avg_rating} count={data.review_count} />
        </div>
      )}
      {error && <p role="alert" className="mt-6 rounded-2xl bg-accent-100 p-4 text-accent-700">{error}</p>}
      {!data && !error && <p className="mt-8 text-slate-500">Loading…</p>}

      {data && data.items.length === 0 && (
        <div className="mt-6 rounded-2xl border border-dashed border-brand-200 bg-brand-50 p-10 text-center">
          <MessageSquareText size={36} className="mx-auto text-brand-600" aria-hidden="true" />
          <h2 className="mt-3 text-xl font-bold">No reviews yet</h2>
          <p className="mt-1 text-slate-600">{isArtisan ? "Reviews appear here after customers rate your completed jobs." : "After a job is completed, you can rate the artisan from the request page."}</p>
          <Link to="/requests" className="btn-primary mt-4">Go to my requests</Link>
        </div>
      )}
      {data && data.items.length > 0 && <div className="mt-6 space-y-3">{data.items.map((r) => <ReviewCard key={r.id} review={r} showJob />)}</div>}

      {data && data.pages > 1 && (
        <nav className="mt-8 flex items-center justify-center gap-4" aria-label="Pagination">
          <button className="btn-outline" disabled={page <= 1} onClick={() => setPage(page - 1)}>Previous</button>
          <span className="font-semibold text-brand-900">Page {data.page} of {data.pages}</span>
          <button className="btn-outline" disabled={page >= data.pages} onClick={() => setPage(page + 1)}>Next</button>
        </nav>
      )}
    </section>
  );
}
