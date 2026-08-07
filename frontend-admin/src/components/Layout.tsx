import { Link, Outlet } from "react-router-dom";

import { useAuth } from "../auth/AuthContext";

export function Layout() {
  const { user, logout } = useAuth();

  return (
    <div className="layout">
      <header className="layout-header">
        <Link to="/tenders" className="layout-brand">
          OptiProcure — Back-office
        </Link>
        {user && (
          <div className="layout-user">
            <span>
              {user.full_name} · <strong>{user.role}</strong>
            </span>
            <button type="button" onClick={logout}>
              Déconnexion
            </button>
          </div>
        )}
      </header>
      <main className="layout-main">
        <Outlet />
      </main>
    </div>
  );
}
