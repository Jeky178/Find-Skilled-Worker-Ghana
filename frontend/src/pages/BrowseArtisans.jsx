import { useEffect, useMemo, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { Search, SearchX } from "lucide-react";
import api, { getErrorMessage } from "../services/api";
import useCategories from "../hooks/useCategories";
import ArtisanCard from "../components/ArtisanCard";
import { LOCATIONS } from "../constants";

const SORTS = [
  ["recommended", "Recommended"], ["rating", "Highest rated"], ["experience", "Most experienced"],
  ["price_low", "Lowest price"], ["newest", "Newest"],
];

export default function BrowseArtisans() {
  const [params, setParams] = useSearchParams();
  const { categories } = useCategories();
  const [areas, setAreas] = useState(LOCATIONS);
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [qInput, setQInput] = useState(params.get("q") || "");

  const f = {
    q: params.get("q") || "", category: params.get("category") || "", location: params.get("location") || "",
    sort: params.get("sort") || "recommended", available: params.get("available") === "1",
    verified: params.get("verified") === "1", page: Math.max(1, Number(params.get("page")) || 1),
  };

  const setFilter = (changes) => {
    const next = new URLSearchParams(params);
    Object.entries({ page: 1, ...changes }).forEach(([k, v]) => {
      if (v === "" || v === false || v === null || (k === "page" && v === 1) || (k === "sort" && v === "recommended")) next.delete(k);
      else next.set(k, v === true ? "1" : v);
    });
    setParams(next);
  };

  // Areas people have actually registered, merged with the standard list.
  useEffect(() => {
    api.get("/api/artisans/locations")
      .then((res) => setAreas([...new Set([...LOCATIONS, ...res.data.map((l) => l.location)])].sort()))
      .catch(() => {});
  }, []);

  const queryKey = params.toString();
  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError("");
    api.get("/api/artisans", {
      params: {
        q: f.q || undefined, category: f.category || undefined, location: f.location || undefined, sort: f.sort,
        available_only: f.available || undefined, verified_only: f.verified || undefined, page: f.page, page_size: 12,
      },
    })
      .then((res) => { if (!cancelled) setData(res.data); })
      .catch((e) => { if (!cancelled) setError(getErrorMessage(e)); })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [queryKey]);

  const categoryName = useMemo(() => categories.find((c) => c.slug === f.category)?.name, [categories, f.category]);
  const hasFilters = f.q || f.category || f.location || f.available || f.verified;
  const heading = `${categoryName ? categoryName + "s" : "Skilled workers"}${f.location ? ` in ${f.location}` : " across Ghana"}`;

  return (
    <>
      <section className="bg-brand-50">
        <div className="mx-auto max-w-6xl px-4 py-10">
          <h1 className="text-3xl font-extrabold md:text-4xl">{heading}</h1>
          <form
            onSubmit={(e) => { e.preventDefault(); setFilter({ q: qInput.trim() }); }}
            className="mt-6 flex gap-2" role="search"
          >
            <label htmlFor="q" className="sr-only">Search by name or skill</label>
            <input id="q" className="field" placeholder="Search by name, skill or keyword" value={qInput} onChange={(e) => setQInput(e.target.value)} />
            <button className="btn-accent shrink-0"><Search size={18} aria-hidden="true" /> Search</button>
          </form>
        </div>
      </section>

      <section className="mx-auto max-w-6xl px-4 py-8">
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <div>
            <label htmlFor="f-category" className="label">Profession</label>
            <select id="f-category" className="field" value={f.category} onChange={(e) => setFilter({ category: e.target.value })}>
              <option value="">All professions</option>
              {categories.map((c) => <option key={c.id} value={c.slug}>{c.name}</option>)}
            </select>
          </div>
          <div>
            <label htmlFor="f-location" className="label">Area</label>
            <select id="f-location" className="field" value={f.location} onChange={(e) => setFilter({ location: e.target.value })}>
              <option value="">All areas</option>
              {areas.map((l) => <option key={l} value={l}>{l}</option>)}
            </select>
          </div>
          <div>
            <label htmlFor="f-sort" className="label">Sort by</label>
            <select id="f-sort" className="field" value={f.sort} onChange={(e) => setFilter({ sort: e.target.value })}>
              {SORTS.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
            </select>
          </div>
          <fieldset className="flex flex-col justify-end gap-2 pb-1">
            <legend className="sr-only">Quick filters</legend>
            <label className="flex items-center gap-2 font-semibold text-brand-900">
              <input type="checkbox" className="h-4 w-4 accent-brand-800" checked={f.available} onChange={(e) => setFilter({ available: e.target.checked })} /> Available now
            </label>
            <label className="flex items-center gap-2 font-semibold text-brand-900">
              <input type="checkbox" className="h-4 w-4 accent-brand-800" checked={f.verified} onChange={(e) => setFilter({ verified: e.target.checked })} /> Verified only
            </label>
          </fieldset>
        </div>

        <div className="mt-6 flex items-center justify-between gap-3" aria-live="polite">
          <p className="text-slate-600">{loading ? "Searching…" : data ? `${data.total} ${data.total === 1 ? "artisan" : "artisans"} found` : ""}</p>
          {hasFilters && <button onClick={() => { setQInput(""); setParams({}); }} className="font-semibold text-brand-700 underline">Clear filters</button>}
        </div>

        {error && <p role="alert" className="mt-6 rounded-2xl bg-accent-100 p-4 text-accent-700">{error}</p>}

        {loading && !data && (
          <div className="mt-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-3" aria-busy="true">
            {Array.from({ length: 6 }).map((_, i) => <div key={i} className="h-52 animate-pulse rounded-2xl bg-slate-100" />)}
          </div>
        )}

        {data && data.items.length > 0 && (
          <div className={`mt-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-3 ${loading ? "opacity-60" : ""}`}>
            {data.items.map((a) => <ArtisanCard key={a.id} artisan={a} />)}
          </div>
        )}

        {data && !loading && data.items.length === 0 && !error && (
          <div className="mt-6 rounded-2xl border border-dashed border-brand-200 bg-brand-50 p-10 text-center">
            <SearchX size={36} className="mx-auto text-brand-600" aria-hidden="true" />
            <h2 className="mt-3 text-xl font-bold">No artisans match your search</h2>
            <p className="mt-1 text-slate-600">Try another area or profession, or remove a filter.</p>
            <div className="mt-4 flex flex-wrap justify-center gap-3">
              {hasFilters && <button onClick={() => { setQInput(""); setParams({}); }} className="btn-primary">Clear filters</button>}
              <Link to="/register?role=artisan" className="btn-outline">Are you a skilled worker? Join us</Link>
            </div>
          </div>
        )}

        {data && data.pages > 1 && (
          <nav className="mt-8 flex items-center justify-center gap-4" aria-label="Pagination">
            <button className="btn-outline" disabled={f.page <= 1} onClick={() => setFilter({ page: f.page - 1 })}>Previous</button>
            <span className="font-semibold text-brand-900">Page {data.page} of {data.pages}</span>
            <button className="btn-outline" disabled={f.page >= data.pages} onClick={() => setFilter({ page: f.page + 1 })}>Next</button>
          </nav>
        )}
      </section>
    </>
  );
}
