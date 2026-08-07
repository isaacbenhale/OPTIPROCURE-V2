import type { TenderStatus } from "../types";

const STATUS_LABELS: Record<TenderStatus, string> = {
  DRAFT: "Brouillon",
  PENDING_REVIEW: "En révision",
  REVISION_REQUESTED: "Retourné",
  APPROVED: "Approuvé",
  QUEUED_FOR_PUBLICATION: "En attente de publication",
  PUBLISHED: "Publié",
  EXPIRED: "Expiré",
  REJECTED: "Rejeté",
  ARCHIVED: "Archivé",
};

export function StatusBadge({ status }: { status: TenderStatus }) {
  return <span className={`status-badge status-${status.toLowerCase()}`}>{STATUS_LABELS[status]}</span>;
}
