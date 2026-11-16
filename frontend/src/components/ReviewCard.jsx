import Stars from "./Stars";
import { timeAgo } from "../utils";

export default function ReviewCard({ review, showJob = false }) {
  return (
    <article className="rounded-2xl border border-slate-200 p-5">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <Stars rating={review.rating} count={1} size={16} showCount={false} />
        <time className="text-sm text-slate-500" dateTime={review.created_at}>{timeAgo(review.created_at)}</time>
      </div>
      {review.comment && <p className="mt-3 whitespace-pre-line text-slate-700">{review.comment}</p>}
      <p className="mt-3 text-sm font-semibold text-brand-900">
        {review.reviewer_name}
        {showJob && review.artisan_name && <span className="font-normal text-slate-600"> · reviewed {review.artisan_name}{review.category ? ` (${review.category})` : ""}</span>}
        {showJob && !review.artisan_name && review.category && <span className="font-normal text-slate-600"> · {review.category}</span>}
      </p>
    </article>
  );
}
