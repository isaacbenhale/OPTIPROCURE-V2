"""
Placeholder du Publication Coordinator (CLAUDE.md §"Détection des
changements"). À implémenter dans le module 5 du plan de développement :
détection des AO créés/modifiés/expirés depuis le dernier batch réussi,
génération du manifeste versionné dans S3, écriture de l'identifiant de
batch consommé par GitHub Actions.

Ce stub existe uniquement pour que l'EventBridge Scheduler ait une cible
valide dès aujourd'hui ; il ne touche pas encore à Aurora DSQL ni au
bucket de manifestes.
"""
import json


def handler(event, context):
    print("publication_coordinator stub invoked — module 5 à implémenter")
    return {"statusCode": 200, "body": json.dumps({"status": "noop"})}
