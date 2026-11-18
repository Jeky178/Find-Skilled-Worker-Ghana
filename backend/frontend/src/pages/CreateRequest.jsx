import { useEffect, useMemo, useRef, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { ImagePlus, X } from "lucide-react";
import api, { getErrorMessage } from "../services/api";
import Avatar from "../components/Avatar";
import { LOCATIONS } from "../constants";

const MAX_PHOTOS = 5;
const MAX_MB = 5;
const TYPES = ["image/jpeg", "image/png", "image/webp"];

export default function CreateRequest() {
  const { id } = useParams();
  const navigate = useNavigate();
  const fileInput = useRef(null);
  const [artisan, setArtisan] = useState(null);
  const [loadError, setLoadError] = useState("");
  const [form, setForm] = useState({ title: "", description: "", location: "", preferred_date: "" });
  const [files, setFiles] = useState([]);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    let cancelled = false;
    api.get(`/api/artisans/${id}`)
      .then((res) => {
        if (cancelled) return;
        setArtisan(res.data);
        setForm((f) => ({ ...f, location: res.data.locations[0] || "" }));
      })
      .catch((e) => { if (!cancelled) setLoadError(e.response?.status === 404 ? "This artisan could not be found." : getErrorMessage(e)); });
    return () => { cancelled = true; };
  }, [id]);

  // Local previews of the chosen photos (released when they change).
  const previews = useMemo(() => files.map((f) => URL.createObjectURL(f)), [files]);
  useEffect(() => () => previews.forEach((u) => URL.revokeObjectURL(u)), [previews]);

  const handleChange = (e) => setForm({ ...form, [e.target.name]: e.target.value });

  const addFiles = (e) => {
    const picked = Array.from(e.target.files || []);
    e.target.value = "";
    const problems = [];
    const ok = picked.filter((f) => {
      if (!TYPES.includes(f.type)) { problems.push(`${f.name} is not a JPG, PNG or WebP image`); return false; }
      if (f.size > MAX_MB * 1024 * 1024) { problems.push(`${f.name} is larger than ${MAX_MB} MB`); return false; }
      return true;
    });
    const room = MAX_PHOTOS - files.length;
    if (ok.length > room) problems.push(`You can attach up to ${MAX_PHOTOS} photos`);
    setFiles([...files, ...ok.slice(0, Math.max(0, room))]);
    setError(problems.join(". "));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    setBusy(true);
    try {
      const fd = new FormData();
      fd.append("artisan_id", id);
      fd.append("title", form.title.trim());
      fd.append("description", form.description.trim());
      fd.append("location", form.location.trim());
      if (form.preferred_date) fd.append("preferred_date", form.preferred_date);
      files.forEach((f) => fd.append("photos", f));
      const res = await api.post("/api/requests", fd);
      navigate(`/requests/${res.data.id}`, { replace: true });
    } catch (err) {
      setError(getErrorMessage(err));
      setBusy(false);
    }
  };

  if (loadError) return <p role="alert" className="mx-auto my-16 max-w-xl rounded-2xl bg-accent-100 p-4 text-accent-700">{loadError}</p>;
  if (!artisan) return <p className="p-16 text-center text-slate-500">Loading…</p>;

  if (!artisan.is_available) {
    return (
      <section className="mx-auto max-w-xl px-4 py-20 text-center">
        <h1 className="text-3xl font-bold">{artisan.name} is not taking new jobs right now</h1>
        <p className="mt-2 text-slate-600">Browse other {artisan.category.name.toLowerCase()}s who are available.</p>
        <Link to={`/artisans?category=${artisan.category.slug}&available=1`} className="btn-primary mt-6">See available {artisan.category.name.toLowerCase()}s</Link>
      </section>
    );
  }

  const areaOptions = [...new Set([...artisan.locations, ...LOCATIONS])];
  const today = new Date().toISOString().slice(0, 10);

  return (
    <section className="mx-auto max-w-2xl px-4 py-10">
      <Link to={`/artisans/${artisan.id}`} className="text-sm font-semibold text-brand-700 underline">Back to profile</Link>
      <h1 className="mt-3 text-3xl font-bold">Request a service</h1>

      <div className="mt-5 flex items-center gap-4 rounded-2xl bg-brand-50 p-4">
        <Avatar name={artisan.name} src={artisan.profile_image} size="h-14 w-14" text="text-lg" />
        <div>
          <p className="font-display text-lg font-bold text-brand-900">{artisan.name}</p>
          <p className="font-semibold text-accent-700">{artisan.category.name}</p>
        </div>
      </div>

      <form onSubmit={handleSubmit} className="mt-6 space-y-5">
        {error && <p role="alert" className="rounded-xl bg-accent-100 p-3 text-accent-700">{error}</p>}

        <div>
          <label htmlFor="title" className="label">What do you need done?</label>
          <input id="title" name="title" required minLength={3} maxLength={150} className="field" placeholder="e.g. Leaking kitchen sink" value={form.title} onChange={handleChange} />
        </div>
        <div>
          <label htmlFor="description" className="label">Describe the problem</label>
          <textarea id="description" name="description" required minLength={10} maxLength={3000} rows={6} className="field resize-y"
            placeholder="What is wrong, when did it start, and anything the artisan should know?" value={form.description} onChange={handleChange} />
        </div>
        <div className="grid gap-4 sm:grid-cols-2">
          <div>
            <label htmlFor="location" className="label">Where is the job?</label>
            <input id="location" name="location" required list="areas" className="field" placeholder="e.g. Madina, near the market" value={form.location} onChange={handleChange} />
            <datalist id="areas">{areaOptions.map((a) => <option key={a} value={a} />)}</datalist>
          </div>
          <div>
            <label htmlFor="preferred_date" className="label">Preferred date (optional)</label>
            <input id="preferred_date" name="preferred_date" type="date" min={today} className="field" value={form.preferred_date} onChange={handleChange} />
          </div>
        </div>

        <div>
          <p className="label">Photos of the problem (optional)</p>
          <input ref={fileInput} type="file" multiple accept="image/jpeg,image/png,image/webp" className="hidden" onChange={addFiles} />
          {files.length > 0 && (
            <ul className="mb-3 grid grid-cols-3 gap-3 sm:grid-cols-5">
              {previews.map((src, i) => (
                <li key={src} className="relative">
                  <img src={src} alt={`Selected photo ${i + 1}`} className="aspect-square w-full rounded-xl object-cover" />
                  <button type="button" aria-label={`Remove photo ${i + 1}`} onClick={() => setFiles(files.filter((_, j) => j !== i))}
                    className="absolute right-1 top-1 rounded-full bg-white p-1 shadow"><X size={14} /></button>
                </li>
              ))}
            </ul>
          )}
          {files.length < MAX_PHOTOS && (
            <button type="button" className="btn-outline" onClick={() => fileInput.current.click()}><ImagePlus size={18} aria-hidden="true" /> Add photos</button>
          )}
          <p className="mt-2 text-sm text-slate-500">Up to {MAX_PHOTOS} photos, JPG, PNG or WebP, {MAX_MB} MB each. Clear photos help the artisan give a better quote.</p>
        </div>

        <button type="submit" disabled={busy} className="btn-accent w-full py-3 text-lg">{busy ? "Sending request…" : "Send request"}</button>
      </form>
    </section>
  );
}
