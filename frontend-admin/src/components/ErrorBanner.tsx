import { ApiError } from "../api/client";

// Rendu uniforme de error.code/error.fields — jamais de JSON brut affiché
// (voir tasks/03-frontend-admin-backoffice.md, définition de "terminé").
export function ErrorBanner({ error }: { error: unknown }) {
  if (!error) return null;

  if (error instanceof ApiError) {
    const fieldEntries = Object.entries(error.fields);
    return (
      <div className="error-banner" role="alert">
        <p>{error.message}</p>
        {fieldEntries.length > 0 && (
          <ul>
            {fieldEntries.map(([field, detail]) => (
              <li key={field}>
                <strong>{field}</strong> : {String(detail)}
              </li>
            ))}
          </ul>
        )}
      </div>
    );
  }

  const message = error instanceof Error ? error.message : "Une erreur inattendue est survenue.";
  return (
    <div className="error-banner" role="alert">
      <p>{message}</p>
    </div>
  );
}
