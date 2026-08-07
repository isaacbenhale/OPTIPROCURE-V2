import { createContext, useContext, useEffect, useState, type ReactNode } from "react";

import { apiRequest } from "../api/client";
import type { User } from "../types";
import { exchangeCodeForTokens, loadTokens, logout as cognitoLogout, redirectToLogin } from "./cognito";

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
  }

  function logout(): void {
    setUser(null);
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
