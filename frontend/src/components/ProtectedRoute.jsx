import { Navigate, useLocation } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

export default function ProtectedRoute({ children, roles }) {
  const { user, loading } = useAuth();
  const location = useLocation();

  if (loading) return <p className="p-10 text-center text-slate-500">Loading your account…</p>;
  if (!user) return <Navigate to="/login" state={{ from: location.pathname }} replace />;
  if (roles && !roles.includes(user.role)) return <Navigate to="/dashboard" replace />;
  return children;
}
