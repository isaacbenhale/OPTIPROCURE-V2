import { useEffect, useState } from "react";

import { useAuth } from "../auth/AuthContext";
import { clearTokens } from "../auth/cognito";

// Casse-boucle : sans ça, tout échec (même transitoire) sur /me ou l'échange
// de code renvoyait ici, qui relançait Cognito inconditionnellement à
// chaque montage — boucle invisible /login <-> /callback, sans jamais
// afficher d'erreur réelle (bug réel constaté le 2026-08-07). Si on revient
// sur /login moins de 8s après une tentative, on considère que ça boucle et
// on affiche un message au lieu de re-rediriger.
const LOOP_GUARD_KEY = "optiprocure_login_redirect_at";
const LOOP_WINDOW_MS = 8000;

export function LoginPage() {
  const { login } = useAuth();
  const [loopDetected, setLoopDetected] = useState(false);

  useEffect(() => {
    const last = Number(sessionStorage.getItem(LOOP_GUARD_KEY) ?? "0");
    const now = Date.now();
    if (now - last < LOOP_WINDOW_MS) {
      clearTokens();
      setLoopDetected(true);
      return;
    }
    sessionStorage.setItem(LOOP_GUARD_KEY, String(now));
    void login();
  }, [login]);

  if (loopDetected) {
    return (
      <div className="centered">
        <p>
          La connexion échoue de façon répétée. Vérifie ta connexion réseau, ou contacte un administrateur
          si le problème persiste.
        </p>
        <button
          type="button"
          onClick={() => {
            sessionStorage.removeItem(LOOP_GUARD_KEY);
            setLoopDetected(false);
            void login();
          }}
        >
          Réessayer la connexion
        </button>
      </div>
    );
  }

  return (
    <div className="centered">
      <p>Redirection vers la connexion…</p>
    </div>
  );
}
