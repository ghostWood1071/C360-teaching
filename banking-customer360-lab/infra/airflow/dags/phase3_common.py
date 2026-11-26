"""Small Airflow helpers shared by the Phase 3 training DAGs."""

from __future__ import annotations

import os
import socket

import boto3
from botocore.config import Config
import trino

from spark_docker_operator import create_spark_task


def spark_environment() -> dict[str, str]:
    names = (
        "CORE_BANKING_JDBC_URL", "CORE_BANKING_DB_USER", "CORE_BANKING_DB_PASSWORD",
        "CRM_JDBC_URL", "CRM_DB_USER", "CRM_DB_PASSWORD", "PHASE3_CONFIG",
    )
    return {name: os.environ[name] for name in names if os.environ.get(name)}


def phase3_spark_task(task_id: str, job: str, arguments: list[str], **kwargs):
    return create_spark_task(
        task_id=task_id,
        job_path=f"/opt/spark/jobs/phase3/{job}",
        job_args=arguments,
        application_name=f"customer360-{task_id}-{{{{ run_id }}}}",
        resource_profile=os.environ.get("SPARK_RESOURCE_PROFILE", "standard"),
        extra_environment=spark_environment(),
        **kwargs,
    )


def validate_pipeline_parameters(**context) -> None:
    params = context["params"]
    expected_batch = "batch_01" if params["load_type"] == "full" else "batch_02"
    if params["batch_id"] != expected_batch:
        raise ValueError(f"{params['load_type']} load requires {expected_batch}")
    if params["source_mode"] not in {"file", "mixed"}:
        raise ValueError("source_mode must be file or mixed")
    deployed = os.environ.get("SPARK_RESOURCE_PROFILE", "standard")
    if params["resource_profile"] != deployed:
        raise ValueError(f"Requested {params['resource_profile']} but Airflow is deployed with {deployed}; update .env and restart Airflow")
    if params["load_type"] == "full" and params.get("allow_reset", False):
        raise ValueError("Full reset is intentionally not available through the DAG; use the documented explicit reset command")


def check_source_ready(profile: str, batch_id: str) -> None:
    with socket.create_connection(("minio", 9000), timeout=10):
        pass
    client = boto3.client(
        "s3", endpoint_url="http://minio:9000",
        aws_access_key_id=os.environ["SPARK_S3_ACCESS_KEY"],
        aws_secret_access_key=os.environ["SPARK_S3_SECRET_KEY"],
        config=Config(signature_version="s3v4"), region_name="us-east-1",
    )
    prefixes = [
        f"{profile}/{batch_id}/core_banking/customers/",
        f"{profile}/{batch_id}/core_banking/accounts/",
        f"{profile}/raw_delivery/{batch_id}/transactions/",
        f"{profile}/{batch_id}/crm/customer_profiles/",
        f"{profile}/{batch_id}/loan_system/loans/",
        f"{profile}/metadata/dataset_manifest.json",
    ]
    missing = [prefix for prefix in prefixes if client.list_objects_v2(Bucket="raw", Prefix=prefix, MaxKeys=1).get("KeyCount", 0) == 0]
    if missing:
        raise FileNotFoundError(f"Source preparation is incomplete: {missing}")


def check_bronze_ready(schema: str = "bronze") -> None:
    connection = trino.dbapi.connect(host=os.environ["TRINO_HOST"], port=int(os.environ["TRINO_PORT"]),
                                     user="phase3_airflow", catalog="lakehouse", schema=schema,
                                     http_scheme=os.environ.get("TRINO_SCHEME", "http"))
    cursor = connection.cursor()
    cursor.execute("SHOW TABLES")
    tables = {row[0] for row in cursor.fetchall()}
    required = {"customers", "accounts", "transactions", "customer_profiles", "loans"}
    if not required <= tables:
        raise RuntimeError(f"Missing Bronze tables in {schema}: {sorted(required - tables)}")

