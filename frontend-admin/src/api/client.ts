// Wrapper fetch : injection automatique de l'access token (jamais l'id_token
// — backend/tenders_api/auth.py l'exige explicitement), refresh silencieux
// avant expiration, parsing uniforme de l'enveloppe d'erreur {error:{code,
// message,fields}} produite par handler.py (tenders_api et reference_data_api).
import { clearTokens, loadTokens, refreshTokens } from "../auth/cognito";
import type { ApiErrorBody } from "../types";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL;
const REFRESH_MARGIN_MS = 60_000; // rafraîchir 1 min avant l'expiration (jetons de 15 min)

export class ApiError extends Error {
  status: number;
  code: string;
  fields: Record<string, unknown>;

  constructor(status: number, body: ApiErrorBody["error"]) {
    super(body.message);
    this.status = status;
    this.code = body.code;
    this.fields = body.fields;
  }
}

async function getValidAccessToken(): Promise<string> {
  const tokens = loadTokens();
  if (!tokens) {
    throw new ApiError(401, { code: "UNAUTHORIZED", message: "Non connecté.", fields: {} });
  }
  if (Date.now() > tokens.expires_at - REFRESH_MARGIN_MS) {
    const refreshed = await refreshTokens(tokens.refresh_token);
    return refreshed.access_token;
  }
  return tokens.access_token;
}

interface RequestOptions {
  method?: "GET" | "POST" | "PUT" | "DELETE";
  body?: unknown;
  query?: Record<string, string | undefined>;
}

export async function apiRequest<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const token = await getValidAccessToken();

  const url = new URL(API_BASE_URL + path);
  for (const [key, value] of Object.entries(options.query ?? {})) {
    if (value !== undefined) url.searchParams.set(key, value);
  }

  const response = await fetch(url.toString(), {
    method: options.method ?? "GET",
    headers: {
      Authorization: `Bearer ${token}`,
      ...(options.body !== undefined ? { "Content-Type": "application/json" } : {}),
    },
    body: options.body !== undefined ? JSON.stringify(options.body) : undefined,
  });

  if (response.status === 401) {
    clearTokens();
    window.location.assign("/login");
    throw new ApiError(401, { code: "UNAUTHORIZED", message: "Session expirée, reconnexion nécessaire.", fields: {} });
  }

  const data = await response.json().catch(() => ({}) as unknown);

  if (!response.ok) {
    const body = (data as Partial<ApiErrorBody>).error ?? {
      code: "INTERNAL_ERROR" as const,
      message: "Erreur inattendue.",
      fields: {},
    };
    throw new ApiError(response.status, body);
  }

  return data as T;
}
