import { useState } from "react";
import { Link } from "react-router-dom";
import { CheckCircle2, ChevronDown, Hammer, Mail, MapPin, MessageCircle, Phone, Search, ShieldAlert } from "lucide-react";
import { useAuth } from "../context/AuthContext";
import api, { getErrorMessage } from "../services/api";
import { CONTACT, CONTACT_TOPICS, LOCATIONS } from "../constants";

const WHO = [
  { Icon: Search, title: "Looking for a worker", text: "Questions about finding, comparing or requesting a skilled worker." },
  { Icon: Hammer, title: "Artisans and businesses", text: "Help creating your profile, listing your services or joining the platform." },
  { Icon: ShieldAlert, title: "Reporting a problem", text: "Tell us about a suspicious profile, a bad experience or anything that feels wrong." },
];

const FAQ = [
  { q: "Is it free to use?", a: "Searching for artisans and creating an account is free. Artisans can start with a free profile, and optional premium plans are planned for later." },
  { q: "Which areas do you cover?", a: "We are starting in Accra, including Madina, Adenta, Dome, East Legon, Haatso, Achimota and Kasoa, and plan to expand across Ghana." },
  { q: "I am an artisan. How do I join?", a: "Create an account and choose “I am a worker”. You will pick your trade and your main area, and your profile is created straight away." },
  { q: "How do I report a problem with an artisan?", a: "Use the form on this page and choose “Report a problem” as the topic. Include the artisan’s name and what happened so we can look into it." },
];

export default function Contact() {
  const { user } = useAuth();
  const [form, setForm] = useState({
    name: user?.full_name || "", email: user?.email || "", phone: "", topic: CONTACT_TOPICS[0], message: "",
  });
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [sent, setSent] = useState(false);

  const handleChange = (e) => setForm({ ...form, [e.target.name]: e.target.value });

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    setBusy(true);
    try {
      await api.post("/api/contact", { ...form, phone: form.phone.trim() || null });
      setSent(true);
      setForm((f) => ({ ...f, phone: "", message: "" }));
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setBusy(false);
    }
  };

  const waLink = CONTACT.whatsapp ? `https://wa.me/${CONTACT.whatsapp.replace(/\D/g, "")}` : "";
  const direct = [
    CONTACT.email && { Icon: Mail, label: "Email", value: CONTACT.email, href: `mailto:${CONTACT.email}` },
    CONTACT.phone && { Icon: Phone, label: "Call", value: CONTACT.phone, href: `tel:${CONTACT.phone.replace(/\s/g, "")}` },
    waLink && { Icon: MessageCircle, label: "WhatsApp", value: "Start a chat", href: waLink },
  ].filter(Boolean);

  return (
    <>
      <section className="bg-brand-50">
        <div className="mx-auto max-w-6xl px-4 py-14">
          <h1 className="text-4xl font-extrabold">Get in touch</h1>
          <p className="mt-3 max-w-2xl text-lg text-slate-700">
            Need a worker, want to join as an artisan, or have a problem to report? Send us a message and we will read it.
          </p>
        </div>
      </section>

      <section className="mx-auto grid max-w-6xl gap-10 px-4 py-12 lg:grid-cols-[1fr_1.15fr]">
        {/* Left: information */}
        <div className="space-y-8">
          {direct.length > 0 && (
            <ul className="space-y-3">
              {direct.map(({ Icon, label, value, href }) => (
                <li key={label}>
                  <a href={href} target={label === "WhatsApp" ? "_blank" : undefined} rel="noreferrer"
                     className="flex items-center gap-4 rounded-2xl border border-slate-200 p-4 transition-colors hover:border-brand-600 hover:bg-brand-50">
                    <span className="grid h-11 w-11 place-items-center rounded-xl bg-brand-900 text-white"><Icon size={20} aria-hidden="true" /></span>
                    <span><span className="block text-sm text-slate-600">{label}</span><span className="font-semibold text-brand-900">{value}</span></span>
                  </a>
                </li>
              ))}
            </ul>
          )}

          <div>
            <h2 className="text-xl font-bold">What can we help with?</h2>
            <ul className="mt-4 space-y-4">
              {WHO.map(({ Icon, title, text }) => (
                <li key={title} className="flex gap-4">
                  <span className="mt-0.5 grid h-10 w-10 shrink-0 place-items-center rounded-xl bg-accent-100 text-accent-700"><Icon size={20} aria-hidden="true" /></span>
                  <span><span className="block font-display font-bold text-brand-900">{title}</span><span className="text-slate-600">{text}</span></span>
                </li>
              ))}
            </ul>
          </div>

          <div className="rounded-2xl bg-brand-900 p-6 text-brand-100">
            <p className="flex items-center gap-2 font-display text-lg font-bold text-white">
              <MapPin size={18} className="text-accent-400" aria-hidden="true" /> Where we work
            </p>
            <p className="mt-2">We are starting in Accra, Ghana, and growing from here.</p>
            <div className="mt-3 flex flex-wrap gap-2">
              {LOCATIONS.slice(0, 7).map((l) => <span key={l} className="rounded-full bg-brand-700 px-3 py-1 text-sm font-semibold text-white">{l}</span>)}
            </div>
          </div>
        </div>

        {/* Right: form */}
        <div className="rounded-3xl border border-slate-200 p-6 shadow-lg shadow-brand-900/5 md:p-8">
          {sent ? (
            <div className="py-10 text-center" role="status">
              <CheckCircle2 size={48} className="mx-auto text-green-600" aria-hidden="true" />
              <h2 className="mt-4 text-2xl font-bold">Message sent</h2>
              <p className="mx-auto mt-2 max-w-sm text-slate-600">Thank you for reaching out. We have received your message and will reply to {form.email}.</p>
              <button onClick={() => setSent(false)} className="btn-outline mt-6">Send another message</button>
            </div>
          ) : (
            <form onSubmit={handleSubmit} className="space-y-4">
              <h2 className="text-2xl font-bold">Send us a message</h2>
              {error && <p role="alert" className="rounded-xl bg-accent-100 p-3 text-accent-700">{error}</p>}
              <div className="grid gap-4 sm:grid-cols-2">
                <div>
                  <label htmlFor="name" className="label">Your name</label>
                  <input id="name" name="name" required minLength={2} autoComplete="name" className="field" value={form.name} onChange={handleChange} />
                </div>
                <div>
                  <label htmlFor="email" className="label">Email</label>
                  <input id="email" name="email" type="email" required autoComplete="email" className="field" value={form.email} onChange={handleChange} />
                </div>
              </div>
              <div className="grid gap-4 sm:grid-cols-2">
                <div>
                  <label htmlFor="phone" className="label">Phone (optional)</label>
                  <input id="phone" name="phone" type="tel" autoComplete="tel" placeholder="024 123 4567" className="field" value={form.phone} onChange={handleChange} />
                </div>
                <div>
                  <label htmlFor="topic" className="label">Topic</label>
                  <select id="topic" name="topic" className="field" value={form.topic} onChange={handleChange}>
                    {CONTACT_TOPICS.map((t) => <option key={t}>{t}</option>)}
                  </select>
                </div>
              </div>
              <div>
                <label htmlFor="message" className="label">Message</label>
                <textarea id="message" name="message" required minLength={10} maxLength={3000} rows={6} className="field resize-y"
                          placeholder="Tell us how we can help…" value={form.message} onChange={handleChange} />
              </div>
              <button type="submit" disabled={busy} className="btn-accent w-full py-3">{busy ? "Sending…" : "Send message"}</button>
            </form>
          )}
        </div>
      </section>

      {/* FAQ */}
      <section className="bg-brand-50 py-14">
        <div className="mx-auto max-w-3xl px-4">
          <h2 className="text-3xl font-bold">Common questions</h2>
          <div className="mt-6 space-y-3">
            {FAQ.map(({ q, a }) => (
              <details key={q} className="group rounded-2xl bg-white p-5">
                <summary className="flex cursor-pointer list-none items-center justify-between gap-4 font-display font-bold text-brand-900">
                  {q}
                  <ChevronDown size={20} className="shrink-0 transition-transform group-open:rotate-180" aria-hidden="true" />
                </summary>
                <p className="mt-3 text-slate-700">{a}</p>
              </details>
            ))}
          </div>
          <p className="mt-6 text-slate-600">Ready to start? <Link to="/register" className="font-semibold text-brand-700 underline">Create a free account</Link>.</p>
        </div>
      </section>
    </>
  );
}
