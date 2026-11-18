export default function Pager({ page, pages, onChange }) {
  if (!pages || pages <= 1) return null;
  return (
    <nav className="mt-6 flex items-center justify-center gap-4" aria-label="Pagination">
      <button className="btn-outline" disabled={page <= 1} onClick={() => onChange(page - 1)}>Previous</button>
      <span className="font-semibold text-brand-900">Page {page} of {pages}</span>
      <button className="btn-outline" disabled={page >= pages} onClick={() => onChange(page + 1)}>Next</button>
    </nav>
  );
}
