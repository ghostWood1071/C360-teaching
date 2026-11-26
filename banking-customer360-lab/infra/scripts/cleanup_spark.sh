#!/bin/sh
set -eu

ids=$(docker ps -aq --filter "label=customer360.ephemeral=true")
if [ -z "$ids" ]; then
  echo "Không có Spark container tạm thời cần dọn."
  exit 0
fi

for container_id in $ids; do
  docker rm -f "$container_id" >/dev/null
done
echo "Đã xóa các Spark container có nhãn customer360.ephemeral=true."
