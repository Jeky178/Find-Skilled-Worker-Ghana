import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { MapPin, Search, Wrench } from "lucide-react";
import useCategories from "../hooks/useCategories";
import CategoryIcon from "../components/CategoryIcon";
import FeaturedArtisans from "../components/FeaturedArtisans";
import { LOCATIONS } from "../constants";

const STEPS = [
  { title: "Search and compare", text: "Pick the trade and your area, then look through artisan profiles, prices and ratings." },
  { title: "Request the job", text: "Describe the problem, add photos, and send your request. You can also chat on WhatsApp." },
  { title: "Get it fixed and review", text: "Track the request until the work is done, then rate your artisan to help the next customer." },
];

export default function Home() {
  const navigate = useNavigate();
  const { categories, loading, error } = useCategories();
  const [category, setCategory] = useState("");
  const [location, setLocation] = useState("");

  const handleSearch = (e) => {
    e.preventDefault();
    const params = new URLSearchParams();
    if (category) params.set("category", category);
    if (location) params.set("location", location);
    navigate(`/artisans?${params.toString()}`);
  };

  return (
    <>
      {/* Hero */}
      <section className="bg-brand-900 pb-24 pt-14 text-white md:pt-20">
        <div className="mx-auto grid max-w-6xl gap-10 px-4 md:grid-cols-[1.5fr_1fr] md:items-center">
          <div>
            <h1 className="text-4xl font-extrabold leading-[1.08] text-white sm:text-5xl lg:text-6xl">
              Find Trusted Skilled Workers Near You.
            </h1>
            <p className="mt-5 max-w-xl text-lg text-brand-100">
              Connect with reliable plumbers, electricians, carpenters, mechanics and other professionals across Ghana.
            </p>
          </div>
          <div className="rounded-3xl border border-brand-700 bg-brand-800/60 p-5">
            <p className="flex items-center gap-2 font-display font-bold text-white">
              <MapPin size={18} className="text-accent-400" aria-hidden="true" /> We are starting in Accra
            </p>
            <div className="mt-3 flex flex-wrap gap-2">
              {LOCATIONS.slice(0, 7).map((l) => (
                <Link
                  key={l}
                  to={`/artisans?location=${encodeURIComponent(l)}`}
                  className="rounded-full bg-brand-700 px-3 py-1.5 text-sm font-semibold text-white transition-colors hover:bg-accent-600"
                >
                  {l}
                </Link>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* Search panel straddling the hero edge */}
      <div className="relative z-10 mx-auto -mt-12 max-w-5xl px-4">
        <form
          onSubmit={handleSearch}
          className="grid gap-3 rounded-3xl border border-slate-200 bg-white p-4 shadow-xl shadow-brand-900/10 md:grid-cols-[1fr_1fr_auto]"
          role="search"
          aria-label="Search for a skilled worker"
        >
          <div>
            <label htmlFor="category" className="label">What do you need?</label>
            <select id="category" className="field" value={category} onChange={(e) => setCategory(e.target.value)}>
              <option value="">Any profession</option>
              {categories.map((c) => <option key={c.id} value={c.slug}>{c.name}</option>)}
            </select>
          </div>
          <div>
            <label htmlFor="location" className="label">Where?</label>
            <select id="location" className="field" value={location} onChange={(e) => setLocation(e.target.value)}>
              <option value="">All areas</option>
              {LOCATIONS.map((l) => <option key={l} value={l}>{l}</option>)}
            </select>
          </div>
          <button type="submit" className="btn-accent self-end py-3 md:px-8">
            <Search size={18} aria-hidden="true" /> Search
          </button>
        </form>
      </div>

      {/* Categories */}
      <section className="mx-auto max-w-6xl px-4 py-16">
        <h2 className="text-3xl font-bold">Popular services</h2>
        <p className="mt-2 text-slate-600">Choose a trade to see the artisans who offer it.</p>

        {loading && (
          <div className="mt-8 grid grid-cols-2 gap-4 md:grid-cols-4" aria-busy="true">
            {Array.from({ length: 8 }).map((_, i) => <div key={i} className="h-32 animate-pulse rounded-2xl bg-slate-100" />)}
          </div>
        )}
        {error && (
          <p role="alert" className="mt-8 rounded-2xl bg-accent-100 p-4 text-accent-700">
            {error} Make sure the backend is running at the address set in <code>VITE_API_URL</code>.
          </p>
        )}
        {!loading && !error && categories.length === 0 && (
          <p className="mt-8 text-slate-600">No categories yet. Run <code>python seed.py</code> in the backend folder.</p>
        )}
        {categories.length > 0 && (
          <div className="mt-8 grid grid-cols-2 gap-4 md:grid-cols-4">
            {categories.map((c) => (
              <Link
                key={c.id}
                to={`/artisans?category=${c.slug}`}
                className="group rounded-2xl border border-slate-200 p-5 transition-colors hover:border-brand-600 hover:bg-brand-50"
              >
                <span className="grid h-11 w-11 place-items-center rounded-xl bg-brand-50 text-brand-800 group-hover:bg-white">
                  <CategoryIcon name={c.icon} size={22} />
                </span>
                <span className="mt-4 block font-display text-lg font-bold text-brand-900">{c.name}</span>
                {c.description && <span className="mt-1 block text-sm text-slate-600">{c.description}</span>}
              </Link>
            ))}
          </div>
        )}
      </section>

      <FeaturedArtisans />

      {/* How it works */}
      <section className="bg-brand-50 py-16">
        <div className="mx-auto max-w-6xl px-4">
          <h2 className="text-3xl font-bold">How it works</h2>
          <ol className="mt-8 grid gap-6 md:grid-cols-3">
            {STEPS.map((s, i) => (
              <li key={s.title} className="rounded-2xl bg-white p-6">
                <span className="grid h-9 w-9 place-items-center rounded-full bg-brand-900 font-display font-bold text-white">{i + 1}</span>
                <h3 className="mt-4 text-xl font-bold">{s.title}</h3>
                <p className="mt-2 text-slate-600">{s.text}</p>
              </li>
            ))}
          </ol>
        </div>
      </section>

      {/* Artisan call to action */}
      <section className="mx-auto max-w-6xl px-4 py-16">
        <div className="flex flex-col items-start justify-between gap-6 rounded-3xl bg-accent-100 p-8 md:flex-row md:items-center md:p-12">
          <div>
            <h2 className="flex items-center gap-3 text-3xl font-bold"><Wrench aria-hidden="true" className="text-accent-600" /> Are you a skilled worker?</h2>
            <p className="mt-2 max-w-xl text-slate-700">Create a free profile, show photos of your work and let customers in your area find you.</p>
          </div>
          <Link to="/register?role=artisan" className="btn-accent shrink-0 px-8 py-3">Create your free profile</Link>
        </div>
      </section>
    </>
  );
}
