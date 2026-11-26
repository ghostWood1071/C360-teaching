#!/usr/bin/env python3
import argparse
import json

from common import identifiers, merge, session


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", required=True)
    args = parser.parse_args()
    spark = session(f"delta-merge-{args.run_id}")
    try:
        merge(spark, args.run_id)
        print(json.dumps({"action": "merge", "table": identifiers(args.run_id)[1], "status": "passed"}))
    finally:
        spark.stop()


if __name__ == "__main__":
    main()
