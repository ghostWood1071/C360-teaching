#!/usr/bin/env python3
"""Render Trino's PBKDF2 password file from the existing local .env."""

from pathlib import Path
import hashlib
import os

ROOT = Path(__file__).resolve().parents[2]
ENV_PATH = ROOT / ".env"
OUTPUT_PATH = ROOT / "infra/trino/config/security/password.db"
USERS = (
    ("platform_admin", "TRINO_PLATFORM_ADMIN_PASSWORD"),
    ("data_engineer", "TRINO_DATA_ENGINEER_PASSWORD"),
    ("risk_analyst", "TRINO_RISK_ANALYST_PASSWORD"),
    ("marketing_analyst", "TRINO_MARKETING_ANALYST_PASSWORD"),
    ("external_user", "TRINO_EXTERNAL_USER_PASSWORD"),
)


def main() -> None:
    values = {}
    for line in ENV_PATH.read_text(encoding="utf-8").splitlines():
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            values[key] = value

    rendered = []
    for user, key in USERS:
        password = values.get(key, "")
        if not password or password.startswith("CHANGE_ME_"):
            raise RuntimeError(f"Missing initialized secret: {key}")
        salt = os.urandom(16)
        iterations = 10000
        # Trino 484 uses Java PBKDF2WithHmacSHA1 for this password-file format.
        digest = hashlib.pbkdf2_hmac("sha1", password.encode(), salt, iterations, dklen=32)
        rendered.append(f"{user}:{iterations}:{salt.hex()}:{digest.hex()}")

    OUTPUT_PATH.write_text("\n".join(rendered) + "\n", encoding="utf-8")
    OUTPUT_PATH.chmod(0o600)


if __name__ == "__main__":
    main()
