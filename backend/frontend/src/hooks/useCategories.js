import { useEffect, useState } from "react";
import api, { getErrorMessage } from "../services/api";

/** Loads service categories from the API (shared by the home page and forms). */
export default function useCategories() {
  const [categories, setCategories] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;
    api.get("/api/categories")
      .then((res) => !cancelled && setCategories(res.data))
      .catch((e) => !cancelled && setError(getErrorMessage(e)))
      .finally(() => !cancelled && setLoading(false));
    return () => { cancelled = true; };
  }, []);

  return { categories, loading, error };
}
