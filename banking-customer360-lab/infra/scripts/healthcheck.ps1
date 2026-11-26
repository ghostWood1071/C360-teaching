param(
    [ValidateSet("base", "etl", "query", "security", "audit", "distributed")]
    [string]$Profile = "base"
)
$ErrorActionPreference = "Stop"
$Repo = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
Set-Location $Repo
$Values = @{}
Get-Content ".env" | ForEach-Object {
    if ($_ -and -not $_.StartsWith("#") -and $_.Contains("=")) {
        $Pair = $_.Split("=", 2)
        $Values[$Pair[0]] = $Pair[1]
    }
}

function Wait-Url([string]$Name, [string]$Url, [string]$Credential = "") {
    $Deadline = (Get-Date).AddMinutes(5)
    while ((Get-Date) -lt $Deadline) {
        $CurlArgs = @("-k", "-f", "-s", "-S")
        if ($Credential) { $CurlArgs += @("-u", $Credential) }
        $CurlArgs += $Url
        & curl.exe @CurlArgs | Out-Null
        if ($LASTEXITCODE -eq 0) {
            Write-Host "${Name}: healthy"
            return
        }
        Start-Sleep -Seconds 3
    }
    throw "Quá thời gian chờ ${Name}: $Url"
}

Wait-Url "MinIO" "http://localhost:$($Values['MINIO_API_PORT'])/minio/health/live"
if ($Profile -in @("base", "etl")) {
    Wait-Url "Airflow" "http://localhost:$($Values['AIRFLOW_PORT'])/health"
    Wait-Url "SparkHistory" "http://localhost:$($Values['SPARK_HISTORY_PORT'])/api/v1/applications"
}
if ($Profile -in @("base", "query")) {
    Wait-Url "Trino" "http://localhost:$($Values['TRINO_HTTP_PORT'])/v1/info"
}
if ($Profile -in @("security", "audit")) {
    Wait-Url "Ranger" "http://localhost:$($Values['RANGER_PORT'])/service/public/v2/api/service" "$($Values['RANGER_ADMIN_USER']):$($Values['RANGER_ADMIN_PASSWORD'])"
    Wait-Url "Trino" "https://localhost:$($Values['TRINO_HTTPS_PORT'])/v1/info" "platform_admin:$($Values['TRINO_PLATFORM_ADMIN_PASSWORD'])"
}
