import { useEffect } from "react";
import { X } from "lucide-react";

export default function Lightbox({ src, caption, onClose }) {
  useEffect(() => {
    const onKey = (e) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  return (
    <div role="dialog" aria-modal="true" aria-label="Photo viewer" className="fixed inset-0 z-50 grid place-items-center bg-brand-900/90 p-4" onClick={onClose}>
      <button className="absolute right-4 top-4 rounded-full bg-white p-2" onClick={onClose} aria-label="Close photo"><X size={20} /></button>
      <figure onClick={(e) => e.stopPropagation()} className="max-h-full">
        <img src={src} alt={caption || "Photo"} className="max-h-[80vh] rounded-2xl" />
        {caption && <figcaption className="mt-2 text-center text-white">{caption}</figcaption>}
      </figure>
    </div>
  );
}
