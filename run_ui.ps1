# Yes Log UI launcher
#   .\run_ui.ps1 -NoReload   # recommended when testing AI
#   .\run_ui.ps1             # hot reload for UI work
# API key: local .env only (gitignored). Template: .env.example
# Full guide: SETUP_API_KEY.md

param(
    [switch]$NoReload
)

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

if (Test-Path ".\.venv\Scripts\Activate.ps1") {
    .\.venv\Scripts\Activate.ps1
}

# Local .env (gitignored) vs repo .env.example (no real key)
if (-not (Test-Path ".\.env")) {
    Write-Host "Missing .env (local API key file)." -ForegroundColor Yellow
    Write-Host "Run:  .\setup_env.ps1" -ForegroundColor Cyan
    Write-Host "Then edit .env and set your own ARK_API_KEY. See SETUP_API_KEY.md" -ForegroundColor Cyan
    exit 1
}
$keyLine = Get-Content ".\.env" -ErrorAction SilentlyContinue |
    Where-Object { $_ -match '^\s*ARK_API_KEY\s*=' } |
    Select-Object -First 1
if (
    -not $keyLine -or
    $keyLine -match 'ark-你的|your[_-]?key|changeme|placeholder|^\s*ARK_API_KEY\s*=\s*$'
) {
    Write-Host "Set a real ARK_API_KEY in .env (do not leave the template placeholder)." -ForegroundColor Yellow
    Write-Host "See SETUP_API_KEY.md" -ForegroundColor Cyan
    exit 1
}

Write-Host "http://127.0.0.1:8765" -ForegroundColor Cyan

if ($NoReload) {
    uvicorn ui.app:app --host 127.0.0.1 --port 8765
} else {
    uvicorn ui.app:app --reload --host 127.0.0.1 --port 8765 --reload-dir ui --reload-dir storage --reload-dir skill
}
