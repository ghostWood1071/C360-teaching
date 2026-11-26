#!/usr/bin/env python3
from common import session

spark = session("hive-catalog-connectivity-test")
try:
    spark.sql("CREATE DATABASE IF NOT EXISTS smoke_test LOCATION 's3a://warehouse/smoke_test'")
    if "smoke_test" not in {row.namespace for row in spark.sql("SHOW DATABASES").collect()}:
        raise AssertionError("Hive Metastore did not retain the smoke_test namespace")
finally:
    spark.stop()
