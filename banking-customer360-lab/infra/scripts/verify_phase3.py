#!/usr/bin/env python3
"""Run static Phase 3 verification that does not require a live Docker stack."""

from __future__ import annotations

import ast
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]


def main() -> None:
    required = [
        "infra/spark/jobs/phase3/profile_sources.py", "infra/spark/jobs/phase3/ingest_bronze.py",
        "infra/spark/jobs/phase3/build_customer_master.py", "infra/spark/jobs/phase3/build_silver_facts.py",
        "infra/spark/jobs/phase3/validate_bronze.py", "infra/spark/jobs/phase3/validate_silver.py",
        "infra/spark/jobs/phase3/reconcile_data.py", "infra/airflow/dags/customer360_ingestion_pipeline.py",
    ]
    missing = [path for path in required if not (ROOT / path).is_file()]
    if missing:
        raise AssertionError(f"Missing Phase 3 files: {missing}")
    for path in required:
        ast.parse((ROOT / path).read_text(encoding="utf-8"), filename=path)
    result = subprocess.run([sys.executable, "-m", "pytest", "-q", "infra/tests"], cwd=ROOT)
    if result.returncode:
        raise SystemExit(result.returncode)
    print("Phase 3 static verification passed")


if __name__ == "__main__":
    main()

