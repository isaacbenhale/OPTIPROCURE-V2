import { useCallback, useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";

import {
  approveTender,
  archiveTender,
  deleteTender,
  endorseTender,
  getTender,
  getTenderHistory,
  rejectTender,
  returnTender,
  submitTender,
  updateTender,
  type TenderInput,
} from "../api/tenders";
import { DocumentsPanel } from "../components/DocumentsPanel";
import { ErrorBanner } from "../components/ErrorBanner";
import { HistoryTimeline } from "../components/HistoryTimeline";
import { StatusBadge } from "../components/StatusBadge";
import { TenderForm } from "../components/TenderForm";
import { WorkflowActions } from "../components/WorkflowActions";
import type { StatusHistoryEntry, Tender } from "../types";

export function TenderDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [tender, setTender] = useState<Tender | null>(null);
  const [history, setHistory] = useState<StatusHistoryEntry[]>([]);
  const [error, setError] = useState<unknown>(null);
  const [editing, setEditing] = useState(false);

  const refresh = useCallback(async () => {
    if (!id) return;
    try {
      const [tenderData, historyData] = await Promise.all([getTender(id), getTenderHistory(id)]);
      setTender(tenderData);
      setHistory(historyData.items);
    } catch (err) {
      setError(err);
    }
  }, [id]);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  if (!id) return null;
  if (error && !tender) return <ErrorBanner error={error} />;
  if (!tender) return <p>Chargement…</p>;

  const canEdit = tender.available_actions.includes("update");

  async function withErrorHandling(action: () => Promise<unknown>): Promise<void> {
    setError(null);
    try {
      await action();
      await refresh();
    } catch (err) {
      setError(err);
    }
  }

  async function handleFormSubmit(input: TenderInput): Promise<void> {
    await withErrorHandling(() => updateTender(id!, input));
    setEditing(false);
  }

  async function handleDelete(): Promise<void> {
    await deleteTender(id!);
    navigate("/tenders");
  }

  return (
    <div>
      <div className="page-header">
        <h1>{tender.title || "(sans titre)"}</h1>
        <StatusBadge status={tender.status} />
      </div>

      <ErrorBanner error={error} />

      {editing ? (
        <TenderForm initialValue={tender} onSubmit={handleFormSubmit} submitLabel="Enregistrer" />
      ) : (
        <div className="tender-detail-grid">
          <div>
            <dl>
              <dt>Référence</dt>
              <dd>{tender.reference_number || "—"}</dd>
              <dt>Description</dt>
              <dd>{tender.description}</dd>
              <dt>Secteur</dt>
              <dd>{tender.sector === "PUBLIC" ? "Public" : "Privé"}</dd>
              <dt>Type de marché / procédure</dt>
              <dd>
                {tender.procurement_type ?? "—"} / {tender.procedure_type ?? "—"}
              </dd>
              <dt>Localisation</dt>
              <dd>
                {[tender.location_city, tender.location_region].filter(Boolean).join(", ") || "—"}
              </dd>
              <dt>Budget estimé</dt>
              <dd>
                {tender.estimated_budget ? `${tender.estimated_budget} ${tender.currency ?? ""}` : "—"}
              </dd>
              <dt>Date limite de dépôt</dt>
              <dd>{new Date(tender.submission_deadline).toLocaleString("fr-FR")}</dd>
              <dt>Contact</dt>
              <dd>
                {tender.contact_name ?? "—"} {tender.contact_email ? `(${tender.contact_email})` : ""}
              </dd>
            </dl>

            {canEdit && (
              <button type="button" onClick={() => setEditing(true)}>
                Modifier
              </button>
            )}
          </div>

          <div>
            <WorkflowActions
              tender={tender}
              onSubmit={() => withErrorHandling(() => submitTender(id))}
              onReturn={(reason) => withErrorHandling(() => returnTender(id, reason))}
              onEndorse={() => withErrorHandling(() => endorseTender(id))}
              onApprove={() => withErrorHandling(() => approveTender(id))}
              onReject={(reason) => withErrorHandling(() => rejectTender(id, reason))}
              onArchive={() => withErrorHandling(() => archiveTender(id))}
              onDelete={handleDelete}
            />

            <DocumentsPanel tenderId={id} canManage={canEdit} />

            <div className="history-section">
              <h3>Historique</h3>
              <HistoryTimeline entries={history} />
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
