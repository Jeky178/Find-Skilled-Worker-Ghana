import { useCallback, useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { CalendarDays, MapPin, MessageCircle, Phone } from "lucide-react";
import api, { getErrorMessage, mediaUrl } from "../services/api";
import StatusBadge from "../components/StatusBadge";
import ReviewCard from "../components/ReviewCard";
import StarInput from "../components/StarInput";
import Lightbox from "../components/Lightbox";
import Avatar from "../components/Avatar";
import ReportDialog from "../components/ReportDialog";
import { formatDay, timeAgo } from "../utils";

const ACTION_LABELS = {
  accepted: ["Accept request", "btn-primary"], rejected: ["Decline", "btn-outline"], in_progress: ["Start work", "btn-primary"],
  completed: ["Mark as completed", "btn-accent"], cancelled: ["Cancel", "btn-outline"],
};
const NEEDS_FORM = ["rejected", "cancelled"];

export default function RequestDetails() {
  const { id } = useParams();
  const [req, setReq] = useState(null);
  const [error, setError] = useState("");
  const [notFound, setNotFound] = useState(false);
  const [busy, setBusy] = useState(false);
  const [pendingAction, setPendingAction] = useState(null);
  const [note, setNote] = useState("");
  const [photo, setPhoto] = useState(null);
  const [reporting, setReporting] = useState(false);
  const [rating, setRating] = useState(0);
  const [comment, setComment] = useState("");
  const [msg, setMsg] = useState({ type: "", text: "" });

  const load = useCallback(() => {
    api.get(`/api/requests/${id}`)
      .then((res) => setReq(res.data))
      .catch((e) => (e.response?.status === 404 || e.response?.status === 422 ? setNotFound(true) : setError(getErrorMessage(e))));
  }, [id]);
  useEffect(() => { load(); }, [load]);

  const changeStatus = async (status, noteText) => {
    setBusy(true); setMsg({ type: "", text: "" });
    try {
      const res = await api.patch(`/api/requests/${id}/status`, { status, note: noteText || null });
      setReq(res.data); setPendingAction(null); setNote("");
      window.dispatchEvent(new Event("notifications:changed"));
    } catch (err) { setMsg({ type: "error", text: getErrorMessage(err) }); } finally { setBusy(false); }
  };

  const onAction = (status) => {
    if (NEEDS_FORM.includes(status)) { setPendingAction(status); setMsg({ type: "", text: "" }); return; }
    if (status === "completed" && !window.confirm("Mark this job as completed? You cannot undo this.")) return;
    changeStatus(status);
  };

  const submitReview = async (e) => {
    e.preventDefault();
    if (!rating) { setMsg({ type: "error", text: "Please choose a star rating." }); return; }
    setBusy(true); setMsg({ type: "", text: "" });
    try {
      await api.post(`/api/requests/${id}/review`, { rating, comment });
      load(); setMsg({ type: "ok", text: "Thank you. Your review has been posted." });
    } catch (err) { setMsg({ type: "error", text: getErrorMessage(err) }); } finally { setBusy(false); }
  };

  if (notFound) {
    return (
      <section className="mx-auto max-w-xl px-4 py-24 text-center">
        <h1 className="text-3xl font-bold">Request not found</h1>
        <p className="mt-2 text-slate-600">It does not exist, or you do not have access to it.</p>
        <Link to="/requests" className="btn-primary mt-6">Back to my requests</Link>
      </section>
    );
  }
  if (error) return <p role="alert" className="mx-auto my-16 max-w-xl rounded-2xl bg-accent-100 p-4 text-accent-700">{error}</p>;
  if (!req) return <p className="p-16 text-center text-slate-500">Loading request…</p>;

  const isArtisan = req.viewer_role === "artisan";
  const isCustomer = req.viewer_role === "customer";
  const other = isArtisan ? req.customer : req.artisan;
  const needsNote = isArtisan; // artisans must explain a decline or a cancellation
  const box = "rounded-3xl border border-slate-200 p-6";

  return (
    <section className="mx-auto max-w-5xl px-4 py-10">
      <Link to="/requests" className="text-sm font-semibold text-brand-700 underline">Back to requests</Link>
      <div className="mt-3 flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-3xl font-bold">{req.title}</h1>
          <p className="mt-1 text-slate-600">{req.category} · sent {timeAgo(req.created_at)}</p>
        </div>
        <StatusBadge status={req.status} />
      </div>

      {msg.text && (
        <p role={msg.type === "error" ? "alert" : "status"} className={`mt-5 rounded-xl p-3 ${msg.type === "error" ? "bg-accent-100 text-accent-700" : "bg-green-50 text-green-800"}`}>{msg.text}</p>
      )}
      {req.status_note && ["rejected", "cancelled"].includes(req.status) && (
        <p className="mt-5 rounded-xl bg-slate-100 p-3 text-slate-700"><span className="font-semibold">Reason: </span>{req.status_note}</p>
      )}

      <div className="mt-8 grid gap-6 lg:grid-cols-[1fr_320px]">
        <div className="space-y-6">
          <div className={box}>
            <h2 className="text-xl font-bold">The problem</h2>
            <p className="mt-3 whitespace-pre-line text-lg text-slate-700">{req.description}</p>
            <ul className="mt-4 space-y-2 text-slate-700">
              <li className="flex items-center gap-2"><MapPin size={18} aria-hidden="true" />{req.location}</li>
              {req.preferred_date && <li className="flex items-center gap-2"><CalendarDays size={18} aria-hidden="true" />Preferred date: {formatDay(req.preferred_date)}</li>}
            </ul>
            {req.photos.length > 0 && (
              <ul className="mt-5 grid grid-cols-3 gap-3 sm:grid-cols-4">
                {req.photos.map((p, i) => (
                  <li key={p}>
                    <button onClick={() => setPhoto(p)} className="block w-full overflow-hidden rounded-xl" aria-label={`View photo ${i + 1}`}>
                      <img src={mediaUrl(p)} alt={`Problem photo ${i + 1}`} loading="lazy" className="aspect-square w-full object-cover transition-transform hover:scale-105" />
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </div>

          {req.status === "completed" && (
            <div className={box}>
              <h2 className="text-xl font-bold">Review</h2>
              {req.review ? (
                <div className="mt-3"><ReviewCard review={req.review} /></div>
              ) : isCustomer ? (
                <form onSubmit={submitReview} className="mt-3 space-y-3">
                  <p className="text-slate-600">How was the service? Your review helps other customers.</p>
                  <StarInput value={rating} onChange={setRating} />
                  <div>
                    <label htmlFor="comment" className="label">Your comments (optional)</label>
                    <textarea id="comment" rows={4} maxLength={1500} className="field resize-y" placeholder="What went well? Was the work neat and on time?" value={comment} onChange={(e) => setComment(e.target.value)} />
                  </div>
                  <button className="btn-accent" disabled={busy}>{busy ? "Posting…" : "Post review"}</button>
                </form>
              ) : (
                <p className="mt-3 text-slate-600">{isArtisan ? "Waiting for the customer to leave a review." : "No review has been left yet."}</p>
              )}
            </div>
          )}
        </div>

        <aside className="space-y-6">
          <div className={box}>
            <h2 className="text-lg font-bold">{isArtisan ? "Customer" : "Artisan"}</h2>
            <div className="mt-3 flex items-center gap-3">
              <Avatar name={other.name} src={other.profile_image} size="h-12 w-12" text="text-base" />
              <div>
                <p className="font-display font-bold text-brand-900">{other.name}</p>
                {!isArtisan && other.id && <Link to={`/artisans/${other.id}`} className="text-sm font-semibold text-brand-700 underline">View profile</Link>}
              </div>
            </div>
            {req.other_contact ? (
              <div className="mt-4 space-y-2">
                {req.other_contact.whatsapp_url && <a href={req.other_contact.whatsapp_url} target="_blank" rel="noreferrer" className="btn-accent w-full"><MessageCircle size={18} aria-hidden="true" /> WhatsApp</a>}
                {req.other_contact.phone && <a href={`tel:+${req.other_contact.phone}`} className="btn-outline w-full"><Phone size={18} aria-hidden="true" /> +{req.other_contact.phone}</a>}
              </div>
            ) : isArtisan && (
              <p className="mt-4 rounded-xl bg-slate-50 p-3 text-sm text-slate-600">The customer&apos;s phone number is shared once you accept the request.</p>
            )}
          </div>

          {req.viewer_role !== "admin" && (
            <button onClick={() => setReporting(true)} className="text-sm font-semibold text-slate-600 underline hover:text-brand-800">Report a problem with this job</button>
          )}

          {req.allowed_actions.length > 0 && (
            <div className={box}>
              <h2 className="text-lg font-bold">What would you like to do?</h2>
              {pendingAction ? (
                <form className="mt-3 space-y-3" onSubmit={(e) => { e.preventDefault(); changeStatus(pendingAction, note); }}>
                  <label htmlFor="note" className="label">{pendingAction === "rejected" ? "Why can you not take this job?" : needsNote ? "Why are you cancelling?" : "Reason (optional)"}</label>
                  <textarea id="note" rows={3} maxLength={500} required={needsNote} className="field resize-y" value={note} onChange={(e) => setNote(e.target.value)} />
                  <div className="flex gap-2">
                    <button className="btn-primary flex-1" disabled={busy}>{busy ? "Saving…" : "Confirm"}</button>
                    <button type="button" className="btn-outline" onClick={() => setPendingAction(null)}>Back</button>
                  </div>
                </form>
              ) : (
                <div className="mt-3 flex flex-col gap-2">
                  {[...req.allowed_actions].sort((a, b) => (ACTION_LABELS[a][1] === "btn-outline") - (ACTION_LABELS[b][1] === "btn-outline")).map((a) => (
                    <button key={a} className={`${ACTION_LABELS[a][1]} w-full`} disabled={busy} onClick={() => onAction(a)}>
                      {a === "cancelled" && isCustomer ? "Cancel request" : a === "cancelled" ? "Cancel job" : ACTION_LABELS[a][0]}
                    </button>
                  ))}
                </div>
              )}
            </div>
          )}
        </aside>
      </div>

      {reporting && <ReportDialog requestId={req.id} targetName={other.name} onClose={() => setReporting(false)} />}
      {photo && <Lightbox src={mediaUrl(photo)} onClose={() => setPhoto(null)} />}
    </section>
  );
}
