import { useState } from "react";
import { Link, NavLink, useNavigate } from "react-router-dom";
import { Bell, Menu, X } from "lucide-react";
import { useAuth } from "../context/AuthContext";
import useUnreadCount from "../hooks/useUnreadCount";

export default function Navbar() {
  const { user, logout } = useAuth();
  const unread = useUnreadCount();
  const [open, setOpen] = useState(false);
  const navigate = useNavigate();

  const links = [
    { to: "/artisans", label: "Browse artisans" },
    ...(user && user.role !== "admin" ? [{ to: "/requests", label: "My requests" }] : []),
    ...(user?.role === "admin" ? [{ to: "/admin", label: "Admin" }] : []),
    { to: "/about", label: "About" },
    { to: "/contact", label: "Contact" },
  ];

  const linkClass = ({ isActive }) =>
    `rounded-full px-3 py-2 font-semibold transition-colors ${isActive ? "bg-brand-50 text-brand-800" : "text-slate-700 hover:text-brand-800"}`;

  const handleLogout = () => {
    logout();
    setOpen(false);
    navigate("/");
  };

  const bell = (
    <Link to="/notifications" className="relative rounded-full p-2 text-slate-700 hover:bg-brand-50" aria-label={unread ? `Notifications, ${unread} unread` : "Notifications"} onClick={() => setOpen(false)}>
      <Bell size={22} aria-hidden="true" />
      {unread > 0 && (
        <span className="absolute -right-0.5 -top-0.5 grid min-w-[1.25rem] place-items-center rounded-full bg-accent-600 px-1 text-xs font-bold text-white">{unread > 9 ? "9+" : unread}</span>
      )}
    </Link>
  );

  return (
    <header className="sticky top-0 z-30 border-b border-slate-200 bg-white/95 backdrop-blur">
      <nav className="mx-auto flex max-w-6xl items-center justify-between px-4 py-3" aria-label="Main">
        <Link to="/" className="flex items-center gap-2" onClick={() => setOpen(false)}>
          <span className="grid h-9 w-9 place-items-center rounded-xl bg-brand-900" aria-hidden="true">
            <span className="h-3.5 w-3.5 rounded-full bg-accent-500" />
          </span>
          <span className="font-display text-lg font-bold text-brand-900">Find a Skilled Worker</span>
        </Link>

        <div className="hidden items-center gap-1 md:flex">
          {links.map((l) => <NavLink key={l.to} to={l.to} className={linkClass}>{l.label}</NavLink>)}
        </div>

        <div className="hidden items-center gap-2 md:flex">
          {user ? (
            <>
              {bell}
              <Link to="/dashboard" className="btn-outline">My dashboard</Link>
              <button onClick={handleLogout} className="px-3 py-2 font-semibold text-slate-600 hover:text-brand-800">Log out</button>
            </>
          ) : (
            <>
              <Link to="/login" className="px-3 py-2 font-semibold text-brand-800 hover:underline">Log in</Link>
              <Link to="/register" className="btn-accent">Sign up</Link>
            </>
          )}
        </div>

        <div className="flex items-center gap-1 md:hidden">
          {user && bell}
          <button className="rounded-lg p-2" onClick={() => setOpen(!open)} aria-expanded={open} aria-label="Toggle menu">
            {open ? <X /> : <Menu />}
          </button>
        </div>
      </nav>

      {open && (
        <div className="space-y-1 border-t border-slate-200 bg-white px-4 pb-4 pt-2 md:hidden">
          {links.map((l) => (
            <NavLink key={l.to} to={l.to} className={linkClass} onClick={() => setOpen(false)}>
              <span className="block">{l.label}</span>
            </NavLink>
          ))}
          <div className="flex flex-col gap-2 pt-2">
            {user ? (
              <>
                <Link to="/dashboard" className="btn-outline" onClick={() => setOpen(false)}>My dashboard</Link>
                <button onClick={handleLogout} className="btn-outline">Log out</button>
              </>
            ) : (
              <>
                <Link to="/login" className="btn-outline" onClick={() => setOpen(false)}>Log in</Link>
                <Link to="/register" className="btn-accent" onClick={() => setOpen(false)}>Sign up</Link>
              </>
            )}
          </div>
        </div>
      )}
    </header>
  );
}
