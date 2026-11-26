$ErrorActionPreference = "Stop"
$Repo = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
Set-Location $Repo
& docker compose --env-file .env -f infra/compose.yaml -f infra/compose.security.yaml -f infra/compose.audit.yaml -f infra/compose.distributed.yaml -f infra/compose.sources.yaml down --remove-orphans
if ($LASTEXITCODE -ne 0) { throw "Không dừng được hạ tầng." }
