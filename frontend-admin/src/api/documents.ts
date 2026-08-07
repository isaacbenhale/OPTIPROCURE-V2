// Miroir des routes de backend/tenders_api/documents.py (module 02).
import { apiRequest } from "./client";
import type { TenderDocument, TenderDocumentDownload, TenderDocumentUpload } from "../types";

export interface CreateUploadInput {
  file_name: string;
  content_type: string;
  size_bytes: number;
}

export function createUpload(tenderId: string, input: CreateUploadInput): Promise<TenderDocumentUpload> {
  return apiRequest<TenderDocumentUpload>(`/tenders/${tenderId}/documents`, { method: "POST", body: input });
}

// L'upload effectif se fait en PUT direct vers S3 (URL présignée renvoyée
// par createUpload), pas via l'API back-office — voir tasks/02.
export async function uploadFileToS3(uploadUrl: string, file: File): Promise<void> {
  const response = await fetch(uploadUrl, {
    method: "PUT",
    headers: { "Content-Type": file.type },
    body: file,
  });
  if (!response.ok) {
    throw new Error("Échec de l'upload du fichier vers S3.");
  }
}

export function listDocuments(tenderId: string): Promise<{ items: TenderDocument[] }> {
  return apiRequest(`/tenders/${tenderId}/documents`);
}

export function getDocumentDownloadUrl(tenderId: string, documentId: string): Promise<TenderDocumentDownload> {
  return apiRequest<TenderDocumentDownload>(`/tenders/${tenderId}/documents/${documentId}`);
}

export function deleteDocument(tenderId: string, documentId: string): Promise<{ status: string }> {
  return apiRequest(`/tenders/${tenderId}/documents/${documentId}`, { method: "DELETE" });
}
