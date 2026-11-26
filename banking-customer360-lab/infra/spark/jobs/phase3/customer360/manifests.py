"""Read the small Phase 1 JSON manifests uploaded beside source data."""

from __future__ import annotations

import json

from customer360.configuration import raw_root


def read_json_document(spark, uri: str) -> dict:
    records = spark.sparkContext.wholeTextFiles(uri, minPartitions=1).take(2)
    if len(records) != 1:
        raise ValueError(f"Expected exactly one metadata document at {uri}, found {len(records)}")
    return json.loads(records[0][1])


def load_manifests(spark, config: dict, profile: str) -> dict[str, dict]:
    root = f"{raw_root(config, profile)}/metadata"
    names = ("dataset_manifest", "incremental_manifest", "data_quality_manifest", "scenario_manifest", "schema_manifest")
    return {name: read_json_document(spark, f"{root}/{name}.json") for name in names}


def expected_bronze_count(manifests: dict[str, dict], batch_id: str, table: str) -> int:
    if batch_id == "batch_01":
        if table == "transactions":
            return int(manifests["data_quality_manifest"]["raw_delivery"][batch_id]["total"])
        return int(manifests["dataset_manifest"]["expected_counts"][table])
    if batch_id != "batch_02":
        raise ValueError(f"No manifest contract for {batch_id}")
    if table == "transactions":
        return int(manifests["data_quality_manifest"]["raw_delivery"][batch_id]["total"])
    incremental = manifests["incremental_manifest"]
    return int(incremental["inserts"].get(table, 0) + incremental["updates"].get(table, 0))

