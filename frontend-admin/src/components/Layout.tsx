import { useState } from "react";
import { Link, Outlet } from "react-router-dom";

import { useAuth } from "../auth/AuthContext";
import { ConfirmDialog } from "./ConfirmDialog";

export function Layout() {
  const { user, logout } = useAuth();
  const [confirmingLogout, setConfirmingLogout] = useState(false);

  return (
    <div className="layout">
      <header className="layout-header">
        <Link to="/tenders" className="layout-brand">
          OptiProcure — Back-office
        </Link>
        {user && (
          <div className="layout-user">
            {user.role === "ADMIN" && <Link to="/referentiels">Référentiels</Link>}
            <span>
              {user.full_name} · <strong>{user.role}</strong>
            </span>
            <button type="button" onClick={() => setConfirmingLogout(true)}>
              Déconnexion
            </button>
          </div>
        )}
      </header>
      <main className="layout-main">
        <Outlet />
      </main>

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
