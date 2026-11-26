#!/bin/sh
set -eu

PROJECT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)
cd "$PROJECT_DIR"
if [ "${1:-}" != "--yes" ]; then
  printf "Thao tác này xóa volume PostgreSQL, MinIO, Airflow, Spark event log, Ranger và Solr của project. Nhập RESET: "
  read -r answer
  [ "$answer" = "RESET" ] || { echo "Đã hủy."; exit 1; }
fi

docker compose --env-file .env -f infra/compose.yaml -f infra/compose.security.yaml -f infra/compose.audit.yaml -f infra/compose.distributed.yaml -f infra/compose.sources.yaml down --volumes --remove-orphans
echo "Đã xóa container, network và volume chỉ thuộc project customer360. Không thể khôi phục nếu chưa backup."
