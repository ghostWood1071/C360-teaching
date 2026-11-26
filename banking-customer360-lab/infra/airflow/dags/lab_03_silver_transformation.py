"""Lab 03/04: isolated Silver cleansing and customer identity integration."""

from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.python import PythonOperator

from phase3_common import check_bronze_ready, phase3_spark_task

with DAG(
    dag_id="lab_03_silver_transformation", start_date=datetime(2026, 1, 1), schedule=None,
    catchup=False, max_active_runs=1, default_args={"owner": "training", "retries": 1,
    "retry_delay": timedelta(seconds=15)}, tags=["phase3", "lab03", "silver"],
    params={"profile": "small", "batch_id": "batch_01"},
) as dag:
    ready = PythonOperator(task_id="check_bronze_ready", python_callable=check_bronze_ready,
                           op_kwargs={"schema": "bronze"})
    customer = phase3_spark_task("build_customer_master", "build_customer_master.py", [
        "--profile", "{{ params.profile }}", "--batch-id", "{{ params.batch_id }}", "--load-type", "full",
        "--bronze-schema", "bronze", "--silver-schema", "lab03_silver", "--run-id", "{{ run_id }}",
    ], execution_timeout=timedelta(minutes=30))
    facts = phase3_spark_task("build_silver_facts", "build_silver_facts.py", [
        "--profile", "{{ params.profile }}", "--batch-id", "{{ params.batch_id }}", "--load-type", "full",
        "--bronze-schema", "bronze", "--silver-schema", "lab03_silver", "--run-id", "{{ run_id }}",
    ], execution_timeout=timedelta(minutes=30))
    validate = phase3_spark_task("validate_silver", "validate_silver.py", [
        "--profile", "{{ params.profile }}", "--batch-id", "{{ params.batch_id }}", "--load-type", "full",
        "--bronze-schema", "bronze", "--silver-schema", "lab03_silver", "--run-id", "{{ run_id }}",
    ], execution_timeout=timedelta(minutes=30))
    ready >> [customer, facts] >> validate

