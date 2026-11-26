"""File and JDBC source readers selected by configuration."""

from __future__ import annotations

import os

from pyspark.sql import functions as F

from customer360.configuration import raw_root
from customer360.contracts import TABLE_CONTRACTS, validate_batch_id
from customer360.schemas import source_schema


def parquet_path(config: dict, profile: str, batch_id: str, table: str) -> str:
    validate_batch_id(batch_id)
    root = raw_root(config, profile)
    if table == "transactions":
        return f"{root}/raw_delivery/{batch_id}/transactions"
    system = TABLE_CONTRACTS[table]["source_system"]
    return f"{root}/{batch_id}/{system}/{table}"


def read_parquet(spark, config: dict, profile: str, batch_id: str, table: str):
    return spark.read.schema(source_schema(table)).parquet(parquet_path(config, profile, batch_id, table))


def _read_jdbc(spark, config: dict, table: str, batch_id: str):
    contract = TABLE_CONTRACTS[table]
    system = contract["source_system"]
    if system == "core_banking":
        url, user, password = (
            os.environ["CORE_BANKING_JDBC_URL"], os.environ["CORE_BANKING_DB_USER"],
            os.environ["CORE_BANKING_DB_PASSWORD"],
        )
    elif system == "crm":
        url, user, password = (
            os.environ["CRM_JDBC_URL"], os.environ["CRM_DB_USER"], os.environ["CRM_DB_PASSWORD"],
        )
    else:
        raise ValueError(f"JDBC is not configured for {table}")
    prefix = config["jdbc"].get("staging_table_prefix", "phase3")
    staging = f"{prefix}_{batch_id}_{table}"
    options = {"url": url, "dbtable": staging, "user": user, "password": password,
               "driver": "org.postgresql.Driver", "fetchsize": str(config["jdbc"]["fetch_size"])}
    partitions = int(config["jdbc"].get("num_partitions", 1))
    if partitions > 1:
        key = contract["key"]
        bounds = (spark.read.format("jdbc").options(**{**options, "dbtable": f"(SELECT MIN({key}) AS lo, MAX({key}) AS hi FROM {staging}) bounds"}).load().first())
        if bounds and bounds.lo is not None and bounds.hi is not None and bounds.lo < bounds.hi:
            options.update(partitionColumn=key, lowerBound=str(bounds.lo), upperBound=str(bounds.hi + 1), numPartitions=str(partitions))
    frame = spark.read.format("jdbc").options(**options).load()
    expected = source_schema(table)
    if frame.columns != expected.fieldNames():
        raise ValueError(f"JDBC schema columns for {table} are {frame.columns}, expected {expected.fieldNames()}")
    return frame.select(*[F.col(field.name).cast(field.dataType).alias(field.name) for field in expected.fields])


def read_source(spark, config: dict, profile: str, batch_id: str, table: str, source_mode: str):
    if source_mode == "file":
        return read_parquet(spark, config, profile, batch_id, table)
    if source_mode != "mixed":
        raise ValueError("source_mode must be file or mixed")
    if table in {"customers", "accounts", "customer_profiles"}:
        return _read_jdbc(spark, config, table, batch_id)
    return read_parquet(spark, config, profile, batch_id, table)

