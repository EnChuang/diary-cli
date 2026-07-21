# 八卦編年史 UI 啟動腳本
#   .\run_ui.ps1 -NoReload   ← 測 AI 建議用這個
#   .\run_ui.ps1             ← 熱重載

param(
    [switch]$NoReload
)

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

if (Test-Path ".\.venv\Scripts\Activate.ps1") {
    .\.venv\Scripts\Activate.ps1
}

Write-Host "http://127.0.0.1:8765" -ForegroundColor Cyan

if ($NoReload) {
    uvicorn ui.app:app --host 127.0.0.1 --port 8765
} else {
    uvicorn ui.app:app --reload --host 127.0.0.1 --port 8765 --reload-dir ui --reload-dir storage --reload-dir skill
}
