import { useCallback, useEffect, useState } from "react";
import api, { getErrorMessage } from "../../services/api";
import CategoryIcon from "../../components/CategoryIcon";

const ICONS = ["wrench", "zap", "hammer", "paintbrush", "car", "snowflake", "refrigerator", "layout-grid", "flame", "home", "sparkles", "settings"];

function Row({ c, onSaved }) {
  const [edit, setEdit] = useState(false);
  const [form, setForm] = useState({ name: c.name, description: c.description || "", icon: c.icon || "wrench" });
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const patch = async (body) => {
    setBusy(true); setError("");
    try { onSaved((await api.patch(`/api/admin/categories/${c.id}`, body)).data); setEdit(false); } catch (e) { setError(getErrorMessage(e)); } finally { setBusy(false); }
  };

  return (
    <li className={`rounded-2xl border p-4 ${c.is_active ? "border-slate-200" : "border-dashed border-slate-300 bg-slate-50"}`}>
      {edit ? (
        <form className="grid gap-3 md:grid-cols-[1fr_1.5fr_auto_auto]" onSubmit={(e) => { e.preventDefault(); patch(form); }}>
          <input aria-label="Name" required minLength={2} className="field" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
          <input aria-label="Description" className="field" value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} />
          <select aria-label="Icon" className="field" value={form.icon} onChange={(e) => setForm({ ...form, icon: e.target.value })}>{ICONS.map((i) => <option key={i}>{i}</option>)}</select>
          <div className="flex gap-2"><button className="btn-primary" disabled={busy}>Save</button><button type="button" className="btn-outline" onClick={() => setEdit(false)}>Cancel</button></div>
        </form>
      ) : (
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            <span className="grid h-10 w-10 place-items-center rounded-xl bg-brand-50 text-brand-800"><CategoryIcon name={c.icon} size={20} /></span>
            <div>
              <p className="font-display font-bold text-brand-900">{c.name}{!c.is_active && <span className="ml-2 rounded-full bg-slate-200 px-2 py-0.5 text-xs font-bold text-slate-700">Hidden</span>}</p>
              <p className="text-sm text-slate-600">{c.description || "No description"} · {c.artisan_count} {c.artisan_count === 1 ? "artisan" : "artisans"}</p>
            </div>
          </div>
          <div className="flex gap-2">
            <button className="btn-outline" onClick={() => setEdit(true)}>Edit</button>
            <button className="btn-outline" disabled={busy} onClick={() => patch({ is_active: !c.is_active })}>{c.is_active ? "Hide" : "Show"}</button>
          </div>
        </div>
      )}
      {error && <p role="alert" className="mt-2 text-sm text-accent-700">{error}</p>}
    </li>
  );
}

export default function Categories() {
  const [items, setItems] = useState(null);
  const [error, setError] = useState("");
  const [form, setForm] = useState({ name: "", description: "", icon: "wrench" });
  const [busy, setBusy] = useState(false);

  const load = useCallback(() => { api.get("/api/admin/categories").then((r) => setItems(r.data)).catch((e) => setError(getErrorMessage(e))); }, []);
  useEffect(() => { load(); }, [load]);

  const add = async (e) => {
    e.preventDefault(); setBusy(true); setError("");
    try { await api.post("/api/admin/categories", form); setForm({ name: "", description: "", icon: "wrench" }); load(); } catch (err) { setError(getErrorMessage(err)); } finally { setBusy(false); }
  };

  return (
    <div>
      <h2 className="text-2xl font-bold">Service categories</h2>
      <p className="mt-1 text-slate-600">Hiding a category removes it from search, the homepage and registration. Existing profiles are kept.</p>
      <form onSubmit={add} className="mt-4 grid gap-3 rounded-2xl bg-brand-50 p-4 md:grid-cols-[1fr_1.5fr_auto_auto]">
        <input aria-label="New category name" required minLength={2} placeholder="New category, e.g. Roofer" className="field" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
        <input aria-label="Description" placeholder="Short description" className="field" value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} />
        <select aria-label="Icon" className="field" value={form.icon} onChange={(e) => setForm({ ...form, icon: e.target.value })}>{ICONS.map((i) => <option key={i}>{i}</option>)}</select>
        <button className="btn-accent" disabled={busy}>Add category</button>
      </form>
      {error && <p role="alert" className="mt-4 rounded-xl bg-accent-100 p-3 text-accent-700">{error}</p>}
      <ul className="mt-4 space-y-2">{items?.map((c) => <Row key={`${c.id}-${c.name}-${c.is_active}`} c={c} onSaved={(n) => setItems((xs) => xs.map((x) => (x.id === n.id ? n : x)))} />)}</ul>
    </div>
  );
}
