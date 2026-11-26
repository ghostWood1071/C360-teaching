#!/usr/bin/env python3
"""Execute result-based Ranger/Trino and MinIO security acceptance tests."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from typing import Callable


def host_mode(root: Path) -> int:
    command = [
        "docker", "compose", "--env-file", ".env",
        "-f", "infra/compose.yaml", "-f", "infra/compose.security.yaml",
        "--profile", "tools", "run", "--rm", "security-tests",
    ]
    result = subprocess.run(command, cwd=root)
    if result.returncode:
        return result.returncode
    logs = subprocess.run(
        [
            "docker", "compose", "--env-file", ".env",
            "-f", "infra/compose.yaml", "-f", "infra/compose.security.yaml",
            "logs", "--no-color", "trino",
        ],
        cwd=root,
        text=True,
        capture_output=True,
        check=True,
    ).stdout
    if "marketing_analyst" not in logs or "external_user" not in logs:
        print("FAILED audit: Trino logs do not contain expected Ranger audit identities", file=sys.stderr)
        return 1
    print("PASSED audit: Ranger audit identities persisted in Docker-managed Trino logs")
    return 0


def inside_mode() -> int:
    import boto3
    import requests
    import trino
    from botocore.exceptions import ClientError
    from trino.auth import BasicAuthentication
    import urllib3

    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    host = os.environ.get("TRINO_HOST", "trino")
    port = int(os.environ.get("TRINO_PORT", "8443"))
    passwords = {
        "platform_admin": os.environ["TRINO_PLATFORM_ADMIN_PASSWORD"],
        "data_engineer": os.environ["TRINO_DATA_ENGINEER_PASSWORD"],
        "risk_analyst": os.environ["TRINO_RISK_ANALYST_PASSWORD"],
        "marketing_analyst": os.environ["TRINO_MARKETING_ANALYST_PASSWORD"],
        "external_user": os.environ["TRINO_EXTERNAL_USER_PASSWORD"],
    }
    results: list[dict[str, object]] = []

    def query(user: str, sql: str, password: str | None = None):
        connection = trino.dbapi.connect(
            host=host,
            port=port,
            user=user,
            auth=BasicAuthentication(user, password if password is not None else passwords[user]),
            http_scheme="https",
            verify=False,
            catalog="lakehouse",
        )
        cursor = connection.cursor()
        cursor.execute(sql)
        return cursor.fetchall()

    def passed(name: str, detail: object = None) -> None:
        results.append({"name": name, "passed": True, "detail": detail})

    def denied(name: str, user: str, sql: str) -> None:
        try:
            query(user, sql)
        except Exception as error:
            if "denied" not in str(error).lower() and "cannot access" not in str(error).lower():
                raise AssertionError(f"{name} failed for an unexpected reason: {error}") from error
            passed(name, str(error)[:200])
            return
        raise AssertionError(f"{name}: operation unexpectedly succeeded")

    if query("platform_admin", "SELECT count(*) FROM lakehouse.gold.security_customers") != [[3]]:
        raise AssertionError("platform_admin did not read all security rows")
    passed("platform_admin_read_all")

    for layer in ("bronze", "silver"):
        if query("data_engineer", f"SELECT count(*) FROM lakehouse.{layer}.security_customers") != [[3]]:
            raise AssertionError(f"data_engineer did not read {layer}")
    passed("data_engineer_bronze_silver")

    denied("marketing_bronze_denied", "marketing_analyst", "SELECT * FROM lakehouse.bronze.security_customers")
    marketing = query(
        "marketing_analyst",
        "SELECT customer_id, customer_type, identity_number, phone, email "
        "FROM lakehouse.gold.security_customers ORDER BY customer_id",
    )
    if len(marketing) != 2 or any(row[1] != "INDIVIDUAL" for row in marketing):
        raise AssertionError(f"Marketing row filter returned {marketing!r}")
    original_sensitive = {
        "FICTIONAL-ABC-0001", "FICTIONAL-ABC-0003",
        "+84-SYN-0000000001", "+84-SYN-0000000003",
        "one@example.com", "three@example.com",
    }
    if any(value in original_sensitive for row in marketing for value in row[2:]):
        raise AssertionError(f"Sensitive marketing values were not masked: {marketing!r}")
    passed("marketing_gold_mask_and_row_filter", marketing)
    denied(
        "marketing_income_denied",
        "marketing_analyst",
        "SELECT monthly_income FROM lakehouse.gold.security_customers",
    )

    risk = query(
        "risk_analyst",
        "SELECT customer_id, monthly_income, risk_region FROM lakehouse.gold.security_customers ORDER BY customer_id",
    )
    if len(risk) != 3:
        raise AssertionError(f"Risk analyst returned {risk!r}")
    passed("risk_financial_read", risk)
    denied("risk_phone_denied", "risk_analyst", "SELECT phone FROM lakehouse.gold.security_customers")
    denied("external_user_denied", "external_user", "SELECT * FROM lakehouse.gold.security_customers")

    try:
        query("platform_admin", "SELECT 1", password="incorrect-password")
    except Exception:
        passed("incorrect_password_rejected")
    else:
        raise AssertionError("Incorrect Trino password was accepted")

    try:
        query(
            "platform_admin",
            "INSERT INTO lakehouse.gold.security_customers "
            "VALUES (99, 'INDIVIDUAL', 'X', 'X', 'X', 1, 'X')",
        )
    except Exception as error:
        message = str(error).lower()
        if not any(marker in message for marker in ("denied", "cannot access", "error committing write")):
            raise AssertionError(f"SQL write failed for an unexpected reason: {error}") from error
        if query("platform_admin", "SELECT count(*) FROM lakehouse.gold.security_customers") != [[3]]:
            raise AssertionError("Rejected SQL write changed the security table")
        passed("trino_sql_write_denied", str(error)[:200])
    else:
        raise AssertionError("Trino SQL write unexpectedly succeeded")

    s3 = boto3.client(
        "s3",
        endpoint_url=os.environ["MINIO_ENDPOINT"],
        aws_access_key_id=os.environ["TRINO_S3_ACCESS_KEY"],
        aws_secret_access_key=os.environ["TRINO_S3_SECRET_KEY"],
        region_name="us-east-1",
    )
    try:
        s3.put_object(Bucket="warehouse", Key="security-tests/must-not-write", Body=b"denied")
    except ClientError as error:
        if error.response["Error"]["Code"] not in ("AccessDenied", "XMinioAdminNoSuchUser"):
            raise
        passed("trino_storage_identity_read_only")
    else:
        raise AssertionError("Trino MinIO identity wrote an object")

    anonymous = boto3.client(
        "s3",
        endpoint_url=os.environ["MINIO_ENDPOINT"],
        aws_access_key_id="unauthorized_user",
        aws_secret_access_key="invalid_secret",
        region_name="us-east-1",
    )
    try:
        anonymous.list_objects_v2(Bucket="warehouse", MaxKeys=1)
    except ClientError:
        passed("unknown_minio_credentials_rejected")
    else:
        raise AssertionError("Unknown MinIO credentials accessed the warehouse")

    verify_policy_polling(query, passwords, passed)
    print(json.dumps({"passed": True, "checks": results}, ensure_ascii=False))
    return 0


def verify_policy_polling(query: Callable, passwords: dict[str, str], passed: Callable) -> None:
    import requests

    base = os.environ["RANGER_URL"]
    auth = (os.environ["RANGER_ADMIN_USER"], os.environ["RANGER_ADMIN_PASSWORD"])
    service = os.environ.get("RANGER_SERVICE_NAME", "customer360-trino")
    payload = {
        "name": "99-temporary-external-read-poll-test",
        "service": service,
        "policyType": 0,
        "isEnabled": True,
        "resources": {
            "catalog": {"values": ["lakehouse"], "isExcludes": False, "isRecursive": False},
            "schema": {"values": ["gold"], "isExcludes": False, "isRecursive": False},
            "table": {"values": ["security_customers"], "isExcludes": False, "isRecursive": False},
            "column": {"values": ["customer_id"], "isExcludes": False, "isRecursive": False},
        },
        "policyItems": [{
            "users": ["external_user"], "groups": [], "roles": [], "conditions": [],
            "accesses": [{"type": name, "isAllowed": True} for name in ("use", "show", "select")],
            "delegateAdmin": False,
        }],
    }
    response = requests.post(f"{base}/service/public/v2/api/policy", auth=auth, json=payload, timeout=30)
    response.raise_for_status()
    policy_id = response.json()["id"]
    deadline = time.monotonic() + max(90, int(os.environ.get("RANGER_POLICY_POLL_MS", "30000")) / 1000 * 3)
    try:
        while time.monotonic() < deadline:
            try:
                if query("external_user", "SELECT customer_id FROM lakehouse.gold.security_customers") == [[1], [2], [3]]:
                    passed("ranger_policy_polling_applied")
                    break
            except Exception:
                pass
            time.sleep(3)
        else:
            raise AssertionError("Temporary Ranger policy was not applied before the polling deadline")
    finally:
        requests.delete(f"{base}/service/public/v2/api/policy/{policy_id}", auth=auth, timeout=30).raise_for_status()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--inside-compose", action="store_true")
    args = parser.parse_args()
    return inside_mode() if args.inside_compose else host_mode(Path(__file__).resolve().parents[2])


if __name__ == "__main__":
    sys.exit(main())
