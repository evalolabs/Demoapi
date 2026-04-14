param(
    [string]$Branch = "main",
    [string]$HealthUrl = "http://127.0.0.1:8100/health",
    [int]$HealthRetries = 20,
    [int]$HealthDelaySeconds = 3
)

$ErrorActionPreference = "Stop"

Set-Location -Path $PSScriptRoot

if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    throw "git ist nicht im PATH."
}
if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    throw "docker ist nicht im PATH."
}

Write-Host "Updating repository..."
git fetch --all --prune
git checkout $Branch
git pull origin $Branch

Write-Host "Starting containers..."
docker compose up -d --build

Write-Host "Waiting for health endpoint: $HealthUrl"
$ok = $false
for ($i = 1; $i -le $HealthRetries; $i++) {
    try {
        $resp = Invoke-WebRequest -Uri $HealthUrl -UseBasicParsing -TimeoutSec 5
        if ($resp.StatusCode -ge 200 -and $resp.StatusCode -lt 300) {
            $ok = $true
            Write-Host "Healthy (attempt $i/$HealthRetries)."
            break
        }
    } catch {
        # retry
    }
    Start-Sleep -Seconds $HealthDelaySeconds
}

if (-not $ok) {
    Write-Host "Health check failed. Last container status:"
    docker compose ps
    throw "Deploy abgeschlossen, aber Health-Check fehlgeschlagen."
}

Write-Host "Deploy erfolgreich."
