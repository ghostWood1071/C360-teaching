from __future__ import annotations

from datetime import datetime, timezone
import importlib.util
import json
from pathlib import Path
import sys

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
PHASE3 = ROOT / "infra/spark/jobs/phase3"
sys.path.insert(0, str(PHASE3))

from customer360.contracts import (  # noqa: E402
    TABLE_CONTRACTS, merge_latest_records, normalize_phone_value,
    resolve_latest_records, validate_batch_id,
)


def test_source_contract_matches_phase1_schema_manifest() -> None:
    actual = json.loads((ROOT / "data/small/metadata/schema_manifest.json").read_text())
    assert set(actual) == set(TABLE_CONTRACTS)
    for table, contract in TABLE_CONTRACTS.items():
        assert [item["name"] for item in actual[table]] == [item[0] for item in contract["columns"]]


def test_stable_batch_identifier() -> None:
    assert validate_batch_id("batch_01") == "batch_01"
    assert validate_batch_id("batch_02") == "batch_02"
    with pytest.raises(ValueError):
        validate_batch_id("latest")


@pytest.mark.parametrize(("source", "expected"), [
    ("0900000123", "0900000123"), ("+84 900 000 123", "0900000123"),
    ("090-000-0123", "0900000123"), ("0 SYN 0000000021", "+84-SYN-0000000021"),
    (None, None),
])
def test_phone_normalization(source, expected) -> None:
    assert normalize_phone_value(source) == expected


def test_transaction_deduplication_and_conflict_detection() -> None:
    ts = datetime(2027, 1, 1, tzinfo=timezone.utc)
    identical = [{"transaction_id": 1, "updated_at": ts, "status": "SUCCESS"}] * 2
    assert len(resolve_latest_records(identical, "transaction_id")) == 1
    with pytest.raises(ValueError):
        resolve_latest_records([
            {"transaction_id": 1, "updated_at": ts, "status": "SUCCESS"},
            {"transaction_id": 1, "updated_at": ts, "status": "FAILED"},
        ], "transaction_id")


def test_incremental_replay_and_old_update_do_not_change_state() -> None:
    old = datetime(2027, 1, 1, tzinfo=timezone.utc)
    new = datetime(2027, 1, 2, tzinfo=timezone.utc)
    existing = [{"account_id": 1, "updated_at": new, "balance": 200}]
    incoming = [{"account_id": 1, "updated_at": old, "balance": 100},
                {"account_id": 2, "updated_at": new, "balance": 50}]
    once = merge_latest_records(existing, incoming, "account_id")
    replayed = merge_latest_records(once, incoming, "account_id")
    assert once == replayed
    assert once[0]["balance"] == 200


def test_bronze_writer_is_batch_scoped_and_merge_is_timestamp_guarded() -> None:
    writer = (PHASE3 / "customer360/writers.py").read_text()
    assert 'option("replaceWhere", f"_batch_id = \'{batch_id}\'")' in writer
    assert 'condition="s.updated_at > t.updated_at"' in writer
    assert ".whenNotMatchedInsertAll()" in writer


def test_phase3_config_and_runtime_contract() -> None:
    config = yaml.safe_load((PHASE3 / "config/phase3.yaml").read_text())
    assert config["pipeline"]["timezone"] == "UTC"
    assert config["bronze"]["preserve_raw_duplicates"] is True
    assert config["silver"]["customer_master_strategy"] == "full_rebuild"
    assert config["jdbc"]["num_partitions"] <= 4


def test_airflow_dags_and_jobs_are_present_and_syntax_valid() -> None:
    dags = {
        "lab_01_source_exploration.py": "lab_01_source_exploration",
        "lab_02_bronze_ingestion.py": "lab_02_bronze_ingestion",
        "lab_03_silver_transformation.py": "lab_03_silver_transformation",
        "customer360_ingestion_pipeline.py": "customer360_ingestion_pipeline",
    }
    for filename, dag_id in dags.items():
        source = (ROOT / "infra/airflow/dags" / filename).read_text()
        compile(source, filename, "exec")
        assert f'dag_id="{dag_id}"' in source
        assert "max_active_runs=1" in source
        assert "schedule=None" in source
    for path in PHASE3.glob("*.py"):
        compile(path.read_text(), str(path), "exec")


def test_phase3_reuses_ephemeral_spark_factory_and_event_volume() -> None:
    common = (ROOT / "infra/airflow/dags/phase3_common.py").read_text()
    compose = (ROOT / "infra/compose.yaml").read_text()
    assert "create_spark_task" in common
    assert "resource_profile" in common
    assert "spark-events:/spark-events" in compose
    assert "spark-jobs:/opt/spark/jobs:ro" in compose


def test_trino_can_read_quality_without_write_access() -> None:
    policy = json.loads((ROOT / "infra/minio/policies/trino-reader.json").read_text())
    resources = {resource for statement in policy["Statement"] for resource in statement["Resource"]}
    actions = {action for statement in policy["Statement"] for action in statement["Action"]}
    assert "arn:aws:s3:::warehouse/quality/*" in resources
    assert "s3:GetObject" in actions
    assert not {"s3:PutObject", "s3:DeleteObject"} & actions


def test_small_manifest_retains_performance_scenarios() -> None:
    scenario = json.loads((ROOT / "data/small/metadata/scenario_manifest.json").read_text())
    quality = json.loads((ROOT / "data/small/metadata/data_quality_manifest.json").read_text())
    assert scenario["hot_accounts"][0]["transaction_count"] == 12000
    assert scenario["join_explosion"]["expected_intermediate_rows"] == 50000
    assert scenario["broadcast_join"]["overdue_loan_count"] == 100
    assert quality["raw_delivery"]["batch_01"]["duplicate_events"] == 400
