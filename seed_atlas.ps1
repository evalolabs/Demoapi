param(
    [string]$AtlasUri,

    [string]$DbName,

    [string]$EnvFile = ".env",

    [switch]$DropFirst,

    [int]$BatchSize = 1000
)

$ErrorActionPreference = "Stop"

Set-Location -Path $PSScriptRoot

if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    throw "python ist nicht im PATH. Bitte Python installieren oder PATH pruefen."
}

if ((-not $AtlasUri) -or (-not $DbName)) {
    $envPath = Join-Path $PSScriptRoot $EnvFile
    if (Test-Path $envPath) {
        Get-Content -Path $envPath | ForEach-Object {
            $line = $_.Trim()
            if (-not $line -or $line.StartsWith("#")) {
                return
            }
            $pair = $line -split "=", 2
            if ($pair.Count -ne 2) {
                return
            }
            $key = $pair[0].Trim()
            $value = $pair[1].Trim().Trim('"').Trim("'")
            if ($key -and $value) {
                [System.Environment]::SetEnvironmentVariable($key, $value, "Process")
            }
        }
    }
}

if (-not $AtlasUri) {
    $AtlasUri = $env:ATLAS_URI
}

if (-not $DbName) {
    $DbName = $env:ATLAS_DB_NAME
}

if (-not $DbName) {
    $DbName = "demoapi"
}

if (-not $AtlasUri) {
    throw "ATLAS_URI fehlt. Gib -AtlasUri an oder lege ihn in $EnvFile ab."
}

$env:ATLAS_URI = $AtlasUri
$env:ATLAS_DB_NAME = $DbName

$argsList = @("seed_atlas.py", "--batch-size", "$BatchSize")
if ($DropFirst.IsPresent) {
    $argsList += "--drop-first"
}

Write-Host "Seeding Atlas..."
Write-Host "DB Name: $DbName"
Write-Host "Drop first: $($DropFirst.IsPresent)"
Write-Host "Batch size: $BatchSize"

python @argsList
