"""Pure data contracts shared by runtime code and unit tests."""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping

BATCH_PATTERN = re.compile(r"^batch_[0-9]{2}$")

TABLE_CONTRACTS = {
    "customers": {
        "source_system": "core_banking",
        "key": "customer_id",
        "columns": [
            ("customer_id", "long", False), ("full_name", "string", False),
            ("identity_number", "string", False), ("date_of_birth", "date", True),
            ("gender", "string", True), ("customer_type", "string", False),
            ("created_at", "timestamp", False), ("updated_at", "timestamp", False),
        ],
    },
    "accounts": {
        "source_system": "core_banking", "key": "account_id",
        "columns": [
            ("account_id", "long", False), ("customer_id", "long", False),
            ("account_type", "string", False), ("balance", "decimal(18,2)", False),
            ("status", "string", False), ("created_at", "timestamp", False),
            ("updated_at", "timestamp", False),
        ],
    },
    "transactions": {
        "source_system": "core_banking", "key": "transaction_id",
        "columns": [
            ("transaction_id", "long", False), ("account_id", "long", False),
            ("transaction_type", "string", False), ("amount", "decimal(18,2)", False),
            ("transaction_time", "timestamp", False), ("channel", "string", False),
            ("merchant_category", "string", False), ("merchant_name", "string", False),
            ("description", "string", False), ("reference_number", "string", False),
            ("status", "string", False), ("updated_at", "timestamp", False),
        ],
    },
    "customer_profiles": {
        "source_system": "crm", "key": "profile_id",
        "columns": [
            ("profile_id", "long", False), ("identity_number", "string", False),
            ("phone", "string", True), ("email", "string", True),
            ("address", "string", True), ("occupation", "string", True),
            ("monthly_income", "decimal(18,2)", True), ("updated_at", "timestamp", False),
        ],
    },
    "loans": {
        "source_system": "loan_system", "key": "loan_id",
        "columns": [
            ("loan_id", "long", False), ("customer_id", "long", False),
            ("loan_type", "string", False), ("loan_amount", "decimal(18,2)", False),
            ("outstanding", "decimal(18,2)", False), ("overdue_days", "integer", False),
            ("loan_date", "date", False), ("status", "string", False),
            ("updated_at", "timestamp", False),
        ],
    },
}

FACT_TABLES = ("accounts", "transactions", "loans")


def validate_batch_id(batch_id: str) -> str:
    if not BATCH_PATTERN.fullmatch(batch_id):
        raise ValueError("batch_id must use the stable form batch_NN")
    return batch_id


def normalize_phone_value(value: str | None) -> str | None:
    """Normalize real Vietnamese examples and the lab's explicit SYN phones."""
    if value is None:
        return None
    compact = re.sub(r"[^A-Za-z0-9+]", "", value).upper()
    synthetic = re.fullmatch(r"(?:\+?84|0)?SYN([0-9]{10})", compact)
    if synthetic:
        return f"+84-SYN-{synthetic.group(1)}"
    digits = re.sub(r"\D", "", value)
    if digits.startswith("84") and len(digits) == 11:
        digits = "0" + digits[2:]
    if re.fullmatch(r"0[0-9]{9}", digits):
        return digits
    return value.strip() or None


def resolve_latest_records(records: Iterable[Mapping], key: str, timestamp: str = "updated_at") -> list[dict]:
    """Small pure reference model used to test the Spark latest-record contract."""
    grouped: dict[object, list[dict]] = {}
    for record in records:
        item = dict(record)
        grouped.setdefault(item[key], []).append(item)
    output = []
    for business_key, items in grouped.items():
        latest_timestamp = max(item[timestamp] for item in items)
        latest = [item for item in items if item[timestamp] == latest_timestamp]
        payloads = {tuple(sorted(item.items())) for item in latest}
        if len(payloads) > 1:
            raise ValueError(f"Conflicting payloads for {key}={business_key} at {latest_timestamp}")
        output.append(latest[0])
    return sorted(output, key=lambda item: item[key])


def merge_latest_records(existing: Iterable[Mapping], incoming: Iterable[Mapping], key: str) -> list[dict]:
    return resolve_latest_records([*map(dict, existing), *map(dict, incoming)], key)

