#!/bin/sh
set -eu

PROJECT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)
cd "$PROJECT_DIR"
COMPOSE="docker compose --env-file .env -f infra/compose.yaml"

"$PROJECT_DIR/infra/scripts/healthcheck.sh" base
$COMPOSE exec -T airflow-scheduler airflow dags unpause infrastructure_smoke_test >/dev/null
run_id="manual_infra_$(date -u +%Y%m%dT%H%M%SZ)"
$COMPOSE exec -T airflow-scheduler airflow dags trigger infrastructure_smoke_test --run-id "$run_id" >/dev/null

deadline=$(( $(date +%s) + 1800 ))
while :; do
  state=$(
    $COMPOSE exec -T airflow-scheduler \
      airflow dags list-runs -d infrastructure_smoke_test --no-backfill --output plain 2>/dev/null \
      | awk -v id="$run_id" '$2 == id { print $3; exit }'
  )
  case "$state" in
    success)
      echo "Infrastructure smoke test passed: $run_id"
      exit 0
      ;;
    failed)
      echo "Infrastructure smoke test failed: $run_id" >&2
      $COMPOSE exec -T airflow-scheduler airflow tasks states-for-dag-run infrastructure_smoke_test "$run_id" || true
      exit 1
      ;;
  esac
  if [ "$(date +%s)" -ge "$deadline" ]; then
    echo "Infrastructure smoke test timed out: $run_id" >&2
    exit 1
  fi
  sleep 5
done
