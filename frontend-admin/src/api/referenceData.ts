// Miroir en lecture des routes de backend/reference_data_api (module 01) —
// consommées ici uniquement pour peupler les listes déroulantes du
// formulaire de création/édition d'un AO (TenderForm). La gestion complète
// des référentiels (création/édition depuis l'UI) n'est pas dans le
// périmètre du module 03 (voir tasks/03-frontend-admin-backoffice.md).
// Même API Gateway que tenders_api (aws_apigatewayv2_api.backoffice unique).
import { apiRequest } from "./client";
import type { Category, Country, Organization } from "../types";

export function listCountries(): Promise<{ items: Country[] }> {
  return apiRequest("/countries");
}

export function listCategories(): Promise<{ items: Category[] }> {
  return apiRequest("/categories");
}

export function listOrganizations(): Promise<{ items: Organization[] }> {
  return apiRequest("/organizations");
}
