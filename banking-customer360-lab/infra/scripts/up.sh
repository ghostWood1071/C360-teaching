#!/bin/sh
set -eu

PROJECT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)
cd "$PROJECT_DIR"
test -f .env || { echo "Chưa có .env; chạy make setup." >&2; exit 1; }

BASE="docker compose --env-file .env -f infra/compose.yaml"
profile=${1:-base}

case "$profile" in
  base) $BASE up -d ;;
  etl) $BASE up -d postgres minio minio-init hive-metastore-init hive-metastore spark-jobs-init spark-volume-init spark-history airflow-init airflow-scheduler airflow-webserver ;;
  query) $BASE up -d postgres minio minio-init hive-metastore-init hive-metastore trino ;;
  security) $BASE -f infra/compose.security.yaml up -d ;;
  audit) RANGER_AUDIT_SOLR_ENABLED=true $BASE -f infra/compose.security.yaml -f infra/compose.audit.yaml up -d ;;
  distributed) $BASE -f infra/compose.distributed.yaml --profile distributed up -d spark-master spark-worker-1 spark-worker-2 ;;
  *) echo "Profile không hợp lệ: $profile" >&2; exit 2 ;;
esac

"$PROJECT_DIR/infra/scripts/healthcheck.sh" "$profile"
