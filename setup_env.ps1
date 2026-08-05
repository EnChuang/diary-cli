# 建立本機 .env（從範本複製；不會覆寫已有的 .env）
# 用法（專案根目錄）：
#   .\setup_env.ps1
#
# 分工：
#   .env.example  → 進 GitHub，無真 Key，給重現專案的人用
#   .env          → 只在你／使用者本機，填自己的 ARK_API_KEY，gitignore 不同步

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

$example = Join-Path $PSScriptRoot ".env.example"
$envFile = Join-Path $PSScriptRoot ".env"

if (-not (Test-Path $example)) {
    Write-Host "找不到 .env.example，請確認在專案根目錄。" -ForegroundColor Red
    exit 1
}

if (Test-Path $envFile) {
    Write-Host "已有 .env，未覆寫（保留你現有的 API Key）。" -ForegroundColor Yellow
    Write-Host "路徑: $envFile"
    Write-Host "若要重填，請手動編輯該檔，或先改名備份再執行本腳本。"
    exit 0
}

Copy-Item $example $envFile
Write-Host "已建立 .env（從 .env.example 複製）。" -ForegroundColor Green
Write-Host ""
Write-Host "下一步（必做）：" -ForegroundColor Cyan
Write-Host "  1. 用編輯器打開: $envFile"
Write-Host "  2. 把 ARK_API_KEY=ark-你的金鑰 改成你在 ModelArk／火山控制台申請的真 Key"
Write-Host "  3. 可選：調整 ARK_BASE_URL、ARK_MODEL"
Write-Host "  4. 執行 .\run_ui.ps1 -NoReload"
Write-Host ""
Write-Host "注意：.env 不會上傳 GitHub；請勿把真 Key 貼到公開地方。" -ForegroundColor Yellow
