"""Reusable checks and persistent validation result records."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

from pyspark.sql import functions as F


def result(run_id: str, batch_id: str, table: str, check: str, expected, actual, passed: bool) -> dict:
    return {
        "dag_run_id": run_id,
        "source_batch_id": batch_id,
        "table_name": table,
        "check_name": check,
        "expected_value": str(expected),
        "actual_value": str(actual),
        "status": "PASSED" if passed else "FAILED",
        "execution_timestamp": datetime.now(timezone.utc),
    }


def assert_results(results: list[dict]) -> None:
    failed = [item for item in results if item["status"] == "FAILED"]
    if failed:
        summary = "; ".join(f"{item['table_name']}.{item['check_name']}={item['actual_value']}" for item in failed)
        raise AssertionError(f"Critical data quality checks failed: {summary}")


def uniqueness_result(frame, key: str, run_id: str, batch_id: str, table: str) -> dict:
    counts = frame.agg(F.count("*").alias("rows"), F.countDistinct(key).alias("keys")).first()
    return result(run_id, batch_id, table, "business_key_uniqueness", counts.rows, counts.keys, counts.rows == counts.keys)


def required_key_result(frame, key: str, run_id: str, batch_id: str, table: str) -> dict:
    missing = frame.filter(F.col(key).isNull()).count()
    return result(run_id, batch_id, table, "required_key_complete", 0, missing, missing == 0)


def foreign_key_result(child, parent, child_key: str, parent_key: str, run_id: str, batch_id: str, table: str) -> dict:
    child_keys = child.select(F.col(child_key).alias("_child_key")).distinct()
    parent_keys = parent.select(F.col(parent_key).alias("_parent_key")).distinct()
    invalid = child_keys.join(parent_keys, F.col("_child_key") == F.col("_parent_key"), "left_anti").count()
    return result(run_id, batch_id, table, f"foreign_key_{child_key}", 0, invalid, invalid == 0)


def decimal_sum(frame, column: str, condition=None) -> Decimal:
    selected = frame.filter(condition) if condition is not None else frame
    value = selected.agg(F.sum(column).cast("decimal(38,2)").alias("total")).first().total
    return value if value is not None else Decimal("0.00")


def financial_results(accounts, transactions, loans, run_id: str, batch_id: str) -> list[dict]:
    checks = []
    invalid_accounts = accounts.filter((F.col("balance") < 0) | ((F.col("status") == "CLOSED") & (F.col("balance") != 0))).count()
    checks.append(result(run_id, batch_id, "accounts", "valid_balance", 0, invalid_accounts, invalid_accounts == 0))
    invalid_transactions = transactions.filter(F.col("amount") <= 0).count()
    checks.append(result(run_id, batch_id, "transactions", "positive_amount", 0, invalid_transactions, invalid_transactions == 0))
    invalid_loans = loans.filter((F.col("loan_amount") <= 0) | (F.col("outstanding") < 0) | (F.col("outstanding") > F.col("loan_amount")) | (F.col("overdue_days") < 0)).count()
    checks.append(result(run_id, batch_id, "loans", "valid_financial_values", 0, invalid_loans, invalid_loans == 0))
    return checks


def categorical_results(accounts, transactions, loans, run_id: str, batch_id: str) -> list[dict]:
    specs = [
        (accounts, "accounts", "account_type", ["SAVING", "CURRENT"]),
        (accounts, "accounts", "status", ["ACTIVE", "CLOSED"]),
        (transactions, "transactions", "transaction_type", ["CREDIT", "DEBIT"]),
        (transactions, "transactions", "status", ["SUCCESS", "FAILED"]),
        (loans, "loans", "loan_type", ["HOME", "CAR", "PERSONAL", "BUSINESS"]),
        (loans, "loans", "status", ["ACTIVE", "CLOSED"]),
    ]
    output = []
    for frame, table, column, allowed in specs:
        invalid = frame.filter(~F.col(column).isin(allowed)).count()
        output.append(result(run_id, batch_id, table, f"valid_{column}", 0, invalid, invalid == 0))
    return output

