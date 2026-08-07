import { useEffect, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";

import { useAuth } from "../auth/AuthContext";
import { ErrorBanner } from "../components/ErrorBanner";

export function CallbackPage() {
  const { handleCallback } = useAuth();
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const [error, setError] = useState<unknown>(null);

  useEffect(() => {
    const code = searchParams.get("code");
    const state = searchParams.get("state");
    const cognitoError = searchParams.get("error_description") ?? searchParams.get("error");

    if (cognitoError) {
      setError(new Error(cognitoError));
      return;
    }
    if (!code || !state) {
      setError(new Error("Callback OAuth invalide (code ou state manquant)."));
      return;
    }

    handleCallback(code, state)
      .then(() => navigate("/tenders", { replace: true }))
      .catch((err: unknown) => setError(err));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div className="centered">
      <div style={{ width: "100%", maxWidth: 360 }}>
        <span className="logo-mark">OP</span>
        {error ? (
          <>
            <ErrorBanner error={error} />
            <p>
              <a href="/login">Réessayer</a>
            </p>
          </>
        ) : (
          <p>Connexion en cours…</p>
        )}
      </div>
    </div>
  );
}
