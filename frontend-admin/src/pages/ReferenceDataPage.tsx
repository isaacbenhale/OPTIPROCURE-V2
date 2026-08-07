import { useEffect, useState } from "react";

import {
  createCategory,
  createCountry,
  createDiffusionPartnership,
  createOrganization,
  listCategories,
  listCountries,
  listDiffusionPartnerships,
  listOrganizations,
  updateCategory,
  updateDiffusionPartnership,
  updateOrganization,
  type CategoryInput,
  type DiffusionPartnershipInput,
  type OrganizationInput,
} from "../api/referenceData";
import { ErrorBanner } from "../components/ErrorBanner";
import type { Category, Country, DiffusionPartnership, Organization } from "../types";

type Tab = "countries" | "categories" | "organizations" | "partnerships";

const TABS: { key: Tab; label: string }[] = [
  { key: "countries", label: "Pays" },
  { key: "categories", label: "Catégories" },
  { key: "organizations", label: "Organisations" },
  { key: "partnerships", label: "Partenariats de diffusion" },
];

export function ReferenceDataPage() {
  const [tab, setTab] = useState<Tab>("countries");

  return (
    <div>
      <div className="page-header">
        <h1>Référentiels</h1>
      </div>
      <p className="muted">
        Gestion des pays, catégories, organisations et partenariats de diffusion. Écriture réservée à ADMIN
        avec MFA activé.
      </p>

      <div className="tabs">
        {TABS.map((t) => (
          <button
            key={t.key}
            type="button"
            className={tab === t.key ? "" : "button-secondary"}
            onClick={() => setTab(t.key)}
          >
            {t.label}
          </button>
        ))}
      </div>

      {tab === "countries" && <CountriesTab />}
      {tab === "categories" && <CategoriesTab />}
      {tab === "organizations" && <OrganizationsTab />}
      {tab === "partnerships" && <PartnershipsTab />}
    </div>
  );
}

// --- Pays --------------------------------------------------------------

function CountriesTab() {
  const [countries, setCountries] = useState<Country[]>([]);
  const [isoCode, setIsoCode] = useState("");
  const [name, setName] = useState("");
  const [error, setError] = useState<unknown>(null);
  const [saving, setSaving] = useState(false);

  function reload() {
    void listCountries().then((res) => setCountries(res.items));
  }

  useEffect(reload, []);

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setSaving(true);
    createCountry({ iso_code: isoCode.toUpperCase(), name })
      .then(() => {
        setIsoCode("");
        setName("");
        reload();
      })
      .catch((err: unknown) => setError(err))
      .finally(() => setSaving(false));
  }

  return (
    <div>
      <form className="tender-form" onSubmit={handleSubmit}>
        <ErrorBanner error={error} />
        <div className="form-row">
          <label>
            Code ISO (2 lettres) *
            <input
              required
              maxLength={2}
              pattern="[A-Za-z]{2}"
              value={isoCode}
              onChange={(e) => setIsoCode(e.target.value)}
              placeholder="TG"
            />
          </label>
          <label>
            Nom *
            <input required value={name} onChange={(e) => setName(e.target.value)} placeholder="Togo" />
          </label>
        </div>
        <button type="submit" disabled={saving}>
          {saving ? "Ajout…" : "+ Ajouter un pays"}
        </button>
      </form>

      <table className="tenders-table">
        <thead>
          <tr>
            <th>Code</th>
            <th>Nom</th>
          </tr>
        </thead>
        <tbody>
          {countries.map((c) => (
            <tr key={c.id}>
              <td>{c.iso_code}</td>
              <td>{c.name}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// --- Catégories ----------------------------------------------------------

function CategoriesTab() {
  const [categories, setCategories] = useState<Category[]>([]);
  const [editing, setEditing] = useState<Category | null>(null);
  const [form, setForm] = useState<CategoryInput>({ name: "", slug: "", parent_id: null, is_active: true });
  const [error, setError] = useState<unknown>(null);
  const [saving, setSaving] = useState(false);

  function reload() {
    void listCategories().then((res) => setCategories(res.items));
  }

  useEffect(reload, []);

  function startEdit(category: Category) {
    setEditing(category);
    setForm({
      name: category.name,
      slug: category.slug,
      parent_id: category.parent_id,
      is_active: category.is_active,
    });
  }

  function resetForm() {
    setEditing(null);
    setForm({ name: "", slug: "", parent_id: null, is_active: true });
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setSaving(true);
    const request = editing ? updateCategory(editing.id, form) : createCategory(form);
    request
      .then(() => {
        resetForm();
        reload();
      })
      .catch((err: unknown) => setError(err))
      .finally(() => setSaving(false));
  }

  return (
    <div>
      <form className="tender-form" onSubmit={handleSubmit}>
        <ErrorBanner error={error} />
        <div className="form-row">
          <label>
            Nom *
            <input
              required
              value={form.name ?? ""}
              onChange={(e) => setForm({ ...form, name: e.target.value })}
            />
          </label>
          <label>
            Slug *
            <input
              required
              value={form.slug ?? ""}
              onChange={(e) => setForm({ ...form, slug: e.target.value })}
              placeholder="travaux-publics"
            />
          </label>
        </div>
        <div className="form-row">
          <label>
            Catégorie parente
            <select
              value={form.parent_id ?? ""}
              onChange={(e) => setForm({ ...form, parent_id: e.target.value || null })}
            >
              <option value="">— Aucune (catégorie racine) —</option>
              {categories
                .filter((c) => c.id !== editing?.id)
                .map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.name}
                  </option>
                ))}
            </select>
          </label>
          <label className="checkbox-label">
            <input
              type="checkbox"
              checked={form.is_active ?? true}
              onChange={(e) => setForm({ ...form, is_active: e.target.checked })}
            />
            Active
          </label>
        </div>
        <div className="workflow-actions-buttons">
          <button type="submit" disabled={saving}>
            {saving ? "Enregistrement…" : editing ? "Enregistrer" : "+ Ajouter une catégorie"}
          </button>
          {editing && (
            <button type="button" onClick={resetForm}>
              Annuler
            </button>
          )}
        </div>
      </form>

      <table className="tenders-table">
        <thead>
          <tr>
            <th>Nom</th>
            <th>Slug</th>
            <th>Parent</th>
            <th>Statut</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          {categories.map((c) => (
            <tr key={c.id}>
              <td>{c.name}</td>
              <td>{c.slug}</td>
              <td>{categories.find((p) => p.id === c.parent_id)?.name ?? "—"}</td>
              <td>{c.is_active ? "Active" : "Inactive"}</td>
              <td>
                <button type="button" onClick={() => startEdit(c)}>
                  Modifier
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// --- Organisations ---------------------------------------------------------

const ORG_TYPES = ["PUBLIC_BODY", "PRIVATE_PARTNER", "DONOR", "AGGREGATOR"] as const;

function OrganizationsTab() {
  const [organizations, setOrganizations] = useState<Organization[]>([]);
  const [countries, setCountries] = useState<Country[]>([]);
  const [editing, setEditing] = useState<Organization | null>(null);
  const [form, setForm] = useState<OrganizationInput>({
    name: "",
    org_type: "PUBLIC_BODY",
    country_id: null,
    website: "",
    contact_email: "",
    is_active: true,
  });
  const [error, setError] = useState<unknown>(null);
  const [saving, setSaving] = useState(false);

  function reload() {
    void listOrganizations().then((res) => setOrganizations(res.items));
  }

  useEffect(() => {
    reload();
    void listCountries().then((res) => setCountries(res.items));
  }, []);

  function startEdit(org: Organization) {
    setEditing(org);
    setForm({
      name: org.name,
      org_type: org.org_type,
      country_id: org.country_id,
      website: org.website ?? "",
      contact_email: org.contact_email ?? "",
      is_active: org.is_active,
    });
  }

  function resetForm() {
    setEditing(null);
    setForm({ name: "", org_type: "PUBLIC_BODY", country_id: null, website: "", contact_email: "", is_active: true });
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setSaving(true);
    const request = editing ? updateOrganization(editing.id, form) : createOrganization(form);
    request
      .then(() => {
        resetForm();
        reload();
      })
      .catch((err: unknown) => setError(err))
      .finally(() => setSaving(false));
  }

  return (
    <div>
      <form className="tender-form" onSubmit={handleSubmit}>
        <ErrorBanner error={error} />
        <div className="form-row">
          <label>
            Nom *
            <input
              required
              value={form.name ?? ""}
              onChange={(e) => setForm({ ...form, name: e.target.value })}
            />
          </label>
          <label>
            Type *
            <select
              required
              value={form.org_type ?? "PUBLIC_BODY"}
              onChange={(e) => setForm({ ...form, org_type: e.target.value as OrganizationInput["org_type"] })}
            >
              {ORG_TYPES.map((t) => (
                <option key={t} value={t}>
                  {t}
                </option>
              ))}
            </select>
          </label>
          <label>
            Pays
            <select
              value={form.country_id ?? ""}
              onChange={(e) => setForm({ ...form, country_id: e.target.value || null })}
            >
              <option value="">— Aucun —</option>
              {countries.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.name}
                </option>
              ))}
            </select>
          </label>
        </div>
        <div className="form-row">
          <label>
            Site web
            <input
              type="url"
              value={form.website ?? ""}
              onChange={(e) => setForm({ ...form, website: e.target.value })}
            />
          </label>
          <label>
            Email de contact
            <input
              type="email"
              value={form.contact_email ?? ""}
              onChange={(e) => setForm({ ...form, contact_email: e.target.value })}
            />
          </label>
          <label className="checkbox-label">
            <input
              type="checkbox"
              checked={form.is_active ?? true}
              onChange={(e) => setForm({ ...form, is_active: e.target.checked })}
            />
            Active
          </label>
        </div>
        <div className="workflow-actions-buttons">
          <button type="submit" disabled={saving}>
            {saving ? "Enregistrement…" : editing ? "Enregistrer" : "+ Ajouter une organisation"}
          </button>
          {editing && (
            <button type="button" onClick={resetForm}>
              Annuler
            </button>
          )}
        </div>
      </form>

      <table className="tenders-table">
        <thead>
          <tr>
            <th>Nom</th>
            <th>Type</th>
            <th>Pays</th>
            <th>Statut</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          {organizations.map((o) => (
            <tr key={o.id}>
              <td>{o.name}</td>
              <td>{o.org_type}</td>
              <td>{countries.find((c) => c.id === o.country_id)?.name ?? "—"}</td>
              <td>{o.is_active ? "Active" : "Inactive"}</td>
              <td>
                <button type="button" onClick={() => startEdit(o)}>
                  Modifier
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// --- Partenariats de diffusion ----------------------------------------------

const PARTNERSHIP_STATUSES = ["ACTIVE", "SUSPENDED", "EXPIRED", "TERMINATED"] as const;

function PartnershipsTab() {
  const [partnerships, setPartnerships] = useState<DiffusionPartnership[]>([]);
  const [organizations, setOrganizations] = useState<Organization[]>([]);
  const [editing, setEditing] = useState<DiffusionPartnership | null>(null);
  const [form, setForm] = useState<DiffusionPartnershipInput>({
    organization_id: "",
    convention_reference: "",
    signed_at: "",
    valid_from: "",
    valid_until: "",
    status: "ACTIVE",
    notes: "",
  });
  const [error, setError] = useState<unknown>(null);
  const [saving, setSaving] = useState(false);

  function reload() {
    void listDiffusionPartnerships().then((res) => setPartnerships(res.items));
  }

  useEffect(() => {
    reload();
    void listOrganizations().then((res) => setOrganizations(res.items));
  }, []);

  function startEdit(p: DiffusionPartnership) {
    setEditing(p);
    setForm({
      organization_id: p.organization_id,
      convention_reference: p.convention_reference,
      signed_at: p.signed_at?.slice(0, 10),
      valid_from: p.valid_from?.slice(0, 10),
      valid_until: p.valid_until?.slice(0, 10) ?? "",
      status: p.status,
      notes: p.notes ?? "",
    });
  }

  function resetForm() {
    setEditing(null);
    setForm({
      organization_id: "",
      convention_reference: "",
      signed_at: "",
      valid_from: "",
      valid_until: "",
      status: "ACTIVE",
      notes: "",
    });
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setSaving(true);
    const payload = { ...form, valid_until: form.valid_until || null };
    const request = editing ? updateDiffusionPartnership(editing.id, payload) : createDiffusionPartnership(payload);
    request
      .then(() => {
        resetForm();
        reload();
      })
      .catch((err: unknown) => setError(err))
      .finally(() => setSaving(false));
  }

  return (
    <div>
      {organizations.length === 0 && (
        <p className="muted">Crée d'abord au moins une organisation dans l'onglet « Organisations ».</p>
      )}
      <form className="tender-form" onSubmit={handleSubmit}>
        <ErrorBanner error={error} />
        <div className="form-row">
          <label>
            Organisation *
            <select
              required
              value={form.organization_id ?? ""}
              onChange={(e) => setForm({ ...form, organization_id: e.target.value })}
            >
              <option value="">Choisir…</option>
              {organizations.map((o) => (
                <option key={o.id} value={o.id}>
                  {o.name}
                </option>
              ))}
            </select>
          </label>
          <label>
            Référence de convention *
            <input
              required
              value={form.convention_reference ?? ""}
              onChange={(e) => setForm({ ...form, convention_reference: e.target.value })}
            />
          </label>
          <label>
            Statut
            <select
              value={form.status ?? "ACTIVE"}
              onChange={(e) => setForm({ ...form, status: e.target.value as DiffusionPartnershipInput["status"] })}
            >
              {PARTNERSHIP_STATUSES.map((s) => (
                <option key={s} value={s}>
                  {s}
                </option>
              ))}
            </select>
          </label>
        </div>
        <div className="form-row">
          <label>
            Signée le *
            <input
              required
              type="date"
              value={form.signed_at ?? ""}
              onChange={(e) => setForm({ ...form, signed_at: e.target.value })}
            />
          </label>
          <label>
            Valide à partir du *
            <input
              required
              type="date"
              value={form.valid_from ?? ""}
              onChange={(e) => setForm({ ...form, valid_from: e.target.value })}
            />
          </label>
          <label>
            Valide jusqu'au
            <input
              type="date"
              value={form.valid_until ?? ""}
              onChange={(e) => setForm({ ...form, valid_until: e.target.value })}
            />
          </label>
        </div>
        <label>
          Notes
          <textarea
            rows={2}
            value={form.notes ?? ""}
            onChange={(e) => setForm({ ...form, notes: e.target.value })}
          />
        </label>
        <div className="workflow-actions-buttons">
          <button type="submit" disabled={saving}>
            {saving ? "Enregistrement…" : editing ? "Enregistrer" : "+ Ajouter un partenariat"}
          </button>
          {editing && (
            <button type="button" onClick={resetForm}>
              Annuler
            </button>
          )}
        </div>
      </form>

      <table className="tenders-table">
        <thead>
          <tr>
            <th>Organisation</th>
            <th>Convention</th>
            <th>Statut</th>
            <th>Validité</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          {partnerships.map((p) => (
            <tr key={p.id}>
              <td>{organizations.find((o) => o.id === p.organization_id)?.name ?? "—"}</td>
              <td>{p.convention_reference}</td>
              <td>{p.status}</td>
              <td>
                {p.valid_from} → {p.valid_until ?? "∞"}
              </td>
              <td>
                <button type="button" onClick={() => startEdit(p)}>
                  Modifier
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
