$ErrorActionPreference = "Stop"
$Repo = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
Set-Location $Repo
& "$PSScriptRoot/healthcheck.ps1" -Profile base
$Base = @("compose", "--env-file", ".env", "-f", "infra/compose.yaml")
& docker @Base exec -T airflow-scheduler airflow dags unpause infrastructure_smoke_test | Out-Null
$RunId = "manual_infra_$((Get-Date).ToUniversalTime().ToString('yyyyMMddTHHmmssZ'))"
& docker @Base exec -T airflow-scheduler airflow dags trigger infrastructure_smoke_test --run-id $RunId | Out-Null
if ($LASTEXITCODE -ne 0) { throw "Không trigger được DAG." }
$Deadline = (Get-Date).AddMinutes(30)
while ((Get-Date) -lt $Deadline) {
    $State = (& docker @Base exec -T airflow-scheduler airflow dags state infrastructure_smoke_test $RunId 2>$null | Select-Object -Last 1).Trim()
    if ($State -eq "success") { Write-Host "Infrastructure smoke test passed: $RunId"; exit 0 }
    if ($State -eq "failed") { throw "Infrastructure smoke test failed: $RunId" }
    Start-Sleep -Seconds 5
}
throw "Infrastructure smoke test timed out: $RunId"
