"""Validated factory for ephemeral Spark DockerOperator tasks."""

from __future__ import annotations

import os
import re
from collections.abc import Mapping, Sequence

from airflow.providers.docker.operators.docker import DockerOperator
from docker.types import Mount

SAFE_TOKEN = re.compile(r"^[A-Za-z0-9_./:=,+-]+$")
SAFE_MEMORY = re.compile(r"^[1-9][0-9]*(?:[mMgG])$")
SAFE_LOCAL_MASTER = re.compile(r"^local\[[1-9][0-9]*\]$")
ALLOWED_CONF_PREFIXES = (
    "spark.app.",
    "spark.driver.",
    "spark.executor.",
    "spark.sql.",
    "spark.hadoop.fs.s3a.connection.",
    "spark.hadoop.fs.s3a.fast.",
)


def _safe_token(value: str, field: str) -> str:
    if not isinstance(value, str) or not value or not SAFE_TOKEN.fullmatch(value):
        raise ValueError(f"Unsafe {field}: {value!r}")
    return value


def _validate_memory(value: str, field: str) -> str:
    if not SAFE_MEMORY.fullmatch(value):
        raise ValueError(f"{field} must look like 1024m or 4g")
    return value.lower()


def _validate_master(value: str) -> str:
    if SAFE_LOCAL_MASTER.fullmatch(value) or value == "spark://spark-master:7077":
        return value
    raise ValueError("Only local[N] or the lab's ephemeral standalone master is allowed")


def _validated_conf(conf: Mapping[str, str] | None) -> list[str]:
    result: list[str] = []
    for key, value in sorted((conf or {}).items()):
        if not any(key.startswith(prefix) for prefix in ALLOWED_CONF_PREFIXES):
            raise ValueError(f"Spark configuration key is not allowed: {key}")
        result.extend(["--conf", f"{_safe_token(key, 'Spark key')}={_safe_token(str(value), 'Spark value')}"])
    return result


def create_spark_task(
    task_id: str,
    job_path: str,
    job_args: Sequence[str] | None = None,
    spark_conf: Mapping[str, str] | None = None,
    driver_memory: str | None = None,
    container_memory: str | None = None,
    master: str | None = None,
    application_name: str | None = None,
    resource_profile: str | None = None,
    cpus: float | None = None,
    retries: int = 1,
    execution_timeout=None,
    extra_environment: Mapping[str, str] | None = None,
    **operator_kwargs,
) -> DockerOperator:
    """Create a Spark task without invoking a shell or accepting arbitrary Docker options."""

    task_id = _safe_token(task_id, "task_id")
    job_path = _safe_token(job_path, "job_path")
    if not job_path.startswith("/opt/spark/jobs/") or not job_path.endswith(".py"):
        raise ValueError("job_path must be a Python file below /opt/spark/jobs")

    resource_profile = resource_profile or os.environ.get("SPARK_RESOURCE_PROFILE", "standard")
    if resource_profile not in {"standard", "low"}:
        raise ValueError("resource_profile must be standard or low")
    prefix = "SPARK_LOW_" if resource_profile == "low" else "SPARK_"
    master = _validate_master(master or os.environ.get(f"{prefix}MASTER", "local[2]" if resource_profile == "low" else "local[4]"))
    driver_memory = _validate_memory(driver_memory or os.environ.get(f"{prefix}DRIVER_MEMORY", "1g" if resource_profile == "low" else "2g"), "driver_memory")
    container_memory = _validate_memory(
        container_memory or os.environ.get(f"{prefix}CONTAINER_MEMORY", "2560m" if resource_profile == "low" else "4g"), "container_memory"
    )
    cpus = float(cpus if cpus is not None else os.environ.get(f"{prefix}CPUS", "2" if resource_profile == "low" else "4"))
    if not 0.5 <= cpus <= 16:
        raise ValueError("cpus must be between 0.5 and 16")

    args = [str(value) for value in (job_args or [])]
    for value in args:
        if "\x00" in value or "\n" in value or "\r" in value:
            raise ValueError("job_args cannot contain control characters")

    app_name = application_name or f"customer360-{task_id}"
    command = [
        "spark-submit",
        "--master",
        master,
        "--driver-memory",
        driver_memory,
        "--name",
        app_name,
        "--conf",
        f"spark.sql.shuffle.partitions={os.environ.get(f'{prefix}SHUFFLE_PARTITIONS', '4' if resource_profile == 'low' else '8')}",
        *_validated_conf(spark_conf),
        job_path,
        *args,
    ]

    environment = {
        "SPARK_S3_ACCESS_KEY": os.environ["SPARK_S3_ACCESS_KEY"],
        "SPARK_S3_SECRET_KEY": os.environ["SPARK_S3_SECRET_KEY"],
        "PYTHONUNBUFFERED": "1",
    }
    allowed_environment = {
        "CORE_BANKING_JDBC_URL",
        "CORE_BANKING_DB_USER",
        "CORE_BANKING_DB_PASSWORD",
        "CRM_JDBC_URL",
        "CRM_DB_USER",
        "CRM_DB_PASSWORD",
        "PHASE3_CONFIG",
    }
    for key, value in (extra_environment or {}).items():
        if key not in allowed_environment:
            raise ValueError(f"Environment key is not allowed for Spark tasks: {key}")
        if not isinstance(value, str) or "\x00" in value:
            raise ValueError(f"Invalid environment value for {key}")
        environment[key] = value

    return DockerOperator(
        task_id=task_id,
        image=os.environ["SPARK_IMAGE"],
        command=command,
        docker_url="unix://var/run/docker.sock",
        network_mode=os.environ["DOCKER_NETWORK_NAME"],
        environment=environment,
        mounts=[
            Mount(source=os.environ["SPARK_JOBS_VOLUME"], target="/opt/spark/jobs", type="volume", read_only=True),
            Mount(source=os.environ["SPARK_EVENTS_VOLUME"], target="/spark-events", type="volume", read_only=False),
        ],
        mem_limit=container_memory,
        cpus=cpus,
        mount_tmp_dir=False,
        auto_remove="force",
        force_pull=False,
        tty=False,
        pool="spark_tasks",
        retries=retries,
        execution_timeout=execution_timeout,
        **operator_kwargs,
    )
