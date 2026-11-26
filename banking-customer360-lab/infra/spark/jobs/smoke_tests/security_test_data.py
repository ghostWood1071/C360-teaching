#!/usr/bin/env python3
"""Create a tiny synthetic table only for Ranger policy demonstrations."""

from common import session

ROWS = [
    (1, "INDIVIDUAL", "FICTIONAL-ABC-0001", "+84-SYN-0000000001", "one@example.com", 25_000_000, "NORTH"),
    (2, "CORPORATE", "FICTIONAL-ABC-0002", "+84-SYN-0000000002", "two@example.com", 80_000_000, "SOUTH"),
    (3, "INDIVIDUAL", "FICTIONAL-ABC-0003", "+84-SYN-0000000003", "three@example.com", 35_000_000, "CENTRAL"),
]
COLUMNS = ["customer_id", "customer_type", "identity_number", "phone", "email", "monthly_income", "risk_region"]


def write_table(spark, schema: str) -> None:
    location = f"s3a://warehouse/{schema}/security_customers"
    spark.sql(f"CREATE DATABASE IF NOT EXISTS {schema} LOCATION 's3a://warehouse/{schema}'")
    frame = spark.createDataFrame(ROWS, COLUMNS)
    frame.write.format("delta").mode("overwrite").option("overwriteSchema", "true").save(location)
    spark.sql(f"DROP TABLE IF EXISTS {schema}.security_customers")
    spark.sql(f"CREATE TABLE {schema}.security_customers USING DELTA LOCATION '{location}'")


spark = session("security-test-data")
try:
    for layer in ("bronze", "silver", "gold"):
        write_table(spark, layer)
finally:
    spark.stop()
