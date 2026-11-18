import { useState } from "react";
import { Link, Navigate, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import api, { getErrorMessage } from "../services/api";
import PasswordInput from "../components/PasswordInput";
import useServerStatus from "../hooks/useServerStatus";

export default function Login() {
  const { user, login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [form, setForm] = useState({ email: "", password: "" });
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const { status, recheck } = useServerStatus();

  if (user) return <Navigate to="/dashboard" replace />;

  const handleChange = (e) => setForm({ ...form, [e.target.name]: e.target.value });

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    setBusy(true);
    try {
      await login(form.email.trim(), form.password);
      navigate(location.state?.from || "/dashboard", { replace: true });
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setBusy(false);
    }
  };

  return (
    <section className="mx-auto max-w-md px-4 py-14">
      <h1 className="text-3xl font-bold">Log in</h1>
      <p className="mt-2 text-slate-600">Welcome back. Enter your details to continue.</p>

      {status === "offline" && (
        <div role="alert" className="mt-6 rounded-xl border border-accent-400 bg-accent-100 p-4 text-accent-700">
          <p className="font-semibold">The server is not reachable.</p>
          <p className="mt-1 text-sm">Start the backend (in the backend folder run <code>uvicorn main:app --reload</code>) and check that this address is correct: <code>{api.defaults.baseURL}</code></p>
          <button type="button" onClick={recheck} className="mt-2 text-sm font-semibold underline">Check again</button>
        </div>
      )}

      <form onSubmit={handleSubmit} className="mt-8 space-y-4" noValidate>
        {error && <p role="alert" className="rounded-xl bg-accent-100 p-3 text-accent-700">{error}</p>}
        <div>
          <label htmlFor="email" className="label">Email</label>
          <input id="email" name="email" type="email" autoComplete="email" required className="field" value={form.email} onChange={handleChange} />
        </div>
        <div>
          <label htmlFor="password" className="label">Password</label>
          <PasswordInput id="password" name="password" autoComplete="current-password" required value={form.password} onChange={handleChange} />
        </div>
        <button type="submit" disabled={busy || !form.email || !form.password} className="btn-primary w-full py-3">
          {busy ? "Logging in…" : "Log in"}
        </button>
      </form>

      <p className="mt-6 text-center text-slate-600">
        New here? <Link to="/register" className="font-semibold text-brand-700 underline">Create an account</Link>
      </p>
    </section>
  );
}
