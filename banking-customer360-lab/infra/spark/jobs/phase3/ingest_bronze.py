#!/usr/bin/env python3
"""Ingest one stable source delivery batch into five Bronze Delta tables."""

from __future__ import annotations

import json

from pyspark.sql import functions as F

from customer360.cli import parser, validate_args
from customer360.configuration import load_config
from customer360.contracts import TABLE_CONTRACTS
from customer360.readers import read_source
from customer360.spark_session import create_spark_session
from customer360.writers import write_bronze_batch


def main() -> None:
    argument_parser = parser(__doc__)
    argument_parser.add_argument("--inject-failure", choices=("true", "false"), default="false")
    args = validate_args(argument_parser.parse_args())
    config = load_config(args.config)
    spark = create_spark_session(f"customer360-bronze-{args.batch_id}-{args.run_id}", config)
    try:
        summary = {}
        for table, contract in TABLE_CONTRACTS.items():
            source = read_source(spark, config, args.profile, args.batch_id, table, args.source_mode)
            bronze = (source.withColumn("_source_system", F.lit(contract["source_system"]))
                      .withColumn("_batch_id", F.lit(args.batch_id))
                      .withColumn("_ingested_at", F.current_timestamp()))
            if args.explain:
                bronze.explain("formatted")
            summary[table] = write_bronze_batch(spark, config, bronze, table, args.bronze_schema, args.batch_id)
        if args.inject_failure == "true":
            raise RuntimeError("Intentional failure after Bronze commit; disable inject_failure to recover")
        print(json.dumps({"status": "passed", "batch_id": args.batch_id, "rows": summary}, sort_keys=True))
    finally:
        spark.stop()


if __name__ == "__main__":
    main()

