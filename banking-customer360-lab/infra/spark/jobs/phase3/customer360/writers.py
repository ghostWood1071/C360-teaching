"""Delta writers with batch-level idempotency and current-state merge semantics."""

from __future__ import annotations

from delta.tables import DeltaTable
from pyspark.sql import functions as F


def table_location(config: dict, schema: str, table: str) -> str:
    root = config["storage"]["warehouse_root"].rstrip("/")
    if schema in {"bronze", "silver", "quality"}:
        return f"{root}/{schema}/{table}"
    return f"{root}/labs/{schema}/{table}"


def ensure_schema(spark, config: dict, schema: str) -> None:
    root = config["storage"]["warehouse_root"].rstrip("/")
    location = f"{root}/{schema}" if schema in {"bronze", "silver", "quality"} else f"{root}/labs/{schema}"
    spark.sql(f"CREATE DATABASE IF NOT EXISTS `{schema}` LOCATION '{location}'")


def register_delta_table(spark, config: dict, schema: str, table: str) -> None:
    ensure_schema(spark, config, schema)
    location = table_location(config, schema, table)
    spark.sql(f"CREATE TABLE IF NOT EXISTS `{schema}`.`{table}` USING DELTA LOCATION '{location}'")


def write_bronze_batch(spark, config: dict, frame, table: str, schema: str, batch_id: str) -> int:
    invalid = frame.filter(F.col("_batch_id") != F.lit(batch_id)).limit(1).count()
    if invalid:
        raise ValueError(f"Incoming {table} rows do not all belong to {batch_id}")
    count = frame.count()
    location = table_location(config, schema, table)
    if DeltaTable.isDeltaTable(spark, location):
        (frame.write.format("delta").mode("overwrite")
         .option("replaceWhere", f"_batch_id = '{batch_id}'").save(location))
    else:
        frame.write.format("delta").mode("errorifexists").partitionBy("_batch_id").save(location)
    register_delta_table(spark, config, schema, table)
    actual = spark.read.format("delta").load(location).filter(F.col("_batch_id") == batch_id).count()
    if actual != count:
        raise AssertionError(f"Bronze retry-safe write expected {count} {table} rows, found {actual}")
    return count


def overwrite_silver(spark, config: dict, frame, table: str, schema: str) -> None:
    location = table_location(config, schema, table)
    frame.write.format("delta").mode("overwrite").option("overwriteSchema", "true").save(location)
    register_delta_table(spark, config, schema, table)


def merge_silver(spark, config: dict, frame, table: str, schema: str, key: str) -> None:
    if frame.groupBy(key).count().filter(F.col("count") > 1).limit(1).count():
        raise ValueError(f"MERGE source for {table} has duplicate {key}")
    location = table_location(config, schema, table)
    if not DeltaTable.isDeltaTable(spark, location):
        overwrite_silver(spark, config, frame, table, schema)
        return
    target = DeltaTable.forPath(spark, location)
    (target.alias("t").merge(frame.alias("s"), f"t.{key} = s.{key}")
     .whenMatchedUpdateAll(condition="s.updated_at > t.updated_at")
     .whenNotMatchedInsertAll().execute())
    register_delta_table(spark, config, schema, table)


def append_quality_results(spark, config: dict, rows: list[dict], schema: str = "quality") -> None:
    if not rows:
        return
    location = table_location(config, schema, "validation_results")
    frame = spark.createDataFrame(rows)
    frame.write.format("delta").mode("append").save(location)
    register_delta_table(spark, config, schema, "validation_results")

