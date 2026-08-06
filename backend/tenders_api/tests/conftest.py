"""
Config pytest pour backend/tenders_api. Les modules applicatifs (handler.py,
db.py, auth.py, tenders.py...) utilisent des imports plats (pas de package
Python) car c'est le format attendu par le runtime Lambda (tout à la racine
du zip) — on ajoute donc le dossier parent au sys.path plutôt que
d'installer le dossier comme package.

Variables d'environnement requises par db.py/auth.py au niveau module :
factices ici, aucune connexion réseau réelle n'est faite dans les tests
(niveaux 1 et 2 du plan — DB mockée, pas d'intégration contre une vraie
Aurora DSQL).
"""
import os
import sys

os.environ.setdefault("AWS_REGION", "us-east-1")
os.environ.setdefault("DSQL_ENDPOINT", "test-cluster.dsql.us-east-1.on.aws")

_TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(_TESTS_DIR))  # backend/tenders_api/ (imports plats : auth, db, tenders...)
sys.path.insert(0, _TESTS_DIR)  # ce dossier lui-même : nécessaire à `from conftest import FakeCursor`
# sous --import-mode=importlib (backend/pytest.ini), requis pour un run
# combiné de plusieurs Lambdas qui partagent des noms de fichiers de test.


class FakeCursor:
    """
    Curseur factice pour les tests niveau 2 : pas de vraie base, on
    pré-charge les résultats attendus dans l'ordre des appels fetchone()/
    fetchall(), et on garde la trace des requêtes exécutées pour vérifier
    qu'aucune écriture n'a eu lieu quand une validation doit échouer avant
    tout INSERT/UPDATE.
    """

    def __init__(self, fetchone_results=None, fetchall_results=None):
        self._fetchone_queue = list(fetchone_results or [])
        self._fetchall_queue = list(fetchall_results or [])
        self.executed = []

    def execute(self, sql, params=None):
        self.executed.append((" ".join(sql.split()), params))

    def fetchone(self):
        return self._fetchone_queue.pop(0) if self._fetchone_queue else None

    def fetchall(self):
        return self._fetchall_queue.pop(0) if self._fetchall_queue else []

    def executed_sql_contains(self, needle):
        return any(needle in sql for sql, _ in self.executed)
