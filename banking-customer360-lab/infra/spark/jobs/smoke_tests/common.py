"""Shared deterministic Delta infrastructure smoke-test logic."""

from __future__ import annotations

import re

from delta import DeltaTable
from pyspark.sql import SparkSession

EXPECTED = [(1, "alpha", 100), (2, "beta-updated", 250), (3, "gamma", 300), (4, "delta", 400)]


def run_name(value: str) -> str:
    result = re.sub(r"[^a-z0-9_]", "_", value.lower())[-48:]
    if not result or not result[0].isalpha():
        result = f"run_{result}"
    return result


def identifiers(run_id: str) -> tuple[str, str, str]:
    table = f"infra_{run_name(run_id)}"
    return table, f"smoke_test.{table}", f"s3a://warehouse/smoke_test/{table}"


def session(application_name: str) -> SparkSession:
    return SparkSession.builder.appName(application_name).enableHiveSupport().getOrCreate()


def create(spark: SparkSession, run_id: str) -> None:
    _, qualified, location = identifiers(run_id)
    spark.sql("CREATE DATABASE IF NOT EXISTS smoke_test LOCATION 's3a://warehouse/smoke_test'")
    spark.sql(f"DROP TABLE IF EXISTS {qualified}")
    path = spark._jvm.org.apache.hadoop.fs.Path(location)
    fs = path.getFileSystem(spark._jsc.hadoopConfiguration())
    fs.delete(path, True)
    frame = spark.createDataFrame([(1, "alpha", 100), (2, "beta", 200)], ["id", "name", "amount"])
    frame.write.format("delta").mode("errorifexists").save(location)
    spark.sql(
        f"CREATE TABLE {qualified} (id BIGINT, name STRING, amount BIGINT) USING DELTA LOCATION '{location}'"
    )
    if spark.table(qualified).count() != 2:
        raise AssertionError("CREATE did not produce two rows")


def append(spark: SparkSession, run_id: str) -> None:
    _, qualified, _ = identifiers(run_id)
    spark.createDataFrame([(3, "gamma", 300)], ["id", "name", "amount"]).write.format("delta").mode(
        "append"
    ).saveAsTable(qualified)
    if spark.table(qualified).count() != 3:
        raise AssertionError("APPEND did not produce three rows")


def merge(spark: SparkSession, run_id: str) -> None:
    _, qualified, location = identifiers(run_id)
    source = spark.createDataFrame([(2, "beta-updated", 250), (4, "delta", 400)], ["id", "name", "amount"])
    DeltaTable.forPath(spark, location).alias("target").merge(
        source.alias("source"), "target.id = source.id"
    ).whenMatchedUpdateAll().whenNotMatchedInsertAll().execute()
    if spark.table(qualified).count() != 4:
        raise AssertionError("MERGE did not produce four rows")


def validate(spark: SparkSession, run_id: str) -> None:
    _, qualified, location = identifiers(run_id)
    actual = [tuple(row) for row in spark.sql(f"SELECT id, name, amount FROM {qualified} ORDER BY id").collect()]
    if actual != EXPECTED:
        raise AssertionError(f"Current Delta rows {actual!r} differ from {EXPECTED!r}")
    version_zero = [
        tuple(row)
        for row in spark.read.format("delta").option("versionAsOf", 0).load(location).orderBy("id").collect()
    ]
    if version_zero != [(1, "alpha", 100), (2, "beta", 200)]:
        raise AssertionError(f"Delta time travel returned {version_zero!r}")
    history = DeltaTable.forPath(spark, location).history().collect()
    if len(history) < 3:
        raise AssertionError(f"Expected at least three Delta commits, got {len(history)}")
    spark.sql(f"DESCRIBE HISTORY {qualified}").collect()
