#!/bin/sh
set -eu

PROJECT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)
cd "$PROJECT_DIR"

for command_name in docker python3 openssl; do
  if ! command -v "$command_name" >/dev/null 2>&1; then
    echo "Thiếu công cụ bắt buộc: $command_name" >&2
    exit 1
  fi
done
docker compose version >/dev/null
docker info >/dev/null

if [ ! -f .env ]; then
  cp .env.example .env
fi

python3 - <<'PY'
from base64 import urlsafe_b64encode
from pathlib import Path
import os
import secrets

path = Path(".env")
lines = path.read_text(encoding="utf-8").splitlines()
values = {}
for line in lines:
    if line and not line.startswith("#") and "=" in line:
        key, value = line.split("=", 1)
        values[key] = value

for key, value in list(values.items()):
    if value.startswith("CHANGE_ME_"):
        values[key] = secrets.token_urlsafe(32)
values["AIRFLOW_FERNET_KEY"] = urlsafe_b64encode(os.urandom(32)).decode()

rendered = []
for line in lines:
    if line and not line.startswith("#") and "=" in line:
        key = line.split("=", 1)[0]
        line = f"{key}={values[key]}"
    rendered.append(line)
path.write_text("\n".join(rendered) + "\n", encoding="utf-8")
os.chmod(path, 0o600)

PY

python3 infra/scripts/render_trino_passwords.py

set -a
. ./.env
set +a

mkdir -p infra/certs
if [ ! -f infra/certs/trino.jks ]; then
  docker run --rm \
    -v "$PROJECT_DIR/infra/certs:/certs" \
    eclipse-temurin:17-jdk-jammy \
    keytool -genkeypair -alias trino -keyalg RSA -keysize 3072 -validity 3650 \
      -dname "CN=localhost, OU=Training, O=ABC Bank, L=Ho Chi Minh City, C=VN" \
      -ext "SAN=dns:localhost,dns:trino,ip:127.0.0.1" \
      -keystore /certs/trino.jks -storepass "$TRINO_KEYSTORE_PASSWORD" -keypass "$TRINO_KEYSTORE_PASSWORD"
fi
chmod 0600 infra/certs/trino.jks

docker_memory=$(docker info --format '{{.MemTotal}}' 2>/dev/null || printf '0')
if [ "$docker_memory" -gt 0 ] && [ "$docker_memory" -lt 10000000000 ]; then
  echo "Cảnh báo: Docker chỉ có khoảng $((docker_memory / 1024 / 1024 / 1024)) GiB; khuyến nghị 10–12 GiB." >&2
fi

docker compose --env-file .env -f infra/compose.yaml config --quiet
docker compose --env-file .env -f infra/compose.yaml -f infra/compose.security.yaml config --quiet
docker compose --env-file .env -f infra/compose.yaml pull --ignore-buildable
docker compose --env-file .env -f infra/compose.yaml build

echo "Thiết lập hoàn tất. Chạy 'make up' hoặc 'make up-security'."
