"""Silver cleansing and identity integration transformations."""

from __future__ import annotations

from pyspark.sql import Window
from pyspark.sql import functions as F

from customer360.schemas import business_columns


def _payload_hash(frame, columns: list[str]):
    return F.sha2(F.to_json(F.struct(*[F.col(column) for column in columns])), 256)


def latest_by_key(frame, table: str, key: str, timestamp_column: str = "updated_at"):
    columns = [column for column in business_columns(table) if column != key]
    prepared = frame.select(*business_columns(table)).withColumn("_payload_hash", _payload_hash(frame, columns))
    conflicts = (prepared.groupBy(key, timestamp_column)
                 .agg(F.countDistinct("_payload_hash").alias("payloads"))
                 .filter(F.col("payloads") > 1).limit(1).count())
    if conflicts:
        raise ValueError(f"Conflicting {table} payloads share the same {key} and {timestamp_column}")
    window = Window.partitionBy(key).orderBy(F.col(timestamp_column).desc(), F.col("_payload_hash").asc())
    return (prepared.dropDuplicates([key, timestamp_column, "_payload_hash"])
            .withColumn("_row_number", F.row_number().over(window))
            .filter(F.col("_row_number") == 1).drop("_row_number", "_payload_hash"))


def _trim_strings(frame):
    selected = []
    for field in frame.schema.fields:
        selected.append(F.trim(F.col(field.name)).alias(field.name) if field.dataType.simpleString() == "string" else F.col(field.name))
    return frame.select(*selected)


def clean_fact(frame, table: str):
    key = {"accounts": "account_id", "transactions": "transaction_id", "loans": "loan_id"}[table]
    result = _trim_strings(latest_by_key(frame, table, key))
    if table == "accounts":
        result = result.withColumn("account_type", F.upper("account_type")).withColumn("status", F.upper("status"))
    elif table == "transactions":
        result = (result.withColumn("transaction_type", F.upper("transaction_type"))
                  .withColumn("status", F.upper("status"))
                  .withColumn("channel", F.upper("channel"))
                  .withColumn("transaction_month", F.date_format("transaction_time", "yyyy-MM")))
    else:
        result = result.withColumn("loan_type", F.upper("loan_type")).withColumn("status", F.upper("status"))
    return result


def normalized_phone_expression(column):
    compact = F.upper(F.regexp_replace(F.trim(column), "[^A-Za-z0-9+]", ""))
    synthetic_digits = F.regexp_extract(compact, r"^(?:\\+?84|0)?SYN([0-9]{10})$", 1)
    digits = F.regexp_replace(column, "[^0-9]", "")
    local_digits = F.when((F.length(digits) == 11) & digits.startswith("84"), F.concat(F.lit("0"), F.substring(digits, 3, 9))).otherwise(digits)
    return (F.when(column.isNull(), F.lit(None).cast("string"))
            .when(synthetic_digits != "", F.concat(F.lit("+84-SYN-"), synthetic_digits))
            .when(local_digits.rlike(r"^0[0-9]{9}$"), local_digits)
            .otherwise(F.trim(column)))


def build_customer_master(customers, profiles):
    latest_customers = latest_by_key(customers, "customers", "customer_id").alias("c")
    latest_profiles = latest_by_key(profiles, "customer_profiles", "profile_id")
    if latest_profiles.groupBy("identity_number").count().filter(F.col("count") > 1).limit(1).count():
        raise ValueError("CRM identity_number is not unique after latest-record resolution")
    profile = latest_profiles.alias("p")
    joined = latest_customers.join(profile, F.col("c.identity_number") == F.col("p.identity_number"), "left")
    return joined.select(
        F.col("c.customer_id").alias("customer_id"), F.trim(F.col("c.full_name")).alias("full_name"),
        F.col("c.identity_number").alias("identity_number"), F.col("c.date_of_birth").alias("date_of_birth"),
        F.upper(F.col("c.gender")).alias("gender"), F.upper(F.col("c.customer_type")).alias("customer_type"),
        F.col("c.created_at").alias("created_at"), normalized_phone_expression(F.col("p.phone")).alias("phone"),
        F.lower(F.trim(F.col("p.email"))).alias("email"), F.trim(F.col("p.address")).alias("address"),
        F.trim(F.col("p.occupation")).alias("occupation"), F.col("p.monthly_income").cast("decimal(18,2)").alias("monthly_income"),
        F.col("p.updated_at").alias("profile_updated_at"),
        F.greatest(F.col("c.updated_at"), F.coalesce(F.col("p.updated_at"), F.col("c.updated_at"))).alias("updated_at"),
    )

