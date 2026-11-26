#!/bin/sh
set -eu

airflow db migrate

if airflow users list --output plain | awk '{print $2}' | grep -Fxq "$AIRFLOW_ADMIN_USER"; then
  airflow users reset-password --username "$AIRFLOW_ADMIN_USER" "--password=$AIRFLOW_ADMIN_PASSWORD"
else
  airflow users create \
    --username "$AIRFLOW_ADMIN_USER" \
    "--password=$AIRFLOW_ADMIN_PASSWORD" \
    --firstname Platform \
    --lastname Admin \
    --role Admin \
    --email "$AIRFLOW_ADMIN_EMAIL"
fi

airflow pools set spark_tasks "${SPARK_TASK_POOL_SLOTS:-1}" "Serialized ephemeral Spark applications"
