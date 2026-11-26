"""Configuration loading without embedding credentials."""

from __future__ import annotations

import os
from pathlib import Path

import yaml

DEFAULT_CONFIG = os.environ.get("PHASE3_CONFIG", "/opt/spark/jobs/phase3/config/phase3.yaml")


def load_config(path: str | None = None) -> dict:
    config_path = Path(path or DEFAULT_CONFIG)
    with config_path.open(encoding="utf-8") as stream:
        config = yaml.safe_load(stream)
    required = {"pipeline", "storage", "catalog", "batches", "jdbc", "quality"}
    missing = required - set(config)
    if missing:
        raise ValueError(f"Missing Phase 3 configuration sections: {sorted(missing)}")
    return config


def raw_root(config: dict, profile: str) -> str:
    if profile not in {"small", "standard"}:
        raise ValueError("source profile must be small or standard")
    return config["storage"]["raw_root"].format(profile=profile).rstrip("/")


def jdbc_environment() -> dict[str, str]:
    names = (
        "CORE_BANKING_JDBC_URL", "CORE_BANKING_DB_USER", "CORE_BANKING_DB_PASSWORD",
        "CRM_JDBC_URL", "CRM_DB_USER", "CRM_DB_PASSWORD",
    )
    return {name: os.environ[name] for name in names if os.environ.get(name)}

