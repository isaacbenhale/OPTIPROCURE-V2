import { useEffect, useState } from "react";
import QRCode from "qrcode";

import { setupMfa, verifyMfa } from "../api/mfa";
import { useAuth } from "../auth/AuthContext";
import { ErrorBanner } from "../components/ErrorBanner";

// Self-service MFA (module 13) — reproduit en UI ce qui a été fait
// manuellement via script boto3 pour test.admin dans ce projet
// (associate_software_token -> saisie du code -> verify_software_token).
// QR code ET texte brut proposés ensemble (décision révisée le 2026-08-07,
// tasks/13-gestion-comptes-internes.md §4) — le QR est généré entièrement
// côté client (lib qrcode, pas d'appel réseau) : le secret TOTP ne doit
// jamais transiter par un service tiers de génération de QR.
const ISSUER = "OptiProcure";

export function SecurityPage() {
  const { user, refreshUser } = useAuth();
  const [secretCode, setSecretCode] = useState<string | null>(null);
  const [qrDataUrl, setQrDataUrl] = useState<string | null>(null);
  const [code, setCode] = useState("");
  const [error, setError] = useState<unknown>(null);
  const [busy, setBusy] = useState(false);
  const [justEnabled, setJustEnabled] = useState(false);

  useEffect(() => {
    if (!secretCode || !user) {
      setQrDataUrl(null);
      return;
    }
    const label = encodeURIComponent(`${ISSUER}:${user.email}`);
    const otpauthUri = `otpauth://totp/${label}?secret=${secretCode}&issuer=${encodeURIComponent(ISSUER)}`;
    QRCode.toDataURL(otpauthUri)
      .then(setQrDataUrl)
      .catch(() => setQrDataUrl(null)); // dégradation silencieuse : le texte brut reste disponible
  }, [secretCode, user]);

  function handleSetup() {
    setError(null);
    setBusy(true);
    setupMfa()
      .then((res) => setSecretCode(res.secret_code))
      .catch((err: unknown) => setError(err))
      .finally(() => setBusy(false));
  }

  function handleVerify(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setBusy(true);
    verifyMfa(code)
      .then(() => {
        setJustEnabled(true);
        setSecretCode(null);
        setCode("");
        return refreshUser();
      })
      .catch((err: unknown) => setError(err))
      .finally(() => setBusy(false));
  }

  const mfaEnabled = justEnabled || user?.mfa_enabled;

  return (
    <div>
      <div className="page-header">
        <h1>Sécurité</h1>
      </div>

      <ErrorBanner error={error} />

      <div className="tender-form">
        <p>
          Authentification à deux facteurs (MFA) :{" "}
          {mfaEnabled ? <strong>activée</strong> : <strong>non activée</strong>}
        </p>

        {!mfaEnabled && !secretCode && (
          <button type="button" onClick={handleSetup} disabled={busy}>
            {busy ? "Génération…" : "Configurer le MFA"}
          </button>
        )}

        {secretCode && (
          <form onSubmit={handleVerify}>
            <p>
              Scanne ce code avec une application d'authentification (Google Authenticator, Authy…), ou
              saisis la clé manuellement si tu ne peux pas scanner :
            </p>
            {qrDataUrl && (
              <p>
                <img src={qrDataUrl} alt="QR code d'activation du MFA" width={200} height={200} />
              </p>
            )}
            <p>
              <code>{secretCode}</code>
            </p>
            <label>
              Code de vérification
              <input
                required
                inputMode="numeric"
                pattern="[0-9]{6}"
                maxLength={6}
                value={code}
                onChange={(e) => setCode(e.target.value)}
                placeholder="123456"
              />
            </label>
            <div className="workflow-actions-buttons">
              <button type="submit" disabled={busy || code.trim().length !== 6}>
                {busy ? "Vérification…" : "Vérifier et activer"}
              </button>
              <button
                type="button"
                onClick={() => {
                  setSecretCode(null);
                  setCode("");
                }}
              >
                Annuler
              </button>
            </div>
          </form>
        )}

        {mfaEnabled && <p className="muted">Le MFA est actif sur ce compte.</p>}
      </div>
    </div>
  );
}
