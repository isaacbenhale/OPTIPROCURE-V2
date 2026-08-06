.PHONY: build-migrate-lambda build-all clean

# psycopg2-binary contient des bibliothèques compilées : on construit le
# paquet dans un conteneur Amazon Linux pour garantir la compatibilité
# avec l'environnement d'exécution Lambda, quelle que soit la machine
# qui lance `make` (macOS, Windows/WSL, Linux non compatible manylinux...).

build-migrate-lambda:
	rm -rf build/migrate
	mkdir -p build/migrate
	cp lambda_src/migrate/handler.py build/migrate/handler.py
	docker run --rm \
		-v "$(PWD)/lambda_src/migrate:/src" \
		-v "$(PWD)/build/migrate:/out" \
		public.ecr.aws/sam/build-python3.12 \
		pip install -r /src/requirements.txt --target /out --no-cache-dir

build-all: build-migrate-lambda
	@echo "Paquets Lambda prêts dans build/. Lancer 'terraform apply' ensuite."

clean:
	rm -rf build
