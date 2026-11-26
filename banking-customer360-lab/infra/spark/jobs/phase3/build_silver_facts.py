#!/usr/bin/env python3
"""Build or incrementally merge accounts, transactions and loans into Silver."""

from __future__ import annotations

import json

from pyspark.sql import functions as F

from customer360.cli import parser, validate_args
from customer360.configuration import load_config
from customer360.contracts import FACT_TABLES, TABLE_CONTRACTS
from customer360.spark_session import create_spark_session
from customer360.transformations import clean_fact
from customer360.writers import merge_silver, overwrite_silver


def main() -> None:
    args = validate_args(parser(__doc__, source_mode=False).parse_args())
    config = load_config(args.config)
    spark = create_spark_session(f"customer360-silver-facts-{args.batch_id}-{args.run_id}", config)
    try:
        counts = {}
        for table in FACT_TABLES:
            bronze = spark.table(f"`{args.bronze_schema}`.`{table}`")
            if args.load_type == "full":
                delivered = {row._batch_id for row in bronze.select("_batch_id").distinct().collect()}
                if delivered - {args.batch_id}:
                    raise RuntimeError("Refusing Full Load over previously delivered incremental data; use the explicit reset procedure")
                source = bronze.filter(F.col("_batch_id") == args.batch_id)
            else:
                source = bronze.filter(F.col("_batch_id") == args.batch_id)
            silver = clean_fact(source, table)
            if args.explain:
                silver.explain("formatted")
            key = TABLE_CONTRACTS[table]["key"]
            if args.load_type == "full":
                overwrite_silver(spark, config, silver, table, args.silver_schema)
            else:
                merge_silver(spark, config, silver, table, args.silver_schema, key)
            counts[table] = spark.table(f"`{args.silver_schema}`.`{table}`").count()
        print(json.dumps({"status": "passed", "load_type": args.load_type, "rows": counts}, sort_keys=True))
    finally:
        spark.stop()


if __name__ == "__main__":
    main()

