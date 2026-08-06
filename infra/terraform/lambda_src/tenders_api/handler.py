"""
Placeholder de la Lambda métier back-office (CRUD des AO).

À implémenter dans le module 3 du plan de développement (CRUD des AO via
API Gateway + Lambda) : connexion dsql:DbConnect (pas Admin), lecture du
JWT Cognito transmis par l'API Gateway JWT Authorizer, et application des
autorisations fines par rôle (AGENT/REVIEWER/ADMIN) — voir CLAUDE.md.

Ce stub existe uniquement pour que l'infrastructure (API Gateway, route,
intégration Lambda) soit déployable dès aujourd'hui.
"""
import json


def handler(event, context):
    return {
        "statusCode": 200,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps({"status": "ok", "message": "tenders-api placeholder — module 3 à implémenter"}),
    }
