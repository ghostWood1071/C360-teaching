"""Lab 02: isolated Source to Bronze full-load exercise."""

from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.python import PythonOperator

from phase3_common import check_source_ready, phase3_spark_task

with DAG(
    dag_id="lab_02_bronze_ingestion", start_date=datetime(2026, 1, 1), schedule=None,
    catchup=False, max_active_runs=1, default_args={"owner": "training", "retries": 1,
    "retry_delay": timedelta(seconds=15)}, tags=["phase3", "lab02", "bronze"],
    params={"profile": "small", "batch_id": "batch_01", "source_mode": "file"},
) as dag:
    ready = PythonOperator(task_id="check_source_ready", python_callable=check_source_ready,
                           op_kwargs={"profile": "{{ params.profile }}", "batch_id": "{{ params.batch_id }}"})
    ingest = phase3_spark_task("ingest_bronze_tables", "ingest_bronze.py", [
        "--profile", "{{ params.profile }}", "--batch-id", "{{ params.batch_id }}", "--load-type", "full",
        "--source-mode", "{{ params.source_mode }}", "--bronze-schema", "lab02_bronze", "--run-id", "{{ run_id }}",
    ], execution_timeout=timedelta(minutes=30))
    validate = phase3_spark_task("validate_bronze", "validate_bronze.py", [
        "--profile", "{{ params.profile }}", "--batch-id", "{{ params.batch_id }}", "--load-type", "full",
        "--bronze-schema", "lab02_bronze", "--run-id", "{{ run_id }}",
    ], execution_timeout=timedelta(minutes=30))
    ready >> ingest >> validate

