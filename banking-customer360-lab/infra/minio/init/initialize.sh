#!/bin/sh
set -eu

mc alias set local http://minio:9000 "$MINIO_ROOT_USER" "$MINIO_ROOT_PASSWORD" >/dev/null

for bucket in raw warehouse spark-logs; do
  mc mb --ignore-existing "local/$bucket" >/dev/null
done

for prefix in core_banking crm loan_system incremental; do
  printf '' | mc pipe "local/raw/$prefix/.keep" >/dev/null
done
for prefix in bronze silver gold lab smoke_test; do
  printf '' | mc pipe "local/warehouse/$prefix/.keep" >/dev/null
done
printf '' | mc pipe local/spark-logs/.keep >/dev/null

ensure_policy() {
  policy_name=$1
  policy_file=$2
  mc admin policy create local "$policy_name" "$policy_file" >/dev/null
}

ensure_user() {
  access_key=$1
  secret_key=$2
  policy_name=$3
  if ! mc admin user info local "$access_key" >/dev/null 2>&1; then
    mc admin user add local "$access_key" "$secret_key" >/dev/null
  fi
  mc admin policy attach local "$policy_name" --user "$access_key" >/dev/null
}

ensure_policy spark-etl /policies/spark-etl.json
ensure_policy trino-reader /policies/trino-reader.json
ensure_policy platform-admin /policies/platform-admin.json

ensure_user "$SPARK_S3_ACCESS_KEY" "$SPARK_S3_SECRET_KEY" spark-etl
ensure_user "$TRINO_S3_ACCESS_KEY" "$TRINO_S3_SECRET_KEY" trino-reader
ensure_user "$PLATFORM_S3_ACCESS_KEY" "$PLATFORM_S3_SECRET_KEY" platform-admin

mc anonymous set none local/raw >/dev/null
mc anonymous set none local/warehouse >/dev/null
mc anonymous set none local/spark-logs >/dev/null
