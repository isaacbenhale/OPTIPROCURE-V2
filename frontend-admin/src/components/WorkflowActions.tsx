import { useState } from "react";

import { useAuth } from "../auth/AuthContext";
import type { AvailableAction, Tender } from "../types";

interface WorkflowActionsProps {
  tender: Tender;
  onSubmit: () => Promise<void>;
  onReturn: (reason: string) => Promise<void>;
  onEndorse: () => Promise<void>;
  onApprove: () => Promise<void>;
  onReject: (reason: string) => Promise<void>;
  onArchive: () => Promise<void>;
  onDelete: () => Promise<void>;
}

const ACTION_LABELS: Record<AvailableAction, string> = {
  update: "Modifier",
  submit: "Soumettre à révision",
  return: "Retourner à l'agent",
  endorse: "Endosser",
  approve: "Approuver",
  reject: "Rejeter",
  archive: "Archiver",
  delete: "Supprimer",
};

const REASON_REQUIRED: AvailableAction[] = ["return", "reject"];
// Miroir de transitions.py NON_STATUS_ACTIONS/STATUS_ACTIONS "requires_mfa"
// — juste pour l'affichage indicatif, la vérification réelle reste côté
// Lambda (double contrôle, ne jamais faire confiance à ce hint côté client).
const MFA_REQUIRED: AvailableAction[] = ["approve", "reject", "archive"];

// "update" est piloté par le formulaire d'édition (TenderForm), pas un
// bouton d'action ici.
const BUTTON_ACTIONS: AvailableAction[] = ["submit", "return", "endorse", "approve", "reject", "archive", "delete"];

export function WorkflowActions({
  tender,
  onSubmit,
  onReturn,
  onEndorse,
  onApprove,
  onReject,
  onArchive,
  onDelete,
}: WorkflowActionsProps) {
  const { user } = useAuth();
  const [pendingAction, setPendingAction] = useState<AvailableAction | null>(null);
  const [reason, setReason] = useState("");
  const [busy, setBusy] = useState(false);

  const actions = tender.available_actions.filter((action) => BUTTON_ACTIONS.includes(action));

  async function run(action: AvailableAction, reasonValue?: string): Promise<void> {
    setBusy(true);
    try {
      switch (action) {
        case "submit":
          await onSubmit();
          break;
        case "endorse":
          await onEndorse();
          break;
        case "approve":
          await onApprove();
          break;
        case "archive":
          await onArchive();
          break;
        case "delete":
          await onDelete();
          break;
        case "return":
          await onReturn(reasonValue ?? "");
          break;
        case "reject":
          await onReject(reasonValue ?? "");
          break;
        case "update":
          break; // jamais atteint, filtré par BUTTON_ACTIONS
      }
      setPendingAction(null);
      setReason("");
    } finally {
      setBusy(false);
    }
  }

  function handleClick(action: AvailableAction): void {
    if (REASON_REQUIRED.includes(action)) {
      setPendingAction(action);
      return;
    }
    void run(action);
  }

  if (actions.length === 0) {
    return null;
  }

  return (
    <div className="workflow-actions">
      <h3>Actions</h3>
      <div className="workflow-actions-buttons">
        {actions.map((action) => (
          <button key={action} type="button" disabled={busy} onClick={() => handleClick(action)}>
            {ACTION_LABELS[action]}
            {MFA_REQUIRED.includes(action) && user && !user.mfa_enabled && (
              <span className="mfa-note"> (MFA requis)</span>
            )}
          </button>
        ))}
      </div>

      {pendingAction && (
        <div className="reason-modal">
          <p>Motif pour « {ACTION_LABELS[pendingAction]} » (obligatoire) :</p>
          <textarea value={reason} onChange={(event) => setReason(event.target.value)} rows={3} />
          <div className="reason-modal-buttons">
            <button type="button" disabled={busy || !reason.trim()} onClick={() => run(pendingAction, reason)}>
              Confirmer
            </button>
            <button
              type="button"
              disabled={busy}
              onClick={() => {
                setPendingAction(null);
                setReason("");
              }}
            >
              Annuler
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
