# 野史錄 UI 啟動腳本
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

# API Key：本機 .env（gitignore）／倉庫只有 .env.example
if (-not (Test-Path ".\.env")) {
    Write-Host "尚未建立 .env（本機 API Key 檔）。" -ForegroundColor Yellow
    Write-Host "請先執行:  .\setup_env.ps1" -ForegroundColor Cyan
    Write-Host "再編輯 .env 填入你自己的 ARK_API_KEY 後重試。" -ForegroundColor Cyan
    exit 1
}
$keyLine = Get-Content ".\.env" -ErrorAction SilentlyContinue | Where-Object { $_ -match '^\s*ARK_API_KEY\s*=' } | Select-Object -First 1
if ($keyLine -match 'ark-你的|your.key|changeme|^\s*ARK_API_KEY\s*=\s*$') {
    Write-Host "請在 .env 把 ARK_API_KEY 改成你自己的真金鑰（不要留範本占位文字）。" -ForegroundColor Yellow
    exit 1
}

Write-Host "http://127.0.0.1:8765" -ForegroundColor Cyan

if ($NoReload) {
    uvicorn ui.app:app --host 127.0.0.1 --port 8765
} else {
    uvicorn ui.app:app --reload --host 127.0.0.1 --port 8765 --reload-dir ui --reload-dir storage --reload-dir skill
}
