import { useEffect, useState, type ChangeEvent } from "react";

import { createUpload, deleteDocument, getDocumentDownloadUrl, listDocuments, uploadFileToS3 } from "../api/documents";
import type { TenderDocument } from "../types";
import { ErrorBanner } from "./ErrorBanner";

// Miroir de backend/tenders_api/documents.py — ALLOWED_CONTENT_TYPES /
// MAX_DOCUMENT_SIZE_BYTES. Validation ici purement pour l'UX (feedback
// immédiat) ; la Lambda revalide de toute façon côté serveur.
const MAX_SIZE_BYTES = 25 * 1024 * 1024;
const ALLOWED_TYPES = [
  "application/pdf",
  "application/msword",
  "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
  "application/vnd.ms-excel",
  "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
  "image/png",
  "image/jpeg",
];

export function DocumentsPanel({ tenderId, canManage }: { tenderId: string; canManage: boolean }) {
  const [documents, setDocuments] = useState<TenderDocument[]>([]);
  const [error, setError] = useState<unknown>(null);
  const [uploading, setUploading] = useState(false);

  async function refresh(): Promise<void> {
    try {
      const { items } = await listDocuments(tenderId);
      setDocuments(items);
    } catch (err) {
      setError(err);
    }
  }

  useEffect(() => {
    void refresh();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tenderId]);

  async function handleUpload(event: ChangeEvent<HTMLInputElement>): Promise<void> {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (!file) return;

    setError(null);
    if (!ALLOWED_TYPES.includes(file.type)) {
      setError(new Error("Type de fichier non autorisé (PDF, Word, Excel, PNG, JPEG uniquement)."));
      return;
    }
    if (file.size > MAX_SIZE_BYTES) {
      setError(new Error("Fichier trop volumineux (25 Mo maximum)."));
      return;
    }

    setUploading(true);
    try {
      const upload = await createUpload(tenderId, {
        file_name: file.name,
        content_type: file.type,
        size_bytes: file.size,
      });
      await uploadFileToS3(upload.upload_url, file);
      await refresh();
    } catch (err) {
      setError(err);
    } finally {
      setUploading(false);
    }
  }

  async function handleDownload(documentId: string): Promise<void> {
    try {
      const { download_url } = await getDocumentDownloadUrl(tenderId, documentId);
      window.open(download_url, "_blank", "noopener,noreferrer");
    } catch (err) {
      setError(err);
    }
  }

  async function handleDelete(documentId: string): Promise<void> {
    try {
      await deleteDocument(tenderId, documentId);
      await refresh();
    } catch (err) {
      setError(err);
    }
  }

  return (
    <div className="documents-panel">
      <h3>Documents joints</h3>
      <ErrorBanner error={error} />
      {documents.length === 0 ? (
        <p className="muted">Aucun document.</p>
      ) : (
        <ul>
          {documents.map((doc) => (
            <li key={doc.id}>
              <button type="button" onClick={() => handleDownload(doc.id)}>
                {doc.file_name}
              </button>
              <span className="muted"> ({Math.round(doc.size_bytes / 1024)} Ko)</span>
              {canManage && (
                <button type="button" onClick={() => handleDelete(doc.id)}>
                  Supprimer
                </button>
              )}
            </li>
          ))}
        </ul>
      )}
      {canManage && (
        <label className="upload-input">
          {uploading ? "Envoi en cours…" : "Ajouter un document"}
          <input type="file" onChange={handleUpload} disabled={uploading} hidden />
        </label>
      )}
    </div>
  );
}
