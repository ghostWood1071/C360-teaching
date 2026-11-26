"""Spark session construction for independently executable jobs."""

from __future__ import annotations

from pyspark.sql import SparkSession


def create_spark_session(application_name: str, config: dict) -> SparkSession:
    spark = SparkSession.builder.appName(application_name).enableHiveSupport().getOrCreate()
    spark.sparkContext.setLogLevel("WARN")
    spark.conf.set("spark.sql.session.timeZone", config["pipeline"].get("timezone", "UTC"))
    spark.conf.set("spark.sql.adaptive.enabled", str(config["spark"].get("adaptive_enabled", True)).lower())
    return spark

