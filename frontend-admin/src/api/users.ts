// Miroir des routes de backend/users_api/handler.py (module 13). Même API
// Gateway que tenders_api/reference_data_api (aws_apigatewayv2_api.backoffice
// unique). Écriture réservée à ADMIN + MFA côté Lambda.
import { apiRequest } from "./client";
import type { Account, Role } from "../types";

export function listAccounts(): Promise<{ items: Account[] }> {
  return apiRequest("/users");
}

export function createAccount(input: { email: string; groups: Role[] }): Promise<Account> {
  return apiRequest("/users", { method: "POST", body: input });
}

export function updateGroups(cognitoSub: string, groups: Role[]): Promise<Account> {
  return apiRequest(`/users/${cognitoSub}/groups`, { method: "PUT", body: { groups } });
}

export function activateAccount(cognitoSub: string): Promise<{ cognito_sub: string; is_active: boolean }> {
  return apiRequest(`/users/${cognitoSub}/activate`, { method: "POST" });
}

export function deactivateAccount(cognitoSub: string): Promise<{ cognito_sub: string; is_active: boolean }> {
  return apiRequest(`/users/${cognitoSub}/deactivate`, { method: "POST" });
}

export function deleteAccount(cognitoSub: string): Promise<{ cognito_sub: string; deleted: boolean }> {
  return apiRequest(`/users/${cognitoSub}`, { method: "DELETE" });
}
