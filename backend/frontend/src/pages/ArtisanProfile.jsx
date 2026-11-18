import { useCallback, useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { CheckCircle2, ImagePlus, Trash2, Upload } from "lucide-react";
import api, { getErrorMessage, mediaUrl } from "../services/api";
import useCategories from "../hooks/useCategories";
import Avatar from "../components/Avatar";
import { LOCATIONS } from "../constants";

const toForm = (p) => ({
  category_id: String(p.category_id), headline: p.headline || "", bio: p.bio || "",
  years_experience: String(p.years_experience ?? 0), phone: p.phone ? `+${p.phone}` : "",
  whatsapp_number: p.whatsapp_number ? `+${p.whatsapp_number}` : "", price_min: p.price_min ?? "",
  price_max: p.price_max ?? "", price_note: p.price_note || "", is_available: p.is_available, locations: p.locations,
});

const numOrNull = (v) => (v === "" || v === null ? null : Number(v));

export default function ArtisanProfile() {
  const { categories } = useCategories();
  const [profile, setProfile] = useState(null);
  const [form, setForm] = useState(null);
  const [loadError, setLoadError] = useState("");
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState({ type: "", text: "" });
  const [customArea, setCustomArea] = useState("");
  const [caption, setCaption] = useState("");
  const [busy, setBusy] = useState("");
  const photoInput = useRef(null);
  const portfolioInput = useRef(null);

  const load = useCallback(() => {
    api.get("/api/artisan/me")
      .then((res) => { setProfile(res.data); setForm(toForm(res.data)); })
      .catch((e) => setLoadError(getErrorMessage(e)));
  }, []);
  useEffect(() => { load(); }, [load]);

  const flash = (type, text) => setMessage({ type, text });
  const set = (name, value) => setForm((f) => ({ ...f, [name]: value }));
  const handleChange = (e) => set(e.target.name, e.target.value);
  const toggleArea = (area) =>
    set("locations", form.locations.includes(area) ? form.locations.filter((a) => a !== area) : [...form.locations, area]);

  const addCustomArea = () => {
    const name = customArea.trim();
    if (name.length < 2) return;
    const titled = name.replace(/\s+/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
    if (!form.locations.some((l) => l.toLowerCase() === titled.toLowerCase())) set("locations", [...form.locations, titled]);
    setCustomArea("");
  };

  const handleSave = async (e) => {
    e.preventDefault();
    setSaving(true);
    flash("", "");
    try {
      const res = await api.patch("/api/artisan/me", {
        category_id: Number(form.category_id), headline: form.headline, bio: form.bio,
        years_experience: Number(form.years_experience) || 0, phone: form.phone, whatsapp_number: form.whatsapp_number,
        price_min: numOrNull(form.price_min), price_max: numOrNull(form.price_max), price_note: form.price_note,
        is_available: form.is_available, locations: form.locations,
      });
      setProfile(res.data); setForm(toForm(res.data));
      flash("ok", "Your profile has been saved.");
      window.scrollTo({ top: 0, behavior: "smooth" });
    } catch (err) {
      flash("error", getErrorMessage(err));
    } finally {
      setSaving(false);
    }
  };

  const uploadPhoto = async (e) => {
    const file = e.target.files?.[0];
    e.target.value = "";
    if (!file) return;
    setBusy("photo"); flash("", "");
    try {
      const fd = new FormData(); fd.append("file", file);
      const res = await api.post("/api/artisan/me/photo", fd);
      setProfile(res.data); flash("ok", "Profile photo updated.");
    } catch (err) { flash("error", getErrorMessage(err)); } finally { setBusy(""); }
  };

  const removePhoto = async () => {
    setBusy("photo");
    try { setProfile((await api.delete("/api/artisan/me/photo")).data); flash("ok", "Profile photo removed."); }
    catch (err) { flash("error", getErrorMessage(err)); } finally { setBusy(""); }
  };

  const addPortfolio = async (e) => {
    const file = e.target.files?.[0];
    e.target.value = "";
    if (!file) return;
    setBusy("portfolio"); flash("", "");
    try {
      const fd = new FormData(); fd.append("file", file); if (caption.trim()) fd.append("caption", caption.trim());
      await api.post("/api/artisan/me/portfolio", fd);
      setCaption(""); flash("ok", "Photo added to your portfolio."); load();
    } catch (err) { flash("error", getErrorMessage(err)); } finally { setBusy(""); }
  };

  const removePortfolio = async (id) => {
    if (!window.confirm("Remove this photo from your portfolio?")) return;
    setBusy("portfolio");
    try { await api.delete(`/api/artisan/me/portfolio/${id}`); flash("ok", "Photo removed."); load(); }
    catch (err) { flash("error", getErrorMessage(err)); } finally { setBusy(""); }
  };

  if (loadError) return <p role="alert" className="mx-auto my-16 max-w-xl rounded-2xl bg-accent-100 p-4 text-accent-700">{loadError}</p>;
  if (!profile || !form) return <p className="p-16 text-center text-slate-500">Loading your profile…</p>;

  const allAreas = [...new Set([...LOCATIONS, ...form.locations])];
  const atLimit = profile.portfolio.length >= profile.portfolio_limit;
  const section = "rounded-3xl border border-slate-200 p-6";

  return (
    <section className="mx-auto max-w-3xl px-4 py-10">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <h1 className="text-3xl font-bold">My professional profile</h1>
        <Link to={`/artisans/${profile.id}`} className="btn-outline">View public profile</Link>
      </div>

      <div className="mt-6 rounded-3xl bg-brand-50 p-6">
        <div className="flex items-center justify-between">
          <p className="font-display font-bold text-brand-900">Profile {profile.completeness}% complete</p>
          {profile.completeness === 100 && <CheckCircle2 className="text-green-600" aria-hidden="true" />}
        </div>
        <div className="mt-2 h-3 overflow-hidden rounded-full bg-white" role="progressbar" aria-valuenow={profile.completeness} aria-valuemin={0} aria-valuemax={100}>
          <div className="h-full rounded-full bg-accent-500 transition-all" style={{ width: `${profile.completeness}%` }} />
        </div>
        {profile.missing.length > 0
          ? <ul className="mt-3 list-disc space-y-0.5 pl-5 text-slate-700">{profile.missing.map((m) => <li key={m}>{m}</li>)}</ul>
          : <p className="mt-3 text-slate-700">Great work. Customers can see everything they need.</p>}
      </div>

      {message.text && (
        <p role={message.type === "error" ? "alert" : "status"} className={`mt-6 rounded-xl p-3 ${message.type === "error" ? "bg-accent-100 text-accent-700" : "bg-green-50 text-green-800"}`}>
          {message.text}
        </p>
      )}

      {/* Photo */}
      <div className={`${section} mt-6 flex flex-wrap items-center gap-5`}>
        <Avatar name={profile.name} src={profile.profile_image} size="h-24 w-24" text="text-3xl" />
        <div>
          <h2 className="text-xl font-bold">Profile photo</h2>
          <p className="text-sm text-slate-600">A clear photo of your face builds trust. JPG, PNG or WebP, up to 5 MB.</p>
          <div className="mt-3 flex gap-2">
            <input ref={photoInput} type="file" accept="image/jpeg,image/png,image/webp" className="hidden" onChange={uploadPhoto} />
            <button type="button" className="btn-primary" disabled={busy === "photo"} onClick={() => photoInput.current.click()}>
              <Upload size={18} aria-hidden="true" /> {busy === "photo" ? "Uploading…" : profile.profile_image ? "Change photo" : "Upload photo"}
            </button>
            {profile.profile_image && <button type="button" className="btn-outline" disabled={busy === "photo"} onClick={removePhoto}>Remove</button>}
          </div>
        </div>
      </div>

      <form onSubmit={handleSave} className="mt-6 space-y-6">
        <div className={`${section} space-y-4`}>
          <h2 className="text-xl font-bold">About you</h2>
          <div>
            <label htmlFor="category_id" className="label">Your occupation</label>
            <select id="category_id" name="category_id" className="field" value={form.category_id} onChange={handleChange}>
              {categories.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
            </select>
          </div>
          <div>
            <label htmlFor="headline" className="label">Headline</label>
            <input id="headline" name="headline" maxLength={150} className="field" placeholder="e.g. Reliable plumber for leaks and new installations" value={form.headline} onChange={handleChange} />
          </div>
          <div>
            <label htmlFor="bio" className="label">Describe your experience</label>
            <textarea id="bio" name="bio" rows={6} maxLength={2000} className="field resize-y" placeholder="What work do you do, what are you best at, and what can customers expect?" value={form.bio} onChange={handleChange} />
            <p className="mt-1 text-sm text-slate-500">{form.bio.length}/2000</p>
          </div>
          <div className="max-w-[12rem]">
            <label htmlFor="years_experience" className="label">Years of experience</label>
            <input id="years_experience" name="years_experience" type="number" min={0} max={60} className="field" value={form.years_experience} onChange={handleChange} />
          </div>
        </div>

        <div className={`${section} space-y-4`}>
          <h2 className="text-xl font-bold">Contact numbers</h2>
          <div className="grid gap-4 sm:grid-cols-2">
            <div>
              <label htmlFor="whatsapp_number" className="label">WhatsApp number</label>
              <input id="whatsapp_number" name="whatsapp_number" type="tel" placeholder="024 123 4567" className="field" value={form.whatsapp_number} onChange={handleChange} />
            </div>
            <div>
              <label htmlFor="phone" className="label">Phone number</label>
              <input id="phone" name="phone" type="tel" placeholder="024 123 4567" className="field" value={form.phone} onChange={handleChange} />
            </div>
          </div>
        </div>

        <div className={`${section} space-y-4`}>
          <h2 className="text-xl font-bold">Prices (GH₵)</h2>
          <div className="grid gap-4 sm:grid-cols-2">
            <div>
              <label htmlFor="price_min" className="label">From</label>
              <input id="price_min" name="price_min" type="number" min={0} step="1" className="field" value={form.price_min} onChange={handleChange} />
            </div>
            <div>
              <label htmlFor="price_max" className="label">To</label>
              <input id="price_max" name="price_max" type="number" min={0} step="1" className="field" value={form.price_max} onChange={handleChange} />
            </div>
          </div>
          <div>
            <label htmlFor="price_note" className="label">Price note (optional)</label>
            <input id="price_note" name="price_note" maxLength={200} className="field" placeholder="e.g. Per visit. Final quote after inspection" value={form.price_note} onChange={handleChange} />
          </div>
        </div>

        <div className={`${section} space-y-4`}>
          <h2 className="text-xl font-bold">Where you work</h2>
          <div className="flex flex-wrap gap-2" role="group" aria-label="Service areas">
            {allAreas.map((a) => (
              <button type="button" key={a} onClick={() => toggleArea(a)} aria-pressed={form.locations.includes(a)}
                className={`rounded-full border px-3 py-1.5 font-semibold transition-colors ${form.locations.includes(a) ? "border-brand-800 bg-brand-800 text-white" : "border-slate-300 text-slate-700 hover:border-brand-600"}`}>
                {a}
              </button>
            ))}
          </div>
          <div className="flex gap-2">
            <label htmlFor="custom-area" className="sr-only">Add another area</label>
            <input id="custom-area" className="field" placeholder="Add another area" value={customArea} onChange={(e) => setCustomArea(e.target.value)}
              onKeyDown={(e) => { if (e.key === "Enter") { e.preventDefault(); addCustomArea(); } }} />
            <button type="button" className="btn-outline shrink-0" onClick={addCustomArea}>Add area</button>
          </div>
        </div>

        <div className={`${section}`}>
          <label className="flex items-start gap-3">
            <input type="checkbox" className="mt-1 h-5 w-5 accent-brand-800" checked={form.is_available} onChange={(e) => set("is_available", e.target.checked)} />
            <span>
              <span className="block font-display text-lg font-bold text-brand-900">I am available for new jobs</span>
              <span className="text-sm text-slate-600">Turn this off when you are fully booked. Customers will see that you are unavailable.</span>
            </span>
          </label>
        </div>

        <button type="submit" disabled={saving} className="btn-accent w-full py-3 text-lg">{saving ? "Saving…" : "Save profile"}</button>
      </form>

      {/* Portfolio */}
      <div className={`${section} mt-6`}>
        <div className="flex flex-wrap items-end justify-between gap-2">
          <h2 className="text-xl font-bold">Photos of your work</h2>
          <p className="text-sm text-slate-600">{profile.portfolio.length} of {profile.portfolio_limit} photos used ({profile.plan} plan)</p>
        </div>

        <div className="mt-4 flex flex-wrap items-end gap-3">
          <div className="min-w-[14rem] flex-1">
            <label htmlFor="caption" className="label">Caption (optional)</label>
            <input id="caption" maxLength={200} className="field" placeholder="e.g. Kitchen sink replacement" value={caption} onChange={(e) => setCaption(e.target.value)} />
          </div>
          <input ref={portfolioInput} type="file" accept="image/jpeg,image/png,image/webp" className="hidden" onChange={addPortfolio} />
          <button type="button" className="btn-primary" disabled={busy === "portfolio" || atLimit} onClick={() => portfolioInput.current.click()}>
            <ImagePlus size={18} aria-hidden="true" /> {busy === "portfolio" ? "Uploading…" : "Add photo"}
          </button>
        </div>
        {atLimit && <p className="mt-3 rounded-xl bg-accent-100 p-3 text-sm text-accent-700">You have reached the {profile.plan} plan limit. Remove a photo to add another{profile.plan === "free" ? <>, or <Link to="/dashboard/billing" className="font-semibold underline">upgrade to Premium</Link> for more space.</> : "."}</p>}

        {profile.portfolio.length === 0 ? (
          <p className="mt-4 text-slate-500">No photos yet. Profiles with photos of finished work get more enquiries.</p>
        ) : (
          <ul className="mt-5 grid grid-cols-2 gap-3 sm:grid-cols-3">
            {profile.portfolio.map((p) => (
              <li key={p.id} className="relative">
                <img src={mediaUrl(p.image_url)} alt={p.caption || "Completed work"} loading="lazy" className="aspect-square w-full rounded-2xl object-cover" />
                <button onClick={() => removePortfolio(p.id)} aria-label={`Remove photo${p.caption ? `: ${p.caption}` : ""}`}
                  className="absolute right-2 top-2 rounded-full bg-white p-2 text-accent-700 shadow hover:bg-accent-100"><Trash2 size={16} /></button>
                {p.caption && <p className="mt-1 text-sm text-slate-600">{p.caption}</p>}
              </li>
            ))}
          </ul>
        )}
      </div>
    </section>
  );
}
