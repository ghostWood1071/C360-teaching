param(
    [ValidateSet("base", "etl", "query", "security", "audit", "distributed")]
    [string]$Profile = "base"
)
$ErrorActionPreference = "Stop"
$Repo = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
Set-Location $Repo
if (-not (Test-Path ".env")) { throw "Chưa có .env; chạy .\infra\scripts\setup.ps1." }

$Base = @("compose", "--env-file", ".env", "-f", "infra/compose.yaml")
switch ($Profile) {
    "base" { $Args = $Base + @("up", "-d") }
    "etl" { $Args = $Base + @("up", "-d", "postgres", "minio", "minio-init", "hive-metastore-init", "hive-metastore", "spark-jobs-init", "spark-volume-init", "spark-history", "airflow-init", "airflow-scheduler", "airflow-webserver") }
    "query" { $Args = $Base + @("up", "-d", "postgres", "minio", "minio-init", "hive-metastore-init", "hive-metastore", "trino") }
    "security" { $Args = $Base + @("-f", "infra/compose.security.yaml", "up", "-d") }
    "audit" { $env:RANGER_AUDIT_SOLR_ENABLED = "true"; $Args = $Base + @("-f", "infra/compose.security.yaml", "-f", "infra/compose.audit.yaml", "up", "-d") }
    "distributed" { $Args = $Base + @("-f", "infra/compose.distributed.yaml", "--profile", "distributed", "up", "-d", "spark-master", "spark-worker-1", "spark-worker-2") }
}
& docker @Args
if ($LASTEXITCODE -ne 0) { throw "Không khởi động được profile $Profile." }
& "$PSScriptRoot/healthcheck.ps1" -Profile $Profile
