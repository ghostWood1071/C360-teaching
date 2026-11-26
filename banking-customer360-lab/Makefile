SHELL := /bin/sh
COMPOSE := docker compose --env-file .env -f infra/compose.yaml

.PHONY: setup build up up-etl up-query up-security up-audit health smoke-test security-test logs stats cleanup-spark down reset config test phase3-prepare-small phase3-verify

setup:
	./infra/scripts/setup.sh

build:
	$(COMPOSE) build

up:
	./infra/scripts/up.sh base

up-etl:
	./infra/scripts/up.sh etl

up-query:
	./infra/scripts/up.sh query

up-security:
	./infra/scripts/up.sh security

up-audit:
	./infra/scripts/up.sh audit

health:
	./infra/scripts/healthcheck.sh

smoke-test:
	./infra/scripts/smoke_test.sh

security-test:
	./infra/scripts/verify_security.py

logs:
	$(COMPOSE) logs --tail=200 -f

stats:
	./infra/scripts/collect_stats.sh

cleanup-spark:
	./infra/scripts/cleanup_spark.sh

down:
	./infra/scripts/down.sh

reset:
	./infra/scripts/reset.sh

config:
	$(COMPOSE) config --quiet

test:
	python -m pytest -q

.PHONY: generate-small generate-standard validate-small validate-standard

generate-small:
	python synthetic_data_generator/scripts/generate_data.py --config synthetic_data_generator/configs/small.yaml --output data/small

generate-standard:
	python synthetic_data_generator/scripts/generate_data.py --config synthetic_data_generator/configs/standard.yaml --output data/standard

validate-small:
	python synthetic_data_generator/scripts/validate_data.py --data-path data/small

validate-standard:
	python synthetic_data_generator/scripts/validate_data.py --data-path data/standard

phase3-prepare-small:
	python infra/scripts/prepare_phase3_sources.py --profile small

phase3-verify:
	python infra/scripts/verify_phase3.py
