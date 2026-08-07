// Flux Authorization Code + PKCE contre le Hosted UI Cognito (cognito.tf :
// client SPA public, generate_secret = false). Jetons en sessionStorage
// (pas localStorage) — choix délibéré : un back-office interne n'a pas
// besoin qu'une session survive à la fermeture de l'onglet, et ça réduit
// la fenêtre d'exposition en cas de XSS.
import { generateCodeChallenge, generateCodeVerifier, generateState } from "./pkce";

const DOMAIN = import.meta.env.VITE_COGNITO_DOMAIN;
const CLIENT_ID = import.meta.env.VITE_COGNITO_CLIENT_ID;
const REDIRECT_URI = import.meta.env.VITE_REDIRECT_URI;
const LOGOUT_URI = import.meta.env.VITE_LOGOUT_URI;

const CODE_VERIFIER_KEY = "optiprocure_code_verifier";
const STATE_KEY = "optiprocure_oauth_state";
const TOKENS_KEY = "optiprocure_tokens";

export interface Tokens {
  access_token: string;
  id_token: string;
  refresh_token: string;
  expires_at: number; // epoch ms
}

interface TokenResponse {
  access_token: string;
  id_token: string;
  refresh_token?: string;
  expires_in: number;
}

function toTokens(data: TokenResponse, fallbackRefreshToken?: string): Tokens {
  const refreshToken = data.refresh_token ?? fallbackRefreshToken;
  if (!refreshToken) {
    throw new Error("Réponse Cognito sans refresh_token.");
  }
  return {
    access_token: data.access_token,
    id_token: data.id_token,
    refresh_token: refreshToken,
    expires_at: Date.now() + data.expires_in * 1000,
  };
}

export async function redirectToLogin(): Promise<void> {
  const verifier = generateCodeVerifier();
  const challenge = await generateCodeChallenge(verifier);
  const state = generateState();
  sessionStorage.setItem(CODE_VERIFIER_KEY, verifier);
  sessionStorage.setItem(STATE_KEY, state);

  const url = new URL(`${DOMAIN}/oauth2/authorize`);
  url.searchParams.set("response_type", "code");
  url.searchParams.set("client_id", CLIENT_ID);
  url.searchParams.set("redirect_uri", REDIRECT_URI);
  // openid : requis pour l'émission d'un id_token (non exploité côté
  // frontend, mais Cognito l'exige comme scope de base du flux OIDC).
  // aws.cognito.signin.user.admin : requis pour que l'access token puisse
  // ensuite appeler cognito-idp:GetUser côté backend (voir cognito.tf).
  // Ni "email" ni "profile" ne sont demandés : le backend récupère déjà
  // email/nom via GetUser (auth.py::fetch_cognito_user_info), le frontend
  // ne lit jamais les claims de l'id_token — et empiriquement, Cognito
  // rejette (invalid_scope) la combinaison des 4 scopes ensemble alors que
  // 3 quelconques passent (bug/limite Hosted UI constatée le 2026-08-07).
  url.searchParams.set("scope", "openid aws.cognito.signin.user.admin");
  url.searchParams.set("code_challenge_method", "S256");
  url.searchParams.set("code_challenge", challenge);
  url.searchParams.set("state", state);
  window.location.assign(url.toString());
}

export async function exchangeCodeForTokens(code: string, state: string): Promise<Tokens> {
  const expectedState = sessionStorage.getItem(STATE_KEY);
  const verifier = sessionStorage.getItem(CODE_VERIFIER_KEY);
  sessionStorage.removeItem(STATE_KEY);
  sessionStorage.removeItem(CODE_VERIFIER_KEY);

  if (!verifier || !expectedState || state !== expectedState) {
    throw new Error("État OAuth invalide (CSRF ou session expirée) — reconnecte-toi.");
  }

  const body = new URLSearchParams({
    grant_type: "authorization_code",
    client_id: CLIENT_ID,
    code,
    redirect_uri: REDIRECT_URI,
    code_verifier: verifier,
  });

  const response = await fetch(`${DOMAIN}/oauth2/token`, {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body,
  });
  if (!response.ok) {
    throw new Error("Échec de l'échange du code d'autorisation contre des jetons.");
  }
  const tokens = toTokens((await response.json()) as TokenResponse);
  storeTokens(tokens);
  return tokens;
}

export async function refreshTokens(refreshToken: string): Promise<Tokens> {
  const body = new URLSearchParams({
    grant_type: "refresh_token",
    client_id: CLIENT_ID,
    refresh_token: refreshToken,
  });
  const response = await fetch(`${DOMAIN}/oauth2/token`, {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body,
  });
  if (!response.ok) {
    throw new Error("Échec du rafraîchissement des jetons.");
  }
  // Cognito ne renvoie pas de nouveau refresh_token sur ce grant — on garde l'ancien.
  const tokens = toTokens((await response.json()) as TokenResponse, refreshToken);
  storeTokens(tokens);
  return tokens;
}

export function storeTokens(tokens: Tokens): void {
  sessionStorage.setItem(TOKENS_KEY, JSON.stringify(tokens));
}

export function loadTokens(): Tokens | null {
  const raw = sessionStorage.getItem(TOKENS_KEY);
  return raw ? (JSON.parse(raw) as Tokens) : null;
}

export function clearTokens(): void {
  sessionStorage.removeItem(TOKENS_KEY);
}

export function logout(): void {
  clearTokens();
  const url = new URL(`${DOMAIN}/logout`);
  url.searchParams.set("client_id", CLIENT_ID);
  url.searchParams.set("logout_uri", LOGOUT_URI);
  window.location.assign(url.toString());
}
