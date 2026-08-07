import { useEffect, useState } from "react";

import { activateAccount, createAccount, deactivateAccount, deleteAccount, listAccounts, updateGroups } from "../api/users";
import { ConfirmDialog } from "../components/ConfirmDialog";
import { ErrorBanner } from "../components/ErrorBanner";
import type { Account, Role } from "../types";

const ALL_ROLES: Role[] = ["ADMIN", "REVIEWER", "AGENT"];

function GroupCheckboxes({
  selected,
  onChange,
}: {
  selected: Role[];
  onChange: (groups: Role[]) => void;
}) {
  function toggle(role: Role) {
    onChange(selected.includes(role) ? selected.filter((r) => r !== role) : [...selected, role]);
  }

  return (
    <div className="form-row">
      {ALL_ROLES.map((role) => (
        <label key={role} className="checkbox-label">
          <input type="checkbox" checked={selected.includes(role)} onChange={() => toggle(role)} />
          {role}
        </label>
      ))}
    </div>
  );
}

export function UsersPage() {
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<unknown>(null);

  const [newEmail, setNewEmail] = useState("");
  const [newGroups, setNewGroups] = useState<Role[]>([]);
  const [creating, setCreating] = useState(false);

  const [editingSub, setEditingSub] = useState<string | null>(null);
  const [editGroups, setEditGroups] = useState<Role[]>([]);
  const [savingGroups, setSavingGroups] = useState(false);

  const [confirmTarget, setConfirmTarget] = useState<{
    sub: string;
    email: string;
    action: "activate" | "deactivate" | "delete";
  } | null>(null);
  const [togglingActive, setTogglingActive] = useState(false);

  function reload() {
    setLoading(true);
    listAccounts()
      .then((res) => setAccounts(res.items))
      .catch((err: unknown) => setError(err))
      .finally(() => setLoading(false));
  }

  useEffect(reload, []);

  function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setCreating(true);
    createAccount({ email: newEmail.trim().toLowerCase(), groups: newGroups })
      .then(() => {
        setNewEmail("");
        setNewGroups([]);
        reload();
      })
      .catch((err: unknown) => setError(err))
      .finally(() => setCreating(false));
  }

  function startEditGroups(account: Account) {
    setEditingSub(account.cognito_sub);
    setEditGroups(account.groups);
  }

  function saveGroups(sub: string) {
    setError(null);
    setSavingGroups(true);
    updateGroups(sub, editGroups)
      .then(() => {
        setEditingSub(null);
        reload();
      })
      .catch((err: unknown) => setError(err))
      .finally(() => setSavingGroups(false));
  }

  function confirmPendingAction() {
    if (!confirmTarget) return;
    setError(null);
    setTogglingActive(true);
    const action =
      confirmTarget.action === "activate"
        ? activateAccount
        : confirmTarget.action === "deactivate"
          ? deactivateAccount
          : deleteAccount;
    action(confirmTarget.sub)
      .then(() => {
        setConfirmTarget(null);
        reload();
      })
      .catch((err: unknown) => setError(err))
      .finally(() => setTogglingActive(false));
  }

  return (
    <div>
      <div className="page-header">
        <h1>Utilisateurs</h1>
      </div>
      <p className="muted">
        Comptes back-office (AGENT/REVIEWER/ADMIN). Un changement de groupes révoque la session active du
        compte concerné (reconnexion nécessaire pour que le nouveau rôle s'applique).
      </p>

      <form className="tender-form" onSubmit={handleCreate}>
        <ErrorBanner error={error} />
        <label>
          Email *
          <input
            required
            type="email"
            value={newEmail}
            onChange={(e) => setNewEmail(e.target.value)}
            placeholder="prenom.nom@optiprocure.test"
          />
        </label>
        <p className="muted">Groupes (au moins un) :</p>
        <GroupCheckboxes selected={newGroups} onChange={setNewGroups} />
        <button type="submit" disabled={creating || newGroups.length === 0}>
          {creating ? "Création…" : "+ Créer un compte"}
        </button>
      </form>

      {loading ? (
        <p>Chargement…</p>
      ) : accounts.length === 0 ? (
        <p className="muted">Aucun compte interne pour l'instant.</p>
      ) : (
        <table className="tenders-table">
          <thead>
            <tr>
              <th>Email</th>
              <th>Groupes</th>
              <th>MFA</th>
              <th>Statut</th>
              <th>Dernière connexion</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {accounts.map((account) => (
              <tr key={account.cognito_sub}>
                <td>{account.email}</td>
                <td>
                  {editingSub === account.cognito_sub ? (
                    <div>
                      <GroupCheckboxes selected={editGroups} onChange={setEditGroups} />
                      <div className="workflow-actions-buttons">
                        <button
                          type="button"
                          disabled={savingGroups || editGroups.length === 0}
                          onClick={() => saveGroups(account.cognito_sub)}
                        >
                          {savingGroups ? "Enregistrement…" : "Enregistrer"}
                        </button>
                        <button type="button" disabled={savingGroups} onClick={() => setEditingSub(null)}>
                          Annuler
                        </button>
                      </div>
                    </div>
                  ) : (
                    <>
                      {account.groups.join(", ")}{" "}
                      <button type="button" onClick={() => startEditGroups(account)}>
                        Modifier
                      </button>
                    </>
                  )}
                </td>
                <td>{account.mfa_enabled ? "Activé" : "—"}</td>
                <td>{account.is_active ? "Actif" : "Désactivé"}</td>
                <td>
                  {account.has_logged_in && account.last_login_at
                    ? new Date(account.last_login_at).toLocaleString("fr-FR")
                    : "Jamais connecté"}
                </td>
                <td>
                  <div className="workflow-actions-buttons">
                    <button
                      type="button"
                      onClick={() =>
                        setConfirmTarget({
                          sub: account.cognito_sub,
                          email: account.email,
                          action: account.is_active ? "deactivate" : "activate",
                        })
                      }
                    >
                      {account.is_active ? "Désactiver" : "Réactiver"}
                    </button>
                    <button
                      type="button"
                      className="button-secondary"
                      onClick={() =>
                        setConfirmTarget({ sub: account.cognito_sub, email: account.email, action: "delete" })
                      }
                    >
                      Supprimer
                    </button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      <ConfirmDialog
        open={confirmTarget !== null}
        title={
          confirmTarget?.action === "delete"
            ? "Supprimer le compte"
            : confirmTarget?.action === "deactivate"
              ? "Désactiver le compte"
              : "Réactiver le compte"
        }
        message={
          confirmTarget?.action === "delete"
            ? `Suppression définitive et irréversible du compte ${confirmTarget.email} (accès Cognito supprimé). Continuer ?`
            : confirmTarget
              ? `Voulez-vous vraiment ${confirmTarget.action === "deactivate" ? "désactiver" : "réactiver"} le compte ${confirmTarget.email} ?`
              : ""
        }
        confirmLabel={
          confirmTarget?.action === "delete" ? "Supprimer" : confirmTarget?.action === "deactivate" ? "Désactiver" : "Réactiver"
        }
        cancelLabel="Annuler"
        onConfirm={confirmPendingAction}
        onCancel={() => setConfirmTarget(null)}
      />
      {togglingActive && <p className="muted">Mise à jour…</p>}
    </div>
  );
}
