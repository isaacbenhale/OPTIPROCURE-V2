import { createContext, useContext, useEffect, useState, type ReactNode } from "react";

import { apiRequest } from "../api/client";
import type { User } from "../types";
import {
  clearLoginLoopGuard,
  exchangeCodeForTokens,
  loadTokens,
  logout as cognitoLogout,
  redirectToLogin,
} from "./cognito";

interface AuthContextValue {
  user: User | null;
  isLoading: boolean;
  login: () => Promise<void>;
  logout: () => void;
  handleCallback: (code: string, state: string) => Promise<void>;
  refreshUser: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  async function loadCurrentUser(): Promise<void> {
    try {
      const me = await apiRequest<User>("/me");
      setUser(me);
    } catch {
      setUser(null);
    }
  }

  useEffect(() => {
    if (loadTokens()) {
      loadCurrentUser().finally(() => setIsLoading(false));
    } else {
      setIsLoading(false);
    }
  }, []);

  async function handleCallback(code: string, state: string): Promise<void> {
    await exchangeCodeForTokens(code, state);
    // Volontairement pas loadCurrentUser() ici : cette fonction avale ses
    // erreurs (comportement voulu pour le montage initial silencieux), ce
    // qui faisait échouer /me sans jamais le signaler à CallbackPage —
    // celle-ci naviguait alors vers /tenders avec user=null, RequireAuth
    // rebondissait vers /login, qui relançait Cognito : boucle invisible
    // sans jamais afficher d'erreur réelle (bug réel constaté le 2026-08-07).
    const me = await apiRequest<User>("/me");
    setUser(me);
    clearLoginLoopGuard();
  }

  function logout(): void {
    // Ne PAS faire setUser(null) ici : ça déclenche un re-render synchrone
    // de RequireAuth (Navigate vers /login) AVANT que la vraie navigation
    // plein-page vers Cognito /logout (ci-dessous) n'ait eu le temps de
    // partir — LoginPage se monte alors en avance, pose son verrou anti-
    // boucle et lance sa propre redirection vers Cognito, en concurrence
    // avec le vrai logout. Selon le timing, soit ce faux départ "gagne" la
    // course (le vrai /logout n'a jamais lieu → session Cognito toujours
    // active → SSO silencieux → reconnexion automatique via /callback),
    // soit il empoisonne juste le verrou anti-boucle (écran d'erreur au
    // lieu de l'écran de connexion) — bug réel constaté le 2026-08-07,
    // reproduit et confirmé par trace de navigation en navigateur réel.
    // window.location.assign() ci-dessous va de toute façon détruire tout
    // l'état React dans l'instant qui suit — setUser(null) n'apporte rien.
    cognitoLogout();
  }

  const value: AuthContextValue = {
    user,
    isLoading,
    login: redirectToLogin,
    logout,
    handleCallback,
    refreshUser: loadCurrentUser,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error("useAuth doit être utilisé à l'intérieur d'un <AuthProvider>.");
  }
  return ctx;
}
