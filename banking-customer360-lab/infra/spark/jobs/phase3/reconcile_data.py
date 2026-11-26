#!/usr/bin/env python3
"""Reconcile latest Bronze state to Silver and preserve Phase 1 scenario distributions."""

from __future__ import annotations

import json

from pyspark.sql import functions as F

from customer360.cli import parser, validate_args
from customer360.configuration import load_config
from customer360.contracts import FACT_TABLES, TABLE_CONTRACTS
from customer360.manifests import load_manifests
from customer360.quality import assert_results, decimal_sum, result
from customer360.spark_session import create_spark_session
from customer360.transformations import clean_fact
from customer360.writers import append_quality_results


def main() -> None:
    args = validate_args(parser(__doc__, source_mode=False).parse_args())
    config = load_config(args.config)
    spark = create_spark_session(f"customer360-reconcile-{args.batch_id}-{args.run_id}", config)
    try:
        manifests = load_manifests(spark, config, args.profile)
        latest = {table: clean_fact(spark.table(f"`{args.bronze_schema}`.`{table}`"), table).cache() for table in FACT_TABLES}
        silver = {table: spark.table(f"`{args.silver_schema}`.`{table}`").cache() for table in FACT_TABLES}
        checks = []
        for table in FACT_TABLES:
            key = TABLE_CONTRACTS[table]["key"]
            expected, actual = latest[table].select(key).distinct().count(), silver[table].count()
            checks.append(result(args.run_id, args.batch_id, table, "latest_record_count", expected, actual, expected == actual))
        for table, column in (("accounts", "balance"), ("transactions", "amount"), ("loans", "outstanding")):
            expected, actual = decimal_sum(latest[table], column), decimal_sum(silver[table], column)
            checks.append(result(args.run_id, args.batch_id, table, f"sum_{column}", expected, actual, expected == actual))
        for tx_type in ("CREDIT", "DEBIT"):
            condition = (F.col("status") == "SUCCESS") & (F.col("transaction_type") == tx_type)
            expected, actual = decimal_sum(latest["transactions"], "amount", condition), decimal_sum(silver["transactions"], "amount", condition)
            checks.append(result(args.run_id, args.batch_id, "transactions", f"successful_{tx_type.lower()}_total", expected, actual, expected == actual))
        if args.load_type == "full":
            scenario = manifests["scenario_manifest"]
            for item in scenario["hot_accounts"]:
                actual = silver["transactions"].filter(F.col("account_id") == item["account_id"]).count()
                checks.append(result(args.run_id, args.batch_id, "transactions", f"hot_account_{item['account_id']}", item["transaction_count"], actual, item["transaction_count"] == actual))
            overdue = silver["loans"].filter(F.col("overdue_days") > 0).count()
            expected_overdue = scenario["broadcast_join"]["overdue_loan_count"]
            checks.append(result(args.run_id, args.batch_id, "loans", "overdue_distribution", expected_overdue, overdue, expected_overdue == overdue))
            months = silver["transactions"].select("transaction_month").distinct().count()
            expected_months = manifests["dataset_manifest"]["config"]["simulation"]["transaction_history"]["months"]
            checks.append(result(args.run_id, args.batch_id, "transactions", "history_months", expected_months, months, expected_months == months))
        append_quality_results(spark, config, checks)
        assert_results(checks)
        print(json.dumps({"status": "passed", "checks": len(checks), "batch_id": args.batch_id}))
    finally:
        spark.stop()


if __name__ == "__main__":
    main()

