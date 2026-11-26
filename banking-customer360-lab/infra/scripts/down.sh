#!/bin/sh
set -eu
PROJECT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)
cd "$PROJECT_DIR"
docker compose --env-file .env -f infra/compose.yaml -f infra/compose.security.yaml -f infra/compose.audit.yaml -f infra/compose.distributed.yaml -f infra/compose.sources.yaml down --remove-orphans
