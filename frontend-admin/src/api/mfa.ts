// Miroir des routes self-service MFA de backend/tenders_api/handler.py
// (module 13, sur son propre compte uniquement — voir auth.py::associate_mfa/verify_mfa).
import { apiRequest } from "./client";

export function setupMfa(): Promise<{ secret_code: string }> {
  return apiRequest("/me/mfa/setup", { method: "POST" });
}

export function verifyMfa(code: string): Promise<{ status: string }> {
  return apiRequest("/me/mfa/verify", { method: "POST", body: { code } });
}
