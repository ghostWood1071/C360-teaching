#!/usr/bin/env python3
import argparse
import json

from common import append, create, identifiers, session, validate


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=("create", "append", "validate"))
    parser.add_argument("--run-id", required=True)
    args = parser.parse_args()
    spark = session(f"delta-{args.action}-{args.run_id}")
    try:
        {"create": create, "append": append, "validate": validate}[args.action](spark, args.run_id)
        _, qualified, location = identifiers(args.run_id)
        print(json.dumps({"action": args.action, "table": qualified, "location": location, "status": "passed"}))
    finally:
        spark.stop()


if __name__ == "__main__":
    main()
