$ErrorActionPreference = "Stop"
$Project = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Project

$Python = Join-Path $Project ".venv\Scripts\python.exe"
$App = Join-Path $Project "app_chai1_betting_v31_1.py"
$Driver = Join-Path $Project "chai1_auto_driver_v31_3.py"

Write-Host "=== chai1 v31.3 START ===" -ForegroundColor Cyan

$listener = Get-NetTCPConnection -LocalPort 8501 -State Listen -ErrorAction SilentlyContinue
if (-not $listener) {
    Start-Process -FilePath $Python `
        -ArgumentList @("-m","streamlit","run",$App,"--server.address","127.0.0.1","--server.port","8501","--browser.gatherUsageStats","false") `
        -WorkingDirectory $Project
    Start-Sleep -Seconds 4
}

$date = Get-Date -Format "yyyyMMdd"
$pidFile = Join-Path $Project "data\daily\auto_driver_$date.pid"
$driverRunning = $false
if (Test-Path $pidFile) {
    $oldPid = Get-Content $pidFile -ErrorAction SilentlyContinue
    if ($oldPid -and (Get-Process -Id $oldPid -ErrorAction SilentlyContinue)) {
        $driverRunning = $true
    }
}

if (-not $driverRunning) {
    Start-Process -FilePath $Python `
        -ArgumentList @($Driver,"--date",$date,"--skip-initial-full") `
        -WorkingDirectory $Project
}

$Tailscale = "C:\Program Files\Tailscale\tailscale.exe"
if (Test-Path $Tailscale) {
    & $Tailscale serve --bg localhost:8501 | Out-Null
}

Start-Process "http://127.0.0.1:8501"
Write-Host "chai1 v31.3 started." -ForegroundColor Green
