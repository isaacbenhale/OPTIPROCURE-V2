.PHONY: test

# Chaque Lambda sous backend/ partage des noms de fichiers (auth.py, db.py,
# errors.py, handler.py) sans être un vrai package Python — imports plats
# requis par le runtime Lambda (voir chaque conftest.py). pytest.ini
# (--import-mode=importlib) évite la collision au moment de la COLLECTE des
# fichiers de test (conftest.py, test_db_retry.py partagés entre Lambdas),
# mais PAS la collision d'IMPORT du code testé lui-même : `import auth`
# reste mis en cache par nom nu dans sys.modules, donc un run combiné
# `pytest backend/` peut faire tester par erreur le auth.py d'une AUTRE
# Lambda à des tests qui n'en font pas partie, sans qu'aucune erreur ne le
# signale tant que les fichiers sont fonctionnellement identiques (bug réel
# constaté le 2026-08-07 dès que auth.py de tenders_api et des autres
# Lambdas ont divergé — voir docs/LECONS-APPRISES-AWS-SERVERLESS.md).
# Un process pytest séparé par Lambda (sys.modules propre à chaque process)
# est la seule garantie correcte — jamais `pytest backend/` directement.
test:
	@for dir in tenders_api reference_data_api users_api; do \
		echo "=== $$dir ==="; \
		(cd $$dir && python -m pytest -q) || exit 1; \
	done
