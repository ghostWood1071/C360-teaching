#!/bin/sh
set -eu
PROJECT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)
cd "$PROJECT_DIR"
set -a
. ./.env
set +a

profile=${1:-base}
deadline=$(( $(date +%s) + 300 ))

check_url() {
  name=$1
  url=$2
  auth=${3:-}
  while :; do
    if [ -n "$auth" ]; then
      if curl -kfsS -u "$auth" "$url" >/dev/null 2>&1; then break; fi
    elif curl -kfsS "$url" >/dev/null 2>&1; then
      break
    fi
    if [ "$(date +%s)" -ge "$deadline" ]; then
      echo "Quá thời gian chờ $name: $url" >&2
      exit 1
    fi
    sleep 3
  done
  echo "$name: healthy"
}

check_url MinIO "http://localhost:${MINIO_API_PORT}/minio/health/live"
case "$profile" in
  etl)
    check_url Airflow "http://localhost:${AIRFLOW_PORT}/health"
    check_url SparkHistory "http://localhost:${SPARK_HISTORY_PORT}/api/v1/applications"
    ;;
  query)
    check_url Trino "http://localhost:${TRINO_HTTP_PORT}/v1/info"
    ;;
  security|audit)
    check_url Ranger "http://localhost:${RANGER_PORT}/service/public/v2/api/service" "${RANGER_ADMIN_USER}:${RANGER_ADMIN_PASSWORD}"
    check_url Trino "https://localhost:${TRINO_HTTPS_PORT}/v1/info" "platform_admin:${TRINO_PLATFORM_ADMIN_PASSWORD}"
    ;;
  base)
    check_url Airflow "http://localhost:${AIRFLOW_PORT}/health"
    check_url SparkHistory "http://localhost:${SPARK_HISTORY_PORT}/api/v1/applications"
    check_url Trino "http://localhost:${TRINO_HTTP_PORT}/v1/info"
    ;;
esac
