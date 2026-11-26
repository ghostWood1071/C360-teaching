"""Explicit Spark schemas derived from the Phase 1 schema manifest."""

from __future__ import annotations

from pyspark.sql.types import (
    DateType, DecimalType, IntegerType, LongType, StringType, StructField, StructType, TimestampType,
)

from customer360.contracts import TABLE_CONTRACTS

TYPE_MAP = {
    "long": LongType(), "string": StringType(), "date": DateType(),
    "timestamp": TimestampType(), "decimal(18,2)": DecimalType(18, 2), "integer": IntegerType(),
}


def source_schema(table: str) -> StructType:
    return StructType([
        StructField(name, TYPE_MAP[data_type], nullable)
        for name, data_type, nullable in TABLE_CONTRACTS[table]["columns"]
    ])


def business_columns(table: str) -> list[str]:
    return [column[0] for column in TABLE_CONTRACTS[table]["columns"]]

