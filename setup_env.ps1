# Create local .env from template (does not overwrite existing .env)
# Usage (repo root):  .\setup_env.ps1
#
# Split:
#   .env.example  -> on GitHub, NO real key (for clone users)
#   .env          -> local only, your ARK_API_KEY (gitignored, never pushed)

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

$example = Join-Path $PSScriptRoot ".env.example"
$envFile = Join-Path $PSScriptRoot ".env"

if (-not (Test-Path $example)) {
    Write-Host "ERROR: .env.example not found. Run this script from the repo root." -ForegroundColor Red
    exit 1
}

if (Test-Path $envFile) {
    Write-Host "OK: .env already exists (kept as-is, not overwritten)." -ForegroundColor Yellow
    Write-Host "Path: $envFile"
    Write-Host "Edit ARK_API_KEY there, or rename/backup .env then re-run this script."
    exit 0
}

Copy-Item -LiteralPath $example -Destination $envFile
Write-Host "OK: created .env from .env.example" -ForegroundColor Green
Write-Host ""
Write-Host "Next steps (required):" -ForegroundColor Cyan
Write-Host "  1. Open: $envFile"
Write-Host "  2. Set ARK_API_KEY=ark-... (your own ModelArk / Volcengine key)"
Write-Host "  3. Optional: ARK_BASE_URL, ARK_MODEL"
Write-Host "  4. Run: .\run_ui.ps1 -NoReload"
Write-Host ""
Write-Host "NOTE: .env is gitignored and will NOT be uploaded to GitHub." -ForegroundColor Yellow
Write-Host "      See SETUP_API_KEY.md for full instructions (Chinese)."
