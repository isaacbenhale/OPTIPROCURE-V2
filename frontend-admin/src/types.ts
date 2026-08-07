// Types miroir des payloads de backend/tenders_api et backend/reference_data_api.
// Tenus à jour à la main (pas de génération automatique pour cette passe).

export type Role = "AGENT" | "REVIEWER" | "ADMIN";

export type TenderStatus =
  | "DRAFT"
  | "PENDING_REVIEW"
  | "REVISION_REQUESTED"
  | "APPROVED"
  | "QUEUED_FOR_PUBLICATION"
  | "PUBLISHED"
  | "EXPIRED"
  | "REJECTED"
  | "ARCHIVED";

// Miroir de transitions.py : STATUS_ACTIONS + NON_STATUS_ACTIONS.
export type AvailableAction =
  | "update"
  | "submit"
  | "return"
  | "endorse"
  | "approve"
  | "reject"
  | "archive"
  | "delete";

export type Sector = "PUBLIC" | "PRIVATE";
export type ProcurementType = "TRAVAUX" | "FOURNITURES" | "SERVICES" | "PRESTATIONS_INTELLECTUELLES";
export type ProcedureType = "OUVERT" | "RESTREINT" | "GRE_A_GRE" | "CONSULTATION" | "CONCOURS";

export interface User {
  id: string;
  cognito_sub: string;
  email: string;
  full_name: string;
  role: Role;
  is_active: boolean;
  mfa_enabled: boolean;
  last_login_at: string | null;
}

export interface Tender {
  id: string;
  reference_number: string | null;
  title: string;
  description: string;
  sector: Sector;
  organization_id: string;
  country_id: string;
  category_ids: string[];
  procurement_type: ProcurementType | null;
  procedure_type: ProcedureType | null;
  location_region: string | null;
  location_city: string | null;
  estimated_budget: string | null;
  currency: string | null;
  submission_deadline: string;
  eligibility_criteria: string | null;
  required_documents: string | null;
  contact_name: string | null;
  contact_role: string | null;
  contact_email: string | null;
  contact_phone: string | null;
  source_name: string | null;
  source_url: string | null;
  status: TenderStatus;
  created_by: string;
  reviewed_by: string | null;
  approved_by: string | null;
  content_hash: string;
  created_at: string;
  updated_at: string;
  available_actions: AvailableAction[];
}

export interface TenderListResponse {
  items: Tender[];
  next_cursor: string | null;
}

export interface StatusHistoryEntry {
  from_status: TenderStatus | null;
  to_status: TenderStatus;
  changed_by: string | null;
  actor_type: "USER" | "SYSTEM" | "PIPELINE";
  reason: string | null;
  created_at: string;
}

export interface TenderDocument {
  id: string;
  tender_id: string;
  file_name: string;
  content_type: string;
  size_bytes: number;
  uploaded_by: string;
  uploaded_at: string;
}

export interface TenderDocumentUpload extends TenderDocument {
  upload_url: string;
}

export interface TenderDocumentDownload extends TenderDocument {
  download_url: string;
}

export interface Country {
  id: string;
  iso_code: string;
  name: string;
}

export interface Category {
  id: string;
  parent_id: string | null;
  name: string;
  slug: string;
  is_active: boolean;
}

export interface Organization {
  id: string;
  name: string;
  org_type: "PUBLIC_BODY" | "PRIVATE_PARTNER" | "DONOR" | "AGGREGATOR";
  country_id: string | null;
  website: string | null;
  contact_email: string | null;
  is_active: boolean;
}

export interface DiffusionPartnership {
  id: string;
  organization_id: string;
  convention_reference: string;
  signed_at: string;
  valid_from: string;
  valid_until: string | null;
  status: "ACTIVE" | "SUSPENDED" | "EXPIRED" | "TERMINATED";
  document_s3_key: string | null;
  notes: string | null;
}

export interface ApiErrorBody {
  error: {
    code: "VALIDATION_ERROR" | "UNAUTHORIZED" | "FORBIDDEN" | "NOT_FOUND" | "CONFLICT" | "INTERNAL_ERROR";
    message: string;
    fields: Record<string, unknown>;
  };
}
