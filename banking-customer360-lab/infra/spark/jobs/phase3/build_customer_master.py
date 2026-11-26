#!/usr/bin/env python3
"""Rebuild the integrated Silver customer current state from delivered Bronze batches."""

from __future__ import annotations

import json

from pyspark.sql import functions as F

from customer360.cli import parser, validate_args
from customer360.configuration import load_config
from customer360.spark_session import create_spark_session
from customer360.transformations import build_customer_master
from customer360.writers import overwrite_silver, table_location


def main() -> None:
    args = validate_args(parser(__doc__, source_mode=False).parse_args())
    config = load_config(args.config)
    spark = create_spark_session(f"customer360-silver-customer-master-{args.batch_id}-{args.run_id}", config)
    try:
        customers = spark.table(f"`{args.bronze_schema}`.`customers`")
        profiles = spark.table(f"`{args.bronze_schema}`.`customer_profiles`")
        if args.load_type == "full":
            delivered = {row._batch_id for row in customers.select("_batch_id").distinct().collect()}
            if delivered - {args.batch_id}:
                raise RuntimeError("Refusing a destructive Full Load after incremental Bronze data; run the explicit reset procedure")
            customers = customers.filter(F.col("_batch_id") == args.batch_id)
            profiles = profiles.filter(F.col("_batch_id") == args.batch_id)
        result = build_customer_master(customers, profiles)
        if args.explain:
            result.explain("formatted")
        before = customers.select("customer_id").distinct().count()
        after = result.count()
        if before != after:
            raise AssertionError(f"customer_master cardinality changed from {before} to {after}")
        overwrite_silver(spark, config, result, "customer_master", args.silver_schema)
        print(json.dumps({"status": "passed", "table": "customer_master", "rows": after,
                          "location": table_location(config, args.silver_schema, "customer_master")}))
    finally:
        spark.stop()


if __name__ == "__main__":
    main()

