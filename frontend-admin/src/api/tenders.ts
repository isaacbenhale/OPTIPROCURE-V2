// Miroir des routes de backend/tenders_api/handler.py (§ tenders).
import { apiRequest } from "./client";
import type { StatusHistoryEntry, Tender, TenderListResponse } from "../types";

export interface TenderListFilters {
  status?: string;
  sector?: string;
  procedure_type?: string;
  country_id?: string;
  category_id?: string;
  q?: string;
  cursor?: string;
  page_size?: string;
  [key: string]: string | undefined;
}

export function listTenders(filters: TenderListFilters = {}): Promise<TenderListResponse> {
  return apiRequest<TenderListResponse>("/tenders", { query: filters });
}

export function getTender(id: string): Promise<Tender> {
  return apiRequest<Tender>(`/tenders/${id}`);
}

// Sous-ensemble des champs de Tender modifiables via le formulaire de
// création/édition (voir tenders.py CONTENT_COLUMNS + category_ids).
export type TenderInput = Partial<
  Pick<
    Tender,
    | "reference_number"
    | "title"
    | "description"
    | "sector"
    | "organization_id"
    | "country_id"
    | "procurement_type"
    | "procedure_type"
    | "location_region"
    | "location_city"
    | "estimated_budget"
    | "currency"
    | "submission_deadline"
    | "eligibility_criteria"
    | "required_documents"
    | "contact_name"
    | "contact_role"
    | "contact_email"
    | "contact_phone"
    | "source_name"
    | "source_url"
    | "category_ids"
  >
> & { primary_category_id?: string };

export function createTender(input: TenderInput): Promise<Tender> {
  return apiRequest<Tender>("/tenders", { method: "POST", body: input });
}

export function updateTender(id: string, input: TenderInput): Promise<Tender> {
  return apiRequest<Tender>(`/tenders/${id}`, { method: "PUT", body: input });
}

export function deleteTender(id: string): Promise<{ status: string }> {
  return apiRequest(`/tenders/${id}`, { method: "DELETE" });
}

export function submitTender(id: string): Promise<Tender> {
  return apiRequest<Tender>(`/tenders/${id}/submit`, { method: "POST" });
}

export function returnTender(id: string, reason: string): Promise<Tender> {
  return apiRequest<Tender>(`/tenders/${id}/return`, { method: "POST", body: { reason } });
}

export function endorseTender(id: string): Promise<Tender> {
  return apiRequest<Tender>(`/tenders/${id}/endorse`, { method: "POST" });
}

export function approveTender(id: string): Promise<Tender> {
  return apiRequest<Tender>(`/tenders/${id}/approve`, { method: "POST" });
}

export function rejectTender(id: string, reason: string): Promise<Tender> {
  return apiRequest<Tender>(`/tenders/${id}/reject`, { method: "POST", body: { reason } });
}

export function archiveTender(id: string): Promise<Tender> {
  return apiRequest<Tender>(`/tenders/${id}/archive`, { method: "POST" });
}

export function getTenderHistory(id: string): Promise<{ items: StatusHistoryEntry[] }> {
  return apiRequest(`/tenders/${id}/history`);
}
