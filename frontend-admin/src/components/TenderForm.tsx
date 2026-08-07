import { useEffect, useState, type FormEvent } from "react";

import { listCategories, listCountries, listOrganizations } from "../api/referenceData";
import type { TenderInput } from "../api/tenders";
import type { Category, Country, Organization, ProcedureType, ProcurementType, Sector, Tender } from "../types";

interface TenderFormProps {
  initialValue?: Tender;
  onSubmit: (input: TenderInput) => Promise<void>;
  submitLabel: string;
}

const SECTORS: Sector[] = ["PUBLIC", "PRIVATE"];
const PROCUREMENT_TYPES: ProcurementType[] = ["TRAVAUX", "FOURNITURES", "SERVICES", "PRESTATIONS_INTELLECTUELLES"];
const PROCEDURE_TYPES: ProcedureType[] = ["OUVERT", "RESTREINT", "GRE_A_GRE", "CONSULTATION", "CONCOURS"];

function toDatetimeLocal(iso: string | undefined): string {
  if (!iso) return "";
  const date = new Date(iso);
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}`;
}

function fromDatetimeLocal(value: string): string {
  return value ? new Date(value).toISOString() : "";
}

function buildInitialState(initialValue?: Tender): TenderInput {
  return {
    reference_number: initialValue?.reference_number ?? "",
    title: initialValue?.title ?? "",
    description: initialValue?.description ?? "",
    sector: initialValue?.sector ?? "PUBLIC",
    organization_id: initialValue?.organization_id ?? "",
    country_id: initialValue?.country_id ?? "",
    category_ids: initialValue?.category_ids ?? [],
    procurement_type: initialValue?.procurement_type ?? undefined,
    procedure_type: initialValue?.procedure_type ?? undefined,
    location_region: initialValue?.location_region ?? "",
    location_city: initialValue?.location_city ?? "",
    estimated_budget: initialValue?.estimated_budget ?? "",
    currency: initialValue?.currency ?? "XOF",
    eligibility_criteria: initialValue?.eligibility_criteria ?? "",
    required_documents: initialValue?.required_documents ?? "",
    contact_name: initialValue?.contact_name ?? "",
    contact_role: initialValue?.contact_role ?? "",
    contact_email: initialValue?.contact_email ?? "",
    contact_phone: initialValue?.contact_phone ?? "",
    source_name: initialValue?.source_name ?? "",
    source_url: initialValue?.source_url ?? "",
  };
}

export function TenderForm({ initialValue, onSubmit, submitLabel }: TenderFormProps) {
  const [countries, setCountries] = useState<Country[]>([]);
  const [categories, setCategories] = useState<Category[]>([]);
  const [organizations, setOrganizations] = useState<Organization[]>([]);
  const [form, setForm] = useState<TenderInput>(buildInitialState(initialValue));
  const [deadline, setDeadline] = useState(toDatetimeLocal(initialValue?.submission_deadline));
  const [primaryCategoryId, setPrimaryCategoryId] = useState<string>("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    void listCountries().then((res) => setCountries(res.items));
    void listCategories().then((res) => setCategories(res.items.filter((c) => c.is_active)));
    void listOrganizations().then((res) => setOrganizations(res.items.filter((o) => o.is_active)));
  }, []);

  function updateField<K extends keyof TenderInput>(field: K, value: TenderInput[K]): void {
    setForm((prev) => ({ ...prev, [field]: value }));
  }

  function toggleCategory(categoryId: string): void {
    const current = form.category_ids ?? [];
    const next = current.includes(categoryId)
      ? current.filter((id) => id !== categoryId)
      : [...current, categoryId];
    updateField("category_ids", next);
    if (!next.includes(primaryCategoryId)) {
      setPrimaryCategoryId(next[0] ?? "");
    }
  }

  async function handleSubmit(event: FormEvent): Promise<void> {
    event.preventDefault();
    setBusy(true);
    try {
      await onSubmit({
        ...form,
        submission_deadline: fromDatetimeLocal(deadline),
        primary_category_id: primaryCategoryId || undefined,
      });
    } finally {
      setBusy(false);
    }
  }

  return (
    <form className="tender-form" onSubmit={handleSubmit}>
      <label>
        Référence
        <input value={form.reference_number ?? ""} onChange={(e) => updateField("reference_number", e.target.value)} />
      </label>

      <label>
        Titre *
        <input required value={form.title ?? ""} onChange={(e) => updateField("title", e.target.value)} />
      </label>

      <label>
        Description *
        <textarea
          required
          rows={4}
          value={form.description ?? ""}
          onChange={(e) => updateField("description", e.target.value)}
        />
      </label>

      <div className="form-row">
        <label>
          Secteur *
          <select required value={form.sector ?? ""} onChange={(e) => updateField("sector", e.target.value as Sector)}>
            {SECTORS.map((s) => (
              <option key={s} value={s}>
                {s === "PUBLIC" ? "Public" : "Privé"}
              </option>
            ))}
          </select>
        </label>

        <label>
          Organisation *
          <select
            required
            value={form.organization_id ?? ""}
            onChange={(e) => updateField("organization_id", e.target.value)}
          >
            <option value="" disabled>
              Choisir…
            </option>
            {organizations.map((org) => (
              <option key={org.id} value={org.id}>
                {org.name}
              </option>
            ))}
          </select>
        </label>

        <label>
          Pays *
          <select required value={form.country_id ?? ""} onChange={(e) => updateField("country_id", e.target.value)}>
            <option value="" disabled>
              Choisir…
            </option>
            {countries.map((country) => (
              <option key={country.id} value={country.id}>
                {country.name}
              </option>
            ))}
          </select>
        </label>
      </div>

      <fieldset>
        <legend>Catégories</legend>
        {categories.map((category) => (
          <label key={category.id} className="checkbox-label">
            <input
              type="checkbox"
              checked={(form.category_ids ?? []).includes(category.id)}
              onChange={() => toggleCategory(category.id)}
            />
            {category.name}
          </label>
        ))}
        {(form.category_ids ?? []).length > 1 && (
          <label>
            Catégorie principale
            <select value={primaryCategoryId} onChange={(e) => setPrimaryCategoryId(e.target.value)}>
              {(form.category_ids ?? []).map((id) => (
                <option key={id} value={id}>
                  {categories.find((c) => c.id === id)?.name ?? id}
                </option>
              ))}
            </select>
          </label>
        )}
      </fieldset>

      <div className="form-row">
        <label>
          Type de marché
          <select
            value={form.procurement_type ?? ""}
            onChange={(e) => updateField("procurement_type", (e.target.value || undefined) as ProcurementType)}
          >
            <option value="">—</option>
            {PROCUREMENT_TYPES.map((t) => (
              <option key={t} value={t}>
                {t}
              </option>
            ))}
          </select>
        </label>

        <label>
          Type de procédure
          <select
            value={form.procedure_type ?? ""}
            onChange={(e) => updateField("procedure_type", (e.target.value || undefined) as ProcedureType)}
          >
            <option value="">—</option>
            {PROCEDURE_TYPES.map((t) => (
              <option key={t} value={t}>
                {t}
              </option>
            ))}
          </select>
        </label>
      </div>

      <div className="form-row">
        <label>
          Région
          <input value={form.location_region ?? ""} onChange={(e) => updateField("location_region", e.target.value)} />
        </label>
        <label>
          Ville
          <input value={form.location_city ?? ""} onChange={(e) => updateField("location_city", e.target.value)} />
        </label>
      </div>

      <div className="form-row">
        <label>
          Budget estimé
          <input
            type="number"
            value={form.estimated_budget ?? ""}
            onChange={(e) => updateField("estimated_budget", e.target.value)}
          />
        </label>
        <label>
          Devise
          <input value={form.currency ?? "XOF"} onChange={(e) => updateField("currency", e.target.value)} />
        </label>
        <label>
          Date limite de dépôt *
          <input type="datetime-local" required value={deadline} onChange={(e) => setDeadline(e.target.value)} />
        </label>
      </div>

      <label>
        Critères d'éligibilité
        <textarea
          rows={2}
          value={form.eligibility_criteria ?? ""}
          onChange={(e) => updateField("eligibility_criteria", e.target.value)}
        />
      </label>

      <label>
        Pièces à fournir
        <textarea
          rows={2}
          value={form.required_documents ?? ""}
          onChange={(e) => updateField("required_documents", e.target.value)}
        />
      </label>

      <fieldset>
        <legend>Contact / point focal</legend>
        <div className="form-row">
          <label>
            Nom
            <input value={form.contact_name ?? ""} onChange={(e) => updateField("contact_name", e.target.value)} />
          </label>
          <label>
            Fonction
            <input value={form.contact_role ?? ""} onChange={(e) => updateField("contact_role", e.target.value)} />
          </label>
        </div>
        <div className="form-row">
          <label>
            Email
            <input
              type="email"
              value={form.contact_email ?? ""}
              onChange={(e) => updateField("contact_email", e.target.value)}
            />
          </label>
          <label>
            Téléphone
            <input value={form.contact_phone ?? ""} onChange={(e) => updateField("contact_phone", e.target.value)} />
          </label>
        </div>
      </fieldset>

      <div className="form-row">
        <label>
          Source officielle
          <input value={form.source_name ?? ""} onChange={(e) => updateField("source_name", e.target.value)} />
        </label>
        <label>
          Lien source
          <input value={form.source_url ?? ""} onChange={(e) => updateField("source_url", e.target.value)} />
        </label>
      </div>

      <button type="submit" disabled={busy}>
        {submitLabel}
      </button>
    </form>
  );
}
