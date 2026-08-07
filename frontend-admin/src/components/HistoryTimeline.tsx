import type { StatusHistoryEntry } from "../types";

export function HistoryTimeline({ entries }: { entries: StatusHistoryEntry[] }) {
  if (entries.length === 0) {
    return <p className="muted">Aucun historique pour l'instant.</p>;
  }

  return (
    <ul className="history-timeline">
      {entries.map((entry, index) => (
        <li key={index}>
          <div>
            <strong>
              {entry.from_status ?? "—"} → {entry.to_status}
            </strong>
            <span className="muted"> · {new Date(entry.created_at).toLocaleString("fr-FR")}</span>
          </div>
          {entry.reason && <p>Motif : {entry.reason}</p>}
        </li>
      ))}
    </ul>
  );
}
