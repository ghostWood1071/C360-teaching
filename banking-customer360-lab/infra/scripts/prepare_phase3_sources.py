#!/usr/bin/env python3
"""Upload existing Phase 1 Parquet deliveries and manifests to MinIO without regeneration."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
TABLE_PATHS = (
    "batch_01/core_banking/customers", "batch_01/core_banking/accounts",
    "batch_01/core_banking/transactions",
    "batch_01/crm/customer_profiles", "batch_01/loan_system/loans",
    "batch_02/core_banking/customers", "batch_02/core_banking/accounts",
    "batch_02/core_banking/transactions",
    "batch_02/crm/customer_profiles", "batch_02/loan_system/loans",
    "raw_delivery/batch_01/transactions", "raw_delivery/batch_02/transactions",
    "metadata",
)


def load_env(path: Path) -> dict[str, str]:
    values = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            values[key] = value
    return values


def run(command: list[str], environment: dict[str, str] | None = None) -> None:
    subprocess.run(command, cwd=ROOT, env=environment, check=True)


def mirror_source(profile: str, env: dict[str, str]) -> None:
    data_root = (ROOT / "data" / profile).resolve()
    if not (data_root / "metadata" / "dataset_manifest.json").is_file():
        raise FileNotFoundError(f"Generated Phase 1 data not found at {data_root}")
    image = f"customer360-minio:{env.get('MINIO_VERSION', 'RELEASE.2025-10-15T17-29-55Z')}"
    host = f"http://{env['PLATFORM_S3_ACCESS_KEY']}:{env['PLATFORM_S3_SECRET_KEY']}@minio:9000"
    for relative in TABLE_PATHS:
        source = f"/source/{relative}"
        target = f"c360/raw/{profile}/{relative}"
        run([
            "docker", "run", "--rm", "--network", env.get("DOCKER_NETWORK_NAME", "customer360-network"),
            "-e", f"MC_HOST_c360={host}", "-v", f"{data_root}:/source:ro", image,
            "mc", "mirror", "--overwrite", source, target,
        ])


def validate_local_contract(profile: str) -> dict:
    root = ROOT / "data" / profile
    dataset = json.loads((root / "metadata/dataset_manifest.json").read_text(encoding="utf-8"))
    incremental = json.loads((root / "metadata/incremental_manifest.json").read_text(encoding="utf-8"))
    quality = json.loads((root / "metadata/data_quality_manifest.json").read_text(encoding="utf-8"))
    parquet_files = {path: len(list((root / path).glob("*.parquet"))) for path in TABLE_PATHS if path != "metadata"}
    if any(count == 0 for count in parquet_files.values()):
        raise AssertionError(f"Missing source Parquet files: {parquet_files}")
    return {"profile": profile, "batch_01": dataset["expected_counts"],
            "batch_02": incremental["expected_counts_after_batch_02"],
            "raw_delivery": quality["raw_delivery"], "parquet_files": parquet_files}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", choices=("small", "standard"), default="small")
    parser.add_argument("--env-file", default=str(ROOT / ".env"))
    parser.add_argument("--load-jdbc", action="store_true")
    parser.add_argument("--batch-id", choices=("batch_01", "batch_02"), default="batch_01")
    args = parser.parse_args()
    env_path = Path(args.env_file)
    if not env_path.is_file():
        raise FileNotFoundError("Run make setup before source preparation")
    contract = validate_local_contract(args.profile)
    env = load_env(env_path)
    mirror_source(args.profile, env)
    if args.load_jdbc:
        runtime = os.environ.copy()
        runtime.update(env)
        runtime["CORE_BANKING_JDBC_URL"] = f"jdbc:postgresql://postgres:5432/{env['CORE_BANKING_DB_NAME']}"
        runtime["CRM_JDBC_URL"] = f"jdbc:postgresql://postgres:5432/{env['CRM_DB_NAME']}"
        compose = ["docker", "compose", "--env-file", str(env_path), "-f", "infra/compose.yaml",
                   "-f", "infra/compose.sources.yaml"]
        run([*compose, "run", "--rm", "source-db-init"], runtime)
        run([*compose, "run", "--rm", "spark-runner", "spark-submit",
             "/opt/spark/jobs/phase3/prepare_jdbc_sources.py", "--profile", args.profile,
             "--batch-id", args.batch_id], runtime)
    print(json.dumps({"status": "prepared", **contract}, indent=2, sort_keys=True))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"Phase 3 source preparation failed: {exc}", file=sys.stderr)
        raise

