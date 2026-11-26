"""Shared command-line arguments for Phase 3 Spark applications."""

from __future__ import annotations

import argparse
import os

from customer360.contracts import validate_batch_id


def parser(description: str, *, load_type: bool = True, source_mode: bool = True) -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=description)
    result.add_argument("--config", default=os.environ.get("PHASE3_CONFIG", "/opt/spark/jobs/phase3/config/phase3.yaml"))
    result.add_argument("--profile", choices=("small", "standard"), default="small")
    result.add_argument("--batch-id", default="batch_01")
    result.add_argument("--run-id", default="manual")
    result.add_argument("--explain", action="store_true")
    if load_type:
        result.add_argument("--load-type", choices=("full", "incremental"), default="full")
    if source_mode:
        result.add_argument("--source-mode", choices=("file", "mixed"), default="file")
    result.add_argument("--bronze-schema", default="bronze")
    result.add_argument("--silver-schema", default="silver")
    return result


def validate_args(args):
    validate_batch_id(args.batch_id)
    if hasattr(args, "load_type"):
        expected = "batch_01" if args.load_type == "full" else "batch_02"
        if args.batch_id != expected:
            raise ValueError(f"{args.load_type} load requires {expected}, received {args.batch_id}")
    return args

