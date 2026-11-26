#!/usr/bin/env python3
"""Idempotently create Ranger users, Trino service, and training policies."""

import json
import os
import sys
import time
from typing import Any

import requests

BASE_URL = os.environ.get("RANGER_URL", "http://ranger-admin:6080")
ADMIN_USER = os.environ["RANGER_ADMIN_USER"]
ADMIN_PASSWORD = os.environ["RANGER_ADMIN_PASSWORD"]
SERVICE_NAME = os.environ.get("RANGER_SERVICE_NAME", "customer360-trino")
AUTH = (ADMIN_USER, ADMIN_PASSWORD)
USERS = ["platform_admin", "data_engineer", "risk_analyst", "marketing_analyst", "external_user"]


def is_not_found(response: requests.Response) -> bool:
    """Ranger APIs inconsistently report a missing object as 400 or 404."""
    body = response.text.lower()
    return response.status_code == 404 or (
        response.status_code == 400 and ("data_not_found" in body or "not found" in body)
    )


def request(method: str, path: str, **kwargs: Any) -> requests.Response:
    response = requests.request(method, f"{BASE_URL}{path}", auth=AUTH, timeout=30, **kwargs)
    if response.status_code >= 400:
        raise RuntimeError(f"Ranger API {method} {path} returned {response.status_code}: {response.text[:500]}")
    return response


def wait_ready() -> None:
    for _ in range(60):
        try:
            if requests.get(f"{BASE_URL}/service/public/v2/api/service", auth=AUTH, timeout=5).status_code == 200:
                return
        except requests.RequestException:
            pass
        time.sleep(2)
    raise RuntimeError("Ranger Admin did not become ready")


def ensure_user(username: str) -> None:
    result = requests.get(f"{BASE_URL}/service/xusers/users/userName/{username}", auth=AUTH, timeout=30)
    if result.status_code == 200 and result.text.strip() not in ("", "null"):
        return
    if result.status_code != 200 and not is_not_found(result):
        raise RuntimeError(f"Unable to inspect Ranger user {username}: {result.status_code} {result.text[:500]}")
    payload = {
        "name": username,
        "firstName": username,
        "password": ADMIN_PASSWORD,
        "description": "Customer 360 training identity",
        "userSource": 0,
        "userRoleList": ["ROLE_USER"],
        "status": 1,
    }
    request("POST", "/service/xusers/secure/users", json=payload)


def ensure_service() -> None:
    response = requests.get(f"{BASE_URL}/service/public/v2/api/service/name/{SERVICE_NAME}", auth=AUTH, timeout=30)
    payload = {
        "name": SERVICE_NAME,
        "type": "trino",
        "displayName": "Customer 360 Trino",
        "description": "Trino authorization for the local Customer 360 lab",
        "isEnabled": True,
        "configs": {
            "username": "platform_admin",
            "password": os.environ["TRINO_PLATFORM_ADMIN_PASSWORD"],
            "jdbc.driverClassName": "io.trino.jdbc.TrinoDriver",
            "jdbc.url": "jdbc:trino://trino:8443",
            "ranger.plugin.super.users": "",
            "ranger.plugin.super.groups": "",
            "service.admin.users": ADMIN_USER,
            "service.admin.groups": "",
        },
    }
    if is_not_found(response):
        request("POST", "/service/public/v2/api/service", json=payload)
    elif response.status_code < 400:
        payload["id"] = response.json()["id"]
        request("PUT", f"/service/public/v2/api/service/{payload['id']}", json=payload)
    else:
        raise RuntimeError(f"Unable to inspect Ranger service: {response.status_code} {response.text[:500]}")


def resource(values: list[str]) -> dict[str, Any]:
    return {"values": values, "isExcludes": False, "isRecursive": False}


def policy_item(users: list[str], accesses: list[str]) -> dict[str, Any]:
    return {
        "users": users,
        "groups": [],
        "roles": [],
        "conditions": [],
        "accesses": [{"type": name, "isAllowed": True} for name in accesses],
        "delegateAdmin": False,
    }


def policies() -> list[dict[str, Any]]:
    authenticated = USERS
    return [
        {
            "name": "all - queryid",
            "service": SERVICE_NAME,
            "policyType": 0,
            "isEnabled": True,
            "resources": {"queryid": resource(["*"])},
            "policyItems": [policy_item(authenticated, ["execute"])],
        },
        {
            "name": "all - trinouser",
            "service": SERVICE_NAME,
            "policyType": 0,
            "isEnabled": True,
            "resources": {"trinouser": resource(["{USER}"])},
            "policyItems": [policy_item(authenticated, ["impersonate"])],
        },
        {
            "name": "10-platform-and-engineering-read",
            "service": SERVICE_NAME,
            "policyType": 0,
            "isEnabled": True,
            "resources": {
                "catalog": resource(["lakehouse"]),
                "schema": resource(["bronze", "silver", "gold"]),
                "table": resource(["*"]),
                "column": resource(["*"]),
            },
            "policyItems": [policy_item(["platform_admin", "data_engineer"], ["use", "show", "select"])],
        },
        {
            "name": "20-risk-financial-read",
            "service": SERVICE_NAME,
            "policyType": 0,
            "isEnabled": True,
            "resources": {
                "catalog": resource(["lakehouse"]),
                "schema": resource(["silver", "gold"]),
                "table": resource(["security_customers"]),
                "column": resource(["customer_id", "customer_type", "monthly_income", "risk_region"]),
            },
            "policyItems": [policy_item(["risk_analyst"], ["use", "show", "select"])],
        },
        {
            "name": "30-marketing-gold-read",
            "service": SERVICE_NAME,
            "policyType": 0,
            "isEnabled": True,
            "resources": {
                "catalog": resource(["lakehouse"]),
                "schema": resource(["gold"]),
                "table": resource(["security_customers"]),
                "column": resource(["customer_id", "customer_type", "identity_number", "phone", "email"]),
            },
            "policyItems": [policy_item(["marketing_analyst"], ["use", "show", "select"])],
        },
        {
            "name": "40-mask-phone-identity-email",
            "service": SERVICE_NAME,
            "policyType": 1,
            "isEnabled": True,
            "resources": {
                "catalog": resource(["lakehouse"]),
                "schema": resource(["gold"]),
                "table": resource(["security_customers"]),
                "column": resource(["identity_number", "phone", "email"]),
            },
            "dataMaskPolicyItems": [{
                **policy_item(["marketing_analyst"], ["select"]),
                "dataMaskInfo": {"dataMaskType": "MASK_SHOW_LAST_4", "valueExpr": ""},
            }],
        },
        {
            "name": "50-marketing-individuals-only",
            "service": SERVICE_NAME,
            "policyType": 2,
            "isEnabled": True,
            "resources": {
                "catalog": resource(["lakehouse"]),
                "schema": resource(["gold"]),
                "table": resource(["security_customers"]),
            },
            "rowFilterPolicyItems": [{
                **policy_item(["marketing_analyst"], ["select"]),
                "rowFilterInfo": {"filterExpr": "customer_type = 'INDIVIDUAL'"},
            }],
        },
    ]


def ensure_policy(payload: dict[str, Any]) -> None:
    encoded_name = requests.utils.quote(payload["name"], safe="")
    response = requests.get(
        f"{BASE_URL}/service/public/v2/api/service/{SERVICE_NAME}/policy/{encoded_name}", auth=AUTH, timeout=30
    )
    if is_not_found(response):
        request("POST", "/service/public/v2/api/policy", json=payload)
    elif response.status_code < 400:
        payload["id"] = response.json()["id"]
        request("PUT", f"/service/public/v2/api/policy/{payload['id']}", json=payload)
    else:
        raise RuntimeError(f"Unable to inspect policy {payload['name']}: {response.status_code}")


def main() -> int:
    wait_ready()
    for username in USERS:
        ensure_user(username)
    ensure_service()
    for payload in policies():
        ensure_policy(payload)
    print(json.dumps({"service": SERVICE_NAME, "users": USERS, "policies": [p["name"] for p in policies()]}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
