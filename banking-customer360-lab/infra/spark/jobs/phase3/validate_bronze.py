#!/usr/bin/env python3
"""Validate Bronze schema, metadata, counts and expected delivery duplicates."""

from __future__ import annotations

import json

from pyspark.sql import functions as F

from customer360.cli import parser, validate_args
from customer360.configuration import load_config
from customer360.contracts import TABLE_CONTRACTS
from customer360.manifests import expected_bronze_count, load_manifests
from customer360.quality import assert_results, result
from customer360.schemas import business_columns
from customer360.spark_session import create_spark_session
from customer360.writers import append_quality_results


def main() -> None:
    argument_parser = parser(__doc__, source_mode=False)
    argument_parser.add_argument("--enabled", choices=("true", "false"), default="true")
    args = validate_args(argument_parser.parse_args())
    if args.enabled == "false":
        print(json.dumps({"status": "skipped", "reason": "quality checks disabled"}))
        return
    config = load_config(args.config)
    spark = create_spark_session(f"customer360-validate-bronze-{args.batch_id}-{args.run_id}", config)
    try:
        manifests = load_manifests(spark, config, args.profile)
        checks = []
        for table, contract in TABLE_CONTRACTS.items():
            frame = spark.table(f"`{args.bronze_schema}`.`{table}`").filter(F.col("_batch_id") == args.batch_id)
            actual = frame.count()
            expected = expected_bronze_count(manifests, args.batch_id, table)
            checks.append(result(args.run_id, args.batch_id, table, "source_record_count", expected, actual, actual == expected))
            missing_metadata = frame.filter(F.col("_source_system").isNull() | F.col("_batch_id").isNull() | F.col("_ingested_at").isNull()).count()
            checks.append(result(args.run_id, args.batch_id, table, "metadata_complete", 0, missing_metadata, missing_metadata == 0))
            expected_columns = set(business_columns(table)) | {"_source_system", "_batch_id", "_ingested_at"}
            checks.append(result(args.run_id, args.batch_id, table, "schema_columns", sorted(expected_columns), sorted(frame.columns), expected_columns == set(frame.columns)))
            sources = frame.filter(F.col("_source_system") != contract["source_system"]).count()
            checks.append(result(args.run_id, args.batch_id, table, "source_system", 0, sources, sources == 0))
        tx = spark.table(f"`{args.bronze_schema}`.`transactions`").filter(F.col("_batch_id") == args.batch_id)
        duplicates = tx.count() - tx.select("transaction_id").distinct().count()
        expected_duplicates = manifests["data_quality_manifest"]["raw_delivery"][args.batch_id]["duplicate_events"]
        checks.append(result(args.run_id, args.batch_id, "transactions", "expected_delivery_duplicates", expected_duplicates, duplicates, duplicates == expected_duplicates))
        append_quality_results(spark, config, checks)
        assert_results(checks)
        print(json.dumps({"status": "passed", "checks": len(checks), "batch_id": args.batch_id}))
    finally:
        spark.stop()


if __name__ == "__main__":
    main()

