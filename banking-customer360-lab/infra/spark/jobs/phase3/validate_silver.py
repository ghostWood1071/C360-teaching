#!/usr/bin/env python3
"""Validate Silver keys, foreign keys, financial rules and identity integration."""

from __future__ import annotations

import json

from pyspark.sql import functions as F

from customer360.cli import parser, validate_args
from customer360.configuration import load_config
from customer360.quality import (
    assert_results, categorical_results, financial_results, foreign_key_result,
    required_key_result, result, uniqueness_result,
)
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
    spark = create_spark_session(f"customer360-validate-silver-{args.batch_id}-{args.run_id}", config)
    try:
        customer_master = spark.table(f"`{args.silver_schema}`.`customer_master`").cache()
        accounts = spark.table(f"`{args.silver_schema}`.`accounts`").cache()
        transactions = spark.table(f"`{args.silver_schema}`.`transactions`").cache()
        loans = spark.table(f"`{args.silver_schema}`.`loans`").cache()
        tables = [(customer_master, "customer_master", "customer_id"), (accounts, "accounts", "account_id"),
                  (transactions, "transactions", "transaction_id"), (loans, "loans", "loan_id")]
        checks = []
        for frame, table, key in tables:
            checks.extend([uniqueness_result(frame, key, args.run_id, args.batch_id, table),
                           required_key_result(frame, key, args.run_id, args.batch_id, table)])
        checks.extend([
            foreign_key_result(accounts, customer_master, "customer_id", "customer_id", args.run_id, args.batch_id, "accounts"),
            foreign_key_result(transactions, accounts, "account_id", "account_id", args.run_id, args.batch_id, "transactions"),
            foreign_key_result(loans, customer_master, "customer_id", "customer_id", args.run_id, args.batch_id, "loans"),
        ])
        checks.extend(financial_results(accounts, transactions, loans, args.run_id, args.batch_id))
        checks.extend(categorical_results(accounts, transactions, loans, args.run_id, args.batch_id))
        bronze_customers = spark.table(f"`{args.bronze_schema}`.`customers`")
        latest_customer_count = bronze_customers.select("customer_id").distinct().count()
        actual_customer_count = customer_master.count()
        checks.append(result(args.run_id, args.batch_id, "customer_master", "customer_cardinality", latest_customer_count, actual_customer_count, latest_customer_count == actual_customer_count))
        duplicate_identity = customer_master.groupBy("identity_number").count().filter(F.col("count") > 1).count()
        checks.append(result(args.run_id, args.batch_id, "customer_master", "identity_unique", 0, duplicate_identity, duplicate_identity == 0))
        append_quality_results(spark, config, checks)
        assert_results(checks)
        print(json.dumps({"status": "passed", "checks": len(checks), "rows": {name: frame.count() for frame, name, _ in tables}}, sort_keys=True))
    finally:
        spark.stop()


if __name__ == "__main__":
    main()

