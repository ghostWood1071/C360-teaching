"""Infrastructure-only smoke workflow using isolated, run-specific Delta tables."""

from __future__ import annotations

import os
import re
import socket
from datetime import datetime, timedelta
from pathlib import Path

import requests
import trino
from airflow import DAG
from airflow.operators.python import PythonOperator
from spark_docker_operator import create_spark_task


def normalized_run_id(value: str) -> str:
    return re.sub(r"[^a-z0-9_]", "_", value.lower())[-48:]


def check_dependencies() -> None:
    for host, port in (("minio", 9000), ("hive-metastore", 9083), ("trino", int(os.environ["TRINO_PORT"]))):
        with socket.create_connection((host, port), timeout=10):
            pass
    requests.get("http://minio:9000/minio/health/live", timeout=10).raise_for_status()


def validate_with_trino(run_id: str) -> None:
    table = f"infra_{normalized_run_id(run_id)}"
    connection = trino.dbapi.connect(
        host=os.environ["TRINO_HOST"],
        port=int(os.environ["TRINO_PORT"]),
        user="infrastructure_smoke_test",
        catalog="lakehouse",
        schema="smoke_test",
        http_scheme=os.environ.get("TRINO_SCHEME", "http"),
    )
    cursor = connection.cursor()
    cursor.execute(f'SELECT id, name, amount FROM "{table}" ORDER BY id')
    actual = cursor.fetchall()
    expected = [[1, "alpha", 100], [2, "beta-updated", 250], [3, "gamma", 300], [4, "delta", 400]]
    if actual != expected:
        raise AssertionError(f"Trino returned {actual!r}, expected {expected!r}")


def validate_event_logs() -> None:
    logs = [path for path in Path("/spark-events").iterdir() if path.is_file() and not path.name.startswith(".")]
    if not logs or not any(path.stat().st_size > 0 for path in logs):
        raise AssertionError("No persistent Spark event log was written")


default_args = {"owner": "platform", "retries": 1, "retry_delay": timedelta(seconds=15)}

with DAG(
    dag_id="infrastructure_smoke_test",
    description="Kiểm tra hạ tầng Delta/MinIO/HMS/Trino bằng Spark container tạm thời",
    start_date=datetime(2026, 1, 1),
    schedule=None,
    catchup=False,
    max_active_runs=1,
    default_args=default_args,
    tags=["infrastructure", "delta", "smoke-test"],
) as dag:
    dependency_check = PythonOperator(task_id="check_dependencies", python_callable=check_dependencies)
    create_table = create_spark_task(
        task_id="create_delta_table",
        job_path="/opt/spark/jobs/smoke_tests/delta_smoke_test.py",
        job_args=["create", "--run-id", "{{ run_id }}"],
        application_name="infra-smoke-create-{{ run_id }}",
    )
    append_data = create_spark_task(
        task_id="append_delta_data",
        job_path="/opt/spark/jobs/smoke_tests/delta_smoke_test.py",
        job_args=["append", "--run-id", "{{ run_id }}"],
        application_name="infra-smoke-append-{{ run_id }}",
    )
    merge_data = create_spark_task(
        task_id="merge_delta_data",
        job_path="/opt/spark/jobs/smoke_tests/delta_merge_test.py",
        job_args=["--run-id", "{{ run_id }}"],
        application_name="infra-smoke-merge-{{ run_id }}",
    )
    spark_validation = create_spark_task(
        task_id="validate_with_spark",
        job_path="/opt/spark/jobs/smoke_tests/delta_smoke_test.py",
        job_args=["validate", "--run-id", "{{ run_id }}"],
        application_name="infra-smoke-validate-{{ run_id }}",
    )
    trino_validation = PythonOperator(
        task_id="validate_with_trino",
        python_callable=validate_with_trino,
        op_kwargs={"run_id": "{{ run_id }}"},
    )
    event_log_validation = PythonOperator(task_id="validate_event_logs", python_callable=validate_event_logs)
    dependency_check >> create_table >> append_data >> merge_data >> spark_validation >> trino_validation >> event_log_validation
