import type { ReactNode } from "react";

interface StatCardProps {
  label: string;
  value: ReactNode;
  hint?: string;
  icon: ReactNode;
  tone?: "brand" | "success" | "purple";
}

// Carte de statistique réutilisable — toujours alimentée par de vraies
// données calculées côté page (jamais un chiffre décoratif/fictif).
export function StatCard({ label, value, hint, icon, tone = "brand" }: StatCardProps) {
  return (
    <div className="stat-card">
      <div className="stat-card-top">
        <span className="stat-card-label">{label}</span>
        <span className={`stat-card-icon stat-card-icon-${tone}`}>{icon}</span>
      </div>
      <div className="stat-card-value">{value}</div>
      {hint && <div className="stat-card-hint">{hint}</div>}
    </div>
  );
}
