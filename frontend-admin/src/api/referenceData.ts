// Miroir des routes de backend/reference_data_api/handler.py (module 01).
// Lecture consommée par TenderForm pour peupler les listes déroulantes ;
// écriture consommée par ReferenceDataPage (gestion admin, ADMIN + MFA
// requis côté backend — voir reference_data.py::WRITE_ROLES/require_mfa).
import { apiRequest } from "./client";
import type { Category, Country, DiffusionPartnership, Organization } from "../types";

export function listCountries(): Promise<{ items: Country[] }> {
  return apiRequest("/countries");
}

export function createCountry(input: Pick<Country, "iso_code" | "name">): Promise<Country> {
  return apiRequest("/countries", { method: "POST", body: input });
}

export function listCategories(): Promise<{ items: Category[] }> {
  return apiRequest("/categories");
}

export type CategoryInput = Partial<Pick<Category, "parent_id" | "name" | "slug" | "is_active">>;

export function createCategory(input: CategoryInput): Promise<Category> {
  return apiRequest("/categories", { method: "POST", body: input });
}

export function updateCategory(id: string, input: CategoryInput): Promise<Category> {
  return apiRequest(`/categories/${id}`, { method: "PUT", body: input });
}

export function listOrganizations(): Promise<{ items: Organization[] }> {
  return apiRequest("/organizations");
}

export type OrganizationInput = Partial<
  Pick<Organization, "name" | "org_type" | "country_id" | "website" | "contact_email" | "is_active">
>;

export function createOrganization(input: OrganizationInput): Promise<Organization> {
  return apiRequest("/organizations", { method: "POST", body: input });
}

export function updateOrganization(id: string, input: OrganizationInput): Promise<Organization> {
  return apiRequest(`/organizations/${id}`, { method: "PUT", body: input });
}

export function listDiffusionPartnerships(): Promise<{ items: DiffusionPartnership[] }> {
  return apiRequest("/diffusion-partnerships");
}

export type DiffusionPartnershipInput = Partial<
  Pick<
    DiffusionPartnership,
    "organization_id" | "convention_reference" | "signed_at" | "valid_from" | "valid_until" | "status" | "notes"
  >
>;

export function createDiffusionPartnership(input: DiffusionPartnershipInput): Promise<DiffusionPartnership> {
  return apiRequest("/diffusion-partnerships", { method: "POST", body: input });
}

export function updateDiffusionPartnership(
  id: string,
  input: DiffusionPartnershipInput,
): Promise<DiffusionPartnership> {
  return apiRequest(`/diffusion-partnerships/${id}`, { method: "PUT", body: input });
}
