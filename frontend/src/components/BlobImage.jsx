import { useEffect, useState } from "react";
import api, { getErrorMessage } from "../services/api";
import Lightbox from "./Lightbox";

/** Shows an image that needs the login token to download (private ID documents). */
export default function BlobImage({ url, alt }) {
  const [src, setSrc] = useState("");
  const [error, setError] = useState("");
  const [zoom, setZoom] = useState(false);

  useEffect(() => {
    let objectUrl = "";
    let cancelled = false;
    setSrc(""); setError("");
    api.get(url, { responseType: "blob" })
      .then((res) => { if (!cancelled) { objectUrl = URL.createObjectURL(res.data); setSrc(objectUrl); } })
      .catch((e) => { if (!cancelled) setError(e.response ? "Could not load the document." : getErrorMessage(e)); });
    return () => { cancelled = true; if (objectUrl) URL.revokeObjectURL(objectUrl); };
  }, [url]);

  if (error) return <p role="alert" className="rounded-xl bg-accent-100 p-3 text-sm text-accent-700">{error}</p>;
  if (!src) return <div className="h-48 animate-pulse rounded-xl bg-slate-100" aria-busy="true" />;
  return (
    <>
      <button type="button" onClick={() => setZoom(true)} className="block overflow-hidden rounded-xl border border-slate-200" aria-label={`Enlarge: ${alt}`}>
        <img src={src} alt={alt} className="max-h-72 w-full object-contain bg-slate-50" />
      </button>
      {zoom && <Lightbox src={src} caption={alt} onClose={() => setZoom(false)} />}
    </>
  );
}
