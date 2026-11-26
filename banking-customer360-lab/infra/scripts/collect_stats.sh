#!/bin/sh
set -eu

PROJECT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)
cd "$PROJECT_DIR"
output="infra/evidence/docker-stats-$(date -u +%Y%m%dT%H%M%SZ).csv"
{
  echo "name,cpu_percent,memory_usage,memory_percent,net_io,block_io,pids"
  docker stats --no-stream --format '{{.Name}},{{.CPUPerc}},{{.MemUsage}},{{.MemPerc}},{{.NetIO}},{{.BlockIO}},{{.PIDs}}'
} > "$output"
echo "Đã ghi số đo tức thời: $PROJECT_DIR/$output"
