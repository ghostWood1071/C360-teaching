#!/usr/bin/env python3
"""Load deterministic batch staging tables for the optional mixed source mode."""

from __future__ import annotations

import json
import os

from customer360.cli import parser, validate_args
from customer360.configuration import load_config
from customer360.readers import read_parquet
from customer360.configuration import raw_root
from customer360.schemas import source_schema
from customer360.spark_session import create_spark_session


def main() -> None:
    args = validate_args(parser(__doc__, load_type=False, source_mode=False).parse_args())
    config = load_config(args.config)
    spark = create_spark_session(f"customer360-jdbc-stage-{args.batch_id}", config)
    try:
        staged = {}
        for table, system in (("customers", "core"), ("accounts", "core"), ("transactions", "core"), ("customer_profiles", "crm")):
            if system == "core":
                url, user, password = os.environ["CORE_BANKING_JDBC_URL"], os.environ["CORE_BANKING_DB_USER"], os.environ["CORE_BANKING_DB_PASSWORD"]
            else:
                url, user, password = os.environ["CRM_JDBC_URL"], os.environ["CRM_DB_USER"], os.environ["CRM_DB_PASSWORD"]
            target = f"{config['jdbc'].get('staging_table_prefix', 'phase3')}_{args.batch_id}_{table}"
            if table == "transactions":
                path = f"{raw_root(config, args.profile)}/{args.batch_id}/core_banking/transactions"
                frame = spark.read.schema(source_schema(table)).parquet(path)
            else:
                frame = read_parquet(spark, config, args.profile, args.batch_id, table)
            (frame.write.format("jdbc").mode("overwrite").option("url", url).option("dbtable", target)
             .option("user", user).option("password", password).option("driver", "org.postgresql.Driver").save())
            staged[target] = frame.count()
        print(json.dumps({"status": "passed", "staged": staged}, sort_keys=True))
    finally:
        spark.stop()


if __name__ == "__main__":
    main()

