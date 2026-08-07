"""
Config pytest pour backend/users_api. Copie du conftest.py de
backend/reference_data_api/tests (même raison : imports plats, format
attendu par le runtime Lambda, pas de package Python).
"""
import os
import sys

os.environ.setdefault("AWS_REGION", "us-east-1")
os.environ.setdefault("DSQL_ENDPOINT", "test-cluster.dsql.us-east-1.on.aws")
os.environ.setdefault("COGNITO_USER_POOL_ID", "us-east-1_TESTPOOL")

_TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(_TESTS_DIR))  # backend/users_api/ (imports plats)
sys.path.insert(0, _TESTS_DIR)  # ce dossier lui-même : nécessaire à `from conftest import FakeCursor`
# sous --import-mode=importlib (backend/pytest.ini), requis pour un run
# combiné de plusieurs Lambdas qui partagent des noms de fichiers de test.


class FakeCursor:
    """Curseur factice pour les tests niveau 2 — voir backend/tenders_api/tests/conftest.py."""

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
