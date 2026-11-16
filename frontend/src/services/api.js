import axios from "axios";

const TOKEN_KEY = "fsw_token";

export const tokenStore = {
  get: () => localStorage.getItem(TOKEN_KEY),
  set: (t) => localStorage.setItem(TOKEN_KEY, t),
  clear: () => localStorage.removeItem(TOKEN_KEY),
};

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL ?? "http://localhost:8000",   // an EMPTY value means "same address as the website"
  timeout: 15000,
});

api.interceptors.request.use((config) => {
  const token = tokenStore.get();
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

api.interceptors.response.use(
  (res) => res,
  (error) => {
    const isAuthAttempt = error.config?.url?.includes("/api/auth/login") || error.config?.url?.includes("/api/auth/register");
    if (error.response?.status === 401 && !isAuthAttempt) {
      tokenStore.clear();
      window.dispatchEvent(new Event("auth:expired"));
    }
    return Promise.reject(error);
  }
);

/** Turns any API/network error into a message a person can act on. */
export function getErrorMessage(error) {
  if (!error.response) {
    return `Cannot reach the server at ${api.defaults.baseURL}. Make sure the backend is running (in the backend folder: uvicorn main:app --reload), then try again.`;
  }
  const data = error.response.data;
  if (Array.isArray(data?.errors) && data.errors.length) {
    return data.errors.map((e) => `${e.field ? e.field.replace(/_/g, " ") + ": " : ""}${e.message}`).join(". ");
  }
  if (typeof data?.detail === "string") return data.detail;
  return "Something went wrong. Please try again.";
}

export default api;

/** Turns a stored path like /uploads/profiles/abc.jpg into a full URL on the backend. */
export function mediaUrl(path) {
  if (!path) return null;
  return /^https?:\/\//.test(path) ? path : `${api.defaults.baseURL}${path}`;
}
