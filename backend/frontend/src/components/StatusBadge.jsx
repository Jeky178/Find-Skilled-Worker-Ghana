import { STATUS } from "../utils";

export default function StatusBadge({ status }) {
  const s = STATUS[status] || { label: status, cls: "bg-slate-100 text-slate-700" };
  return <span className={`inline-block rounded-full px-3 py-1 text-sm font-bold ${s.cls}`}>{s.label}</span>;
}
