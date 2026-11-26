"""Complete parameterized Source -> Bronze -> Silver Phase 3 pipeline."""

from datetime import datetime, timedelta

from airflow import DAG
from airflow.models.param import Param
from airflow.operators.python import PythonOperator

from phase3_common import check_source_ready, phase3_spark_task, validate_pipeline_parameters

PARAMS = {
    "load_type": Param("full", enum=["full", "incremental"]),
    "batch_id": Param("batch_01", pattern=r"^batch_[0-9]{2}$"),
    "source_mode": Param("file", enum=["file", "mixed"]),
    "profile": Param("small", enum=["small", "standard"]),
    "resource_profile": Param("standard", enum=["standard", "low"]),
    "enable_quality_checks": Param(True, type="boolean"),
    "inject_failure": Param(False, type="boolean"),
    "allow_reset": Param(False, type="boolean"),
}

COMMON = [
    "--profile", "{{ params.profile }}", "--batch-id", "{{ params.batch_id }}",
    "--load-type", "{{ params.load_type }}", "--run-id", "{{ run_id }}",
]

with DAG(
    dag_id="customer360_ingestion_pipeline", description="Pipeline Source → Bronze → Silver",
    start_date=datetime(2026, 1, 1), schedule=None, catchup=False, max_active_runs=1,
    default_args={"owner": "platform", "retries": 1, "retry_delay": timedelta(seconds=20)},
    params=PARAMS, tags=["phase3", "customer360", "pipeline"],
) as dag:
    parameters = PythonOperator(task_id="validate_parameters", python_callable=validate_pipeline_parameters)
    source_ready = PythonOperator(task_id="check_source_ready", python_callable=check_source_ready,
                                  op_kwargs={"profile": "{{ params.profile }}", "batch_id": "{{ params.batch_id }}"})
    ingest = phase3_spark_task("ingest_bronze", "ingest_bronze.py", COMMON + [
        "--source-mode", "{{ params.source_mode }}", "--inject-failure", "{{ params.inject_failure | lower }}",
    ], execution_timeout=timedelta(minutes=30))
    bronze_quality = phase3_spark_task("validate_bronze", "validate_bronze.py", COMMON + [
        "--enabled", "{{ params.enable_quality_checks | lower }}",
    ],
                                      execution_timeout=timedelta(minutes=30))
    customer = phase3_spark_task("customer_master", "build_customer_master.py", COMMON,
                                 execution_timeout=timedelta(minutes=30))
    facts = phase3_spark_task("silver_facts", "build_silver_facts.py", COMMON,
                              execution_timeout=timedelta(minutes=30))
    silver_quality = phase3_spark_task("validate_silver", "validate_silver.py", COMMON + [
        "--enabled", "{{ params.enable_quality_checks | lower }}",
    ],
                                      execution_timeout=timedelta(minutes=30))
    reconcile = phase3_spark_task("reconcile_data", "reconcile_data.py", COMMON,
                                  execution_timeout=timedelta(minutes=30))
    ready = phase3_spark_task("mark_batch_ready", "mark_batch_ready.py", COMMON,
                              execution_timeout=timedelta(minutes=10))

    parameters >> source_ready >> ingest >> bronze_quality >> [customer, facts] >> silver_quality >> reconcile >> ready

