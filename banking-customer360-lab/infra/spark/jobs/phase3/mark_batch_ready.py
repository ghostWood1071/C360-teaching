#!/usr/bin/env python3
"""Persist the reconciled pipeline-batch readiness marker idempotently."""

from __future__ import annotations

from datetime import datetime, timezone
import json

from delta.tables import DeltaTable

from customer360.cli import parser, validate_args
from customer360.configuration import load_config
from customer360.spark_session import create_spark_session
from customer360.writers import register_delta_table, table_location


def main() -> None:
    args = validate_args(parser(__doc__, source_mode=False).parse_args())
    config = load_config(args.config)
    spark = create_spark_session(f"customer360-mark-ready-{args.batch_id}-{args.run_id}", config)
    try:
        frame = spark.createDataFrame([{
            "batch_id": args.batch_id, "load_type": args.load_type, "status": "READY",
            "dag_run_id": args.run_id, "ready_at": datetime.now(timezone.utc),
        }])
        location = table_location(config, "quality", "pipeline_batches")
        if DeltaTable.isDeltaTable(spark, location):
            frame.write.format("delta").mode("overwrite").option("replaceWhere", f"batch_id = '{args.batch_id}'").save(location)
        else:
            frame.write.format("delta").mode("errorifexists").partitionBy("batch_id").save(location)
        register_delta_table(spark, config, "quality", "pipeline_batches")
        print(json.dumps({"status": "READY", "batch_id": args.batch_id}))
    finally:
        spark.stop()


if __name__ == "__main__":
    main()

