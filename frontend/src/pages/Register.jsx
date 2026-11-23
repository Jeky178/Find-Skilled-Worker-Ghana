import { useState } from "react";
import { Link, Navigate, useNavigate, useSearchParams } from "react-router-dom";
import { Hammer, User } from "lucide-react";
import { useAuth } from "../context/AuthContext";
import useCategories from "../hooks/useCategories";
import { getErrorMessage } from "../services/api";
import PasswordInput from "../components/PasswordInput";
import { LOCATIONS, REGION_LOCATIONS } from "../constants";

export default function Register() {
  const { user, register } = useAuth();
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const { categories } = useCategories();
  const [form, setForm] = useState({
    role: params.get("role") === "artisan" ? "artisan" : "customer",
    full_name: "", email: "", phone: "", password: "", category_id: "", location: "",
  });
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  if (user) return <Navigate to="/dashboard" replace />;

  const set = (name, value) => setForm((f) => ({ ...f, [name]: value }));
  const handleChange = (e) => set(e.target.name, e.target.value);
  const isArtisan = form.role === "artisan";

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    if (form.password.length < 8 || !/[A-Za-z]/.test(form.password) || !/\d/.test(form.password)) {
      setError("Password must be at least 8 characters and include a letter and a number.");
      return;
    }
    const payload = {
      role: form.role,
      full_name: form.full_name,
      email: form.email.trim(),
      password: form.password,
      phone: form.phone.trim() || null,
    };
    if (isArtisan) {
      payload.category_id = Number(form.category_id);
      payload.location = form.location || null;
    }
    setBusy(true);
    try {
      await register(payload);
      navigate("/dashboard", { replace: true });
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setBusy(false);
    }
  };

  const roleButton = (value, label, hint, Icon) => (
    <button
      type="button"
      onClick={() => set("role", value)}
      aria-pressed={form.role === value}
      className={`rounded-2xl border p-4 text-left transition-colors ${form.role === value ? "border-brand-700 bg-brand-50" : "border-slate-300 hover:border-brand-600"}`}
    >
      <Icon size={20} className="text-brand-800" aria-hidden="true" />
      <span className="mt-2 block font-display font-bold text-brand-900">{label}</span>
      <span className="block text-sm text-slate-600">{hint}</span>
    </button>
  );

  return (
    <section className="mx-auto max-w-lg px-4 py-14">
      <h1 className="text-3xl font-bold">Create your account</h1>
      <p className="mt-2 text-slate-600">It takes a minute and it is free.</p>

      <form onSubmit={handleSubmit} className="mt-8 space-y-4" noValidate>
        {error && <p role="alert" className="rounded-xl bg-accent-100 p-3 text-accent-700">{error}</p>}

        <div className="grid grid-cols-2 gap-3">
          {roleButton("customer", "I need a worker", "Find and hire artisans", User)}
          {roleButton("artisan", "I am a worker", "Get customers", Hammer)}
        </div>

        <div>
          <label htmlFor="full_name" className="label">Full name</label>
          <input id="full_name" name="full_name" autoComplete="name" required minLength={2} className="field" value={form.full_name} onChange={handleChange} />
        </div>
        <div>
          <label htmlFor="email" className="label">Email</label>
          <input id="email" name="email" type="email" autoComplete="email" required className="field" value={form.email} onChange={handleChange} />
        </div>
        <div>
          <label htmlFor="phone" className="label">Phone number {isArtisan ? "(customers will use it for WhatsApp)" : "(optional)"}</label>
          <input id="phone" name="phone" type="tel" autoComplete="tel" placeholder="024 123 4567" className="field" value={form.phone} onChange={handleChange} />
        </div>

        {isArtisan && (
          <>
            <div>
              <label htmlFor="category_id" className="label">Your occupation</label>
              <select id="category_id" name="category_id" required className="field" value={form.category_id} onChange={handleChange}>
                <option value="">Choose your trade</option>
                {categories.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
              </select>
            </div>
            <div>
              <label htmlFor="location" className="label">Main area you work in</label>
              <select id="location" name="location" className="field" value={form.location} onChange={handleChange}>
                <option value="">Choose an area</option>
                {Object.entries(REGION_LOCATIONS).map(([region, places]) => <optgroup key={region} label={region}>{places.map((l) => <option key={`${region}-${l}`} value={l}>{l}</option>)}</optgroup>)}
              </select>
            </div>
          </>
        )}

        <div>
          <label htmlFor="password" className="label">Password</label>
          <PasswordInput id="password" name="password" autoComplete="new-password" required minLength={8} value={form.password} onChange={handleChange} aria-describedby="pw-hint" />
          <p id="pw-hint" className="mt-1 text-sm text-slate-500">At least 8 characters, with a letter and a number.</p>
        </div>

        <button type="submit" disabled={busy || (isArtisan && !form.category_id)} className="btn-accent w-full py-3">
          {busy ? "Creating account…" : "Create account"}
        </button>
      </form>

      <p className="mt-6 text-center text-slate-600">
        Already registered? <Link to="/login" className="font-semibold text-brand-700 underline">Log in</Link>
      </p>
    </section>
  );
}
