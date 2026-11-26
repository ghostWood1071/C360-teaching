$ErrorActionPreference = "Stop"
$Repo = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
Set-Location $Repo

foreach ($Command in @("docker", "python")) {
    if (-not (Get-Command $Command -ErrorAction SilentlyContinue)) {
        throw "Thiếu công cụ bắt buộc: $Command"
    }
}
& docker compose version | Out-Null
if ($LASTEXITCODE -ne 0) { throw "Docker Compose không khả dụng." }
& docker info | Out-Null
if ($LASTEXITCODE -ne 0) { throw "Docker Engine không chạy." }

if (-not (Test-Path ".env")) {
    Copy-Item ".env.example" ".env"
}

@'
from base64 import urlsafe_b64encode
from pathlib import Path
import hashlib
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
password_path = Path("infra/trino/config/security/password.db")
password_lines = []
for user, key in (
    ("platform_admin", "TRINO_PLATFORM_ADMIN_PASSWORD"),
    ("data_engineer", "TRINO_DATA_ENGINEER_PASSWORD"),
    ("risk_analyst", "TRINO_RISK_ANALYST_PASSWORD"),
    ("marketing_analyst", "TRINO_MARKETING_ANALYST_PASSWORD"),
    ("external_user", "TRINO_EXTERNAL_USER_PASSWORD"),
):
    salt = os.urandom(16)
    iterations = 10000
    digest = hashlib.pbkdf2_hmac("sha1", values[key].encode(), salt, iterations, dklen=32)
    password_lines.append(f"{user}:{iterations}:{salt.hex()}:{digest.hex()}")
password_path.write_text("\n".join(password_lines) + "\n", encoding="utf-8")
'@ | python -
if ($LASTEXITCODE -ne 0) { throw "Không tạo được cấu hình bí mật." }

$EnvValues = @{}
Get-Content ".env" | ForEach-Object {
    if ($_ -and -not $_.StartsWith("#") -and $_.Contains("=")) {
        $Pair = $_.Split("=", 2)
        $EnvValues[$Pair[0]] = $Pair[1]
    }
}
New-Item -ItemType Directory -Force "infra/certs" | Out-Null
if (-not (Test-Path "infra/certs/trino.jks")) {
    $CertPath = (Resolve-Path "infra/certs").Path
    $KeyArgs = @(
        "run", "--rm", "-v", "${CertPath}:/certs", "eclipse-temurin:17-jdk-jammy",
        "keytool", "-genkeypair", "-alias", "trino", "-keyalg", "RSA", "-keysize", "3072",
        "-validity", "3650", "-dname", "CN=localhost, OU=Training, O=ABC Bank, L=Ho Chi Minh City, C=VN",
        "-ext", "SAN=dns:localhost,dns:trino,ip:127.0.0.1", "-keystore", "/certs/trino.jks",
        "-storepass", $EnvValues["TRINO_KEYSTORE_PASSWORD"], "-keypass", $EnvValues["TRINO_KEYSTORE_PASSWORD"]
    )
    & docker @KeyArgs
    if ($LASTEXITCODE -ne 0) { throw "Không tạo được Trino keystore." }
}

& docker compose --env-file .env -f infra/compose.yaml config --quiet
if ($LASTEXITCODE -ne 0) { throw "Compose base không hợp lệ." }
& docker compose --env-file .env -f infra/compose.yaml -f infra/compose.security.yaml config --quiet
if ($LASTEXITCODE -ne 0) { throw "Compose security không hợp lệ." }
& docker compose --env-file .env -f infra/compose.yaml pull --ignore-buildable
if ($LASTEXITCODE -ne 0) { throw "Không pull được image." }
& docker compose --env-file .env -f infra/compose.yaml build
if ($LASTEXITCODE -ne 0) { throw "Không build được image." }
Write-Host "Thiết lập hoàn tất. Chạy .\infra\scripts\up.ps1 base hoặc security."
