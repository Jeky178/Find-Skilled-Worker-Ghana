import { mediaUrl } from "../services/api";
import { initials } from "../utils";

export default function Avatar({ name, src, size = "h-16 w-16", text = "text-xl" }) {
  const url = mediaUrl(src);
  return url ? (
    <img src={url} alt={`${name}`} className={`${size} shrink-0 rounded-full object-cover`} loading="lazy" />
  ) : (
    <span aria-hidden="true" className={`${size} ${text} grid shrink-0 place-items-center rounded-full bg-brand-900 font-display font-bold text-white`}>
      {initials(name)}
    </span>
  );
}
