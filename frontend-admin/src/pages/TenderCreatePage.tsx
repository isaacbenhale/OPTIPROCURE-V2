import { useState } from "react";
import { useNavigate } from "react-router-dom";

import { createTender, type TenderInput } from "../api/tenders";
import { ErrorBanner } from "../components/ErrorBanner";
import { TenderForm } from "../components/TenderForm";

export function TenderCreatePage() {
  const navigate = useNavigate();
  const [error, setError] = useState<unknown>(null);

  async function handleSubmit(input: TenderInput): Promise<void> {
    setError(null);
    try {
      const tender = await createTender(input);
      navigate(`/tenders/${tender.id}`);
    } catch (err) {
      setError(err);
    }
  }

  return (
    <div>
      <h1>Nouvel appel d'offres</h1>
      <p className="muted">
        Le brouillon peut être modifié tant qu'il n'est pas soumis à révision. Les champs marqués * sont requis pour
        créer le brouillon ; d'autres (type de marché, type de procédure, contact) deviendront obligatoires au moment
        de la soumission.
      </p>
      <ErrorBanner error={error} />
      <TenderForm onSubmit={handleSubmit} submitLabel="Créer le brouillon" />
    </div>
  );
}
