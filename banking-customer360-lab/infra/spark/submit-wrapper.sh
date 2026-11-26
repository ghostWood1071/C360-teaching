#!/bin/sh
set -eu

if [ -z "${SPARK_S3_ACCESS_KEY:-}" ] || [ -z "${SPARK_S3_SECRET_KEY:-}" ]; then
  echo "Spark storage credentials are required" >&2
  exit 64
fi

exec /opt/spark/bin/spark-submit \
  --conf "spark.hadoop.fs.s3a.access.key=${SPARK_S3_ACCESS_KEY}" \
  --conf "spark.hadoop.fs.s3a.secret.key=${SPARK_S3_SECRET_KEY}" \
  "$@"
