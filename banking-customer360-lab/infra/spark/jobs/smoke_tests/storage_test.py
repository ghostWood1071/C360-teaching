#!/usr/bin/env python3
from common import session

spark = session("storage-connectivity-test")
try:
    fs = spark._jvm.org.apache.hadoop.fs.FileSystem.get(spark._jsc.hadoopConfiguration())
    for uri in ("s3a://raw/", "s3a://warehouse/", "s3a://spark-logs/"):
        if not fs.exists(spark._jvm.org.apache.hadoop.fs.Path(uri)):
            raise AssertionError(f"Missing storage path: {uri}")
finally:
    spark.stop()
