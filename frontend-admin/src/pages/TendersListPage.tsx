import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { useAuth } from "../auth/AuthContext";
import { listTenders, type TenderListFilters } from "../api/tenders";
import { ErrorBanner } from "../components/ErrorBanner";
import { StatusBadge } from "../components/StatusBadge";
import type { Tender, TenderStatus } from "../types";

const STATUS_FILTERS: TenderStatus[] = [
  "DRAFT",
  "PENDING_REVIEW",
  "REVISION_REQUESTED",
  "APPROVED",
  "PUBLISHED",
  "EXPIRED",
  "REJECTED",
  "ARCHIVED",
];

export function TendersListPage() {
  const { user } = useAuth();
  const [tenders, setTenders] = useState<Tender[]>([]);
  const [status, setStatus] = useState<string>("");
  const [q, setQ] = useState("");
  const [error, setError] = useState<unknown>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const filters: TenderListFilters = {};
    if (status) filters.status = status;
    if (q) filters.q = q;

    setLoading(true);
    listTenders(filters)
      .then((res) => setTenders(res.items))
      .catch((err: unknown) => setError(err))
      .finally(() => setLoading(false));
  }, [status, q]);

  return (
    <div>
      <div className="page-header">
        <h1>Appels d'offres</h1>
        {(user?.role === "AGENT" || user?.role === "ADMIN") && (
          <Link to="/tenders/new" className="button-link">
            + Nouvel AO
          </Link>
        )}
      </div>

      <div className="filters">
        <input
          type="search"
          placeholder="Rechercher par titre ou référence…"
          value={q}
          onChange={(e) => setQ(e.target.value)}
        />
        <select value={status} onChange={(e) => setStatus(e.target.value)}>
          <option value="">Tous les statuts</option>
          {STATUS_FILTERS.map((s) => (
            <option key={s} value={s}>
              {s}
            </option>
          ))}
        </select>
      </div>

      <ErrorBanner error={error} />

      {loading ? (
        <p>Chargement…</p>
      ) : tenders.length === 0 ? (
        <p className="muted">Aucun AO ne correspond à ces critères.</p>
      ) : (
        <table className="tenders-table">
          <thead>
            <tr>
              <th>Titre</th>
              <th>Statut</th>
              <th>Date limite</th>
            </tr>
          </thead>
          <tbody>
            {tenders.map((tender) => (
              <tr key={tender.id}>
                <td>
                  <Link to={`/tenders/${tender.id}`}>{tender.title || "(sans titre)"}</Link>
                </td>
                <td>
                  <StatusBadge status={tender.status} />
                </td>
                <td>{new Date(tender.submission_deadline).toLocaleDateString("fr-FR")}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
