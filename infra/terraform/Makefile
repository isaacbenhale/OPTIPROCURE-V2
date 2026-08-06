.PHONY: build-migrate-lambda build-tenders-api-lambda build-reference-data-api-lambda build-all clean

# psycopg2-binary contient des bibliothèques compilées : on construit le
# paquet dans un conteneur Amazon Linux pour garantir la compatibilité
# avec l'environnement d'exécution Lambda, quelle que soit la machine
# qui lance `make` (macOS, Windows/WSL, Linux non compatible manylinux...).
# --platform linux/amd64 forcé explicitement : les Lambdas sont déployées
# en x86_64 (défaut Terraform, aucun bloc `architectures` dans les .tf) —
# sans ce flag, un hôte Apple Silicon produirait un wheel arm64 incompatible
# (émulation QEMU côté Docker, plus lent mais garantit la bonne architecture).

build-migrate-lambda:
	rm -rf build/migrate
	mkdir -p build/migrate
	cp lambda_src/migrate/handler.py build/migrate/handler.py
	docker run --rm --platform linux/amd64 \
		-v "$(PWD)/lambda_src/migrate:/src" \
		-v "$(PWD)/build/migrate:/out" \
		public.ecr.aws/sam/build-python3.12 \
		pip install -r /src/requirements.txt --target /out --no-cache-dir

# Code source dans backend/tenders_api/ (pas infra/terraform/lambda_src/) —
# module 3, CRUD + workflow des AO. Même contrainte psycopg2-binary que
# build-migrate-lambda.
build-tenders-api-lambda:
	rm -rf build/tenders_api
	mkdir -p build/tenders_api
	cp ../../backend/tenders_api/*.py build/tenders_api/
	docker run --rm --platform linux/amd64 \
		-v "$(PWD)/../../backend/tenders_api:/src" \
		-v "$(PWD)/build/tenders_api:/out" \
		public.ecr.aws/sam/build-python3.12 \
		pip install -r /src/requirements.txt --target /out --no-cache-dir

# Code source dans backend/reference_data_api/ — module 01, CRUD des
# référentiels (countries/categories/organizations/diffusion_partnerships).
build-reference-data-api-lambda:
	rm -rf build/reference_data_api
	mkdir -p build/reference_data_api
	cp ../../backend/reference_data_api/*.py build/reference_data_api/
	docker run --rm --platform linux/amd64 \
		-v "$(PWD)/../../backend/reference_data_api:/src" \
		-v "$(PWD)/build/reference_data_api:/out" \
		public.ecr.aws/sam/build-python3.12 \
		pip install -r /src/requirements.txt --target /out --no-cache-dir

build-all: build-migrate-lambda build-tenders-api-lambda build-reference-data-api-lambda
	@echo "Paquets Lambda prêts dans build/. Lancer 'terraform apply' ensuite."

clean:
	rm -rf build
