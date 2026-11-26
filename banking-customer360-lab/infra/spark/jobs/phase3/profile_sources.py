#!/usr/bin/env python3
"""Profile the five source deliveries and compare counts with Phase 1 manifests."""

from __future__ import annotations

import json

from pyspark.sql import functions as F

from customer360.cli import parser, validate_args
from customer360.configuration import load_config
from customer360.contracts import TABLE_CONTRACTS
from customer360.manifests import expected_bronze_count, load_manifests
from customer360.readers import read_source
from customer360.spark_session import create_spark_session


TIME_COLUMNS = {
    "customers": ("created_at", "updated_at"), "accounts": ("created_at", "updated_at"),
    "transactions": ("transaction_time", "updated_at"), "customer_profiles": ("updated_at",),
    "loans": ("loan_date", "updated_at"),
}
MONEY_COLUMNS = {"accounts": ("balance",), "transactions": ("amount",),
                 "customer_profiles": ("monthly_income",), "loans": ("loan_amount", "outstanding")}


def profile(frame, table: str) -> dict:
    key = TABLE_CONTRACTS[table]["key"]
    expressions = [F.count("*").alias("rows"), F.countDistinct(key).alias("distinct_keys")]
    for column in frame.columns:
        expressions.append(F.sum(F.when(F.col(column).isNull(), 1).otherwise(0)).alias(f"null__{column}"))
    for column in TIME_COLUMNS[table]:
        expressions.extend([F.min(column).cast("string").alias(f"min__{column}"), F.max(column).cast("string").alias(f"max__{column}")])
    for column in MONEY_COLUMNS.get(table, ()):
        expressions.extend([F.min(column).cast("string").alias(f"min__{column}"), F.max(column).cast("string").alias(f"max__{column}")])
    row = frame.agg(*expressions).first().asDict()
    row["duplicate_business_keys"] = row["rows"] - row["distinct_keys"]
    row["sample"] = frame.limit(3).toJSON().collect()
    return row


def main() -> None:
    args = validate_args(parser(__doc__, load_type=False).parse_args())
    config = load_config(args.config)
    spark = create_spark_session(f"customer360-source-profile-{args.batch_id}-{args.run_id}", config)
    try:
        manifests = load_manifests(spark, config, args.profile)
        frames, report = {}, {}
        for table in TABLE_CONTRACTS:
            frames[table] = read_source(spark, config, args.profile, args.batch_id, table, args.source_mode).cache()
            report[table] = profile(frames[table], table)
            expected = expected_bronze_count(manifests, args.batch_id, table)
            report[table]["manifest_expected_rows"] = expected
            if report[table]["rows"] != expected:
                raise AssertionError(f"{table}: source has {report[table]['rows']} rows, manifest expects {expected}")
        report["relationships"] = {
            "customers_with_accounts": frames["accounts"].select("customer_id").distinct().count(),
            "accounts_with_transactions": frames["transactions"].select("account_id").distinct().count(),
            "customers_with_loans": frames["loans"].select("customer_id").distinct().count(),
            "identity_matches": frames["customers"].select("identity_number").join(frames["customer_profiles"].select("identity_number"), "identity_number").count(),
            "overdue_loans": frames["loans"].filter(F.col("overdue_days") > 0).count(),
        }
        report["top_accounts"] = [row.asDict() for row in frames["transactions"].groupBy("account_id").count().orderBy(F.desc("count")).limit(20).collect()]
        report["transaction_months"] = [row.asDict() for row in frames["transactions"].groupBy(F.date_format("transaction_time", "yyyy-MM").alias("month")).count().orderBy("month").collect()]
        print(json.dumps(report, default=str, sort_keys=True))
    finally:
        spark.stop()


if __name__ == "__main__":
    main()

