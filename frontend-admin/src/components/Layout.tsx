import { useState } from "react";
import { Link, NavLink, Outlet, useLocation } from "react-router-dom";

import { useAuth } from "../auth/AuthContext";
import { ConfirmDialog } from "./ConfirmDialog";
import { IconChevronRight, IconLayers, IconLogout, IconShield, IconTenders, IconUsers } from "./Icons";
import { Logo } from "./Logo";

const BREADCRUMB_LABELS: { test: (path: string) => boolean; label: string }[] = [
  { test: (p) => p === "/tenders/new", label: "Nouvel AO" },
  { test: (p) => /^\/tenders\/[^/]+$/.test(p), label: "Détail de l'AO" },
  { test: (p) => p.startsWith("/tenders"), label: "Appels d'offres" },
  { test: (p) => p.startsWith("/referentiels"), label: "Référentiels" },
  { test: (p) => p.startsWith("/utilisateurs"), label: "Utilisateurs" },
  { test: (p) => p.startsWith("/securite"), label: "Sécurité" },
];

function initials(name: string): string {
  const parts = name.trim().split(/\s+/);
  return parts
    .slice(0, 2)
    .map((p) => p[0]?.toUpperCase() ?? "")
    .join("");
}

export function Layout() {
  const { user, logout } = useAuth();
  const location = useLocation();
  const [confirmingLogout, setConfirmingLogout] = useState(false);

  const currentLabel = BREADCRUMB_LABELS.find((entry) => entry.test(location.pathname))?.label ?? "";

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="sidebar-top">
          <Logo />
        </div>

        <nav className="sidebar-nav">
          <span className="sidebar-nav-label">Menu</span>
          <NavLink to="/tenders" className={({ isActive }) => `nav-item${isActive ? " nav-item-active" : ""}`}>
            <IconTenders size={18} />
            Appels d'offres
          </NavLink>
          {user?.role === "ADMIN" && (
            <NavLink
              to="/referentiels"
              className={({ isActive }) => `nav-item${isActive ? " nav-item-active" : ""}`}
            >
              <IconLayers size={18} />
              Référentiels
            </NavLink>
          )}
          {user?.role === "ADMIN" && (
            <NavLink
              to="/utilisateurs"
              className={({ isActive }) => `nav-item${isActive ? " nav-item-active" : ""}`}
            >
              <IconUsers size={18} />
              Utilisateurs
            </NavLink>
          )}
          <NavLink to="/securite" className={({ isActive }) => `nav-item${isActive ? " nav-item-active" : ""}`}>
            <IconShield size={18} />
            Sécurité
          </NavLink>
        </nav>

        {user && (
          <div className="sidebar-user">
            <span className="avatar">{initials(user.full_name)}</span>
            <span className="sidebar-user-info">
              <span className="sidebar-user-name">{user.full_name}</span>
              <span className={`role-chip role-chip-${user.role.toLowerCase()}`}>{user.role}</span>
            </span>
            <button
              type="button"
              className="icon-button"
              title="Déconnexion"
              onClick={() => setConfirmingLogout(true)}
            >
              <IconLogout size={17} />
            </button>
          </div>
        )}
      </aside>

      <div className="app-main">
        <header className="topbar">
          <div className="breadcrumb">
            <Link to="/tenders">Back-office</Link>
            {currentLabel && (
              <>
                <IconChevronRight size={14} className="breadcrumb-sep" />
                <span>{currentLabel}</span>
              </>
            )}
          </div>
          {user && (
            <div className="topbar-user">
              <span className="avatar avatar-sm">{initials(user.full_name)}</span>
              <span className="topbar-user-name">{user.full_name}</span>
            </div>
          )}
        </header>

        <main className="content">
          <Outlet />
        </main>
      </div>

      <ConfirmDialog
        open={confirmingLogout}
        title="Déconnexion"
        message="Voulez-vous vraiment vous déconnecter ?"
        confirmLabel="Se déconnecter"
        cancelLabel="Annuler"
        onConfirm={logout}
        onCancel={() => setConfirmingLogout(false)}
      />
    </div>
  );
}
