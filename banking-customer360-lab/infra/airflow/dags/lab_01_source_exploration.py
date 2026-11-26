"""Lab 01: inspect source data without writing pipeline tables."""

from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.empty import EmptyOperator
from airflow.operators.python import PythonOperator

from phase3_common import check_source_ready, phase3_spark_task

with DAG(
    dag_id="lab_01_source_exploration", start_date=datetime(2026, 1, 1), schedule=None,
    catchup=False, max_active_runs=1, default_args={"owner": "training", "retries": 1,
    "retry_delay": timedelta(seconds=15)}, tags=["phase3", "lab01", "source"],
    params={"profile": "small", "batch_id": "batch_01", "source_mode": "file"},
) as dag:
    ready = PythonOperator(task_id="check_source_ready", python_callable=check_source_ready,
                           op_kwargs={"profile": "{{ params.profile }}", "batch_id": "{{ params.batch_id }}"})
    profile = phase3_spark_task("profile_sources", "profile_sources.py", [
        "--profile", "{{ params.profile }}", "--batch-id", "{{ params.batch_id }}",
        "--source-mode", "{{ params.source_mode }}", "--run-id", "{{ run_id }}", "--explain",
    ], execution_timeout=timedelta(minutes=30))
    validated = EmptyOperator(task_id="validate_source_manifest")
    ready >> profile >> validated

