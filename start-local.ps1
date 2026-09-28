# Local dev: backend :8000 + frontend :5173, open browser. Close the two minimized windows to stop.
$ErrorActionPreference = "Stop"
$Root = $PSScriptRoot
$Backend = Join-Path $Root "backend"
$Frontend = Join-Path $Root "frontend"
$Uvicorn = Join-Path $Backend ".venv\Scripts\uvicorn.exe"

if (-not (Test-Path $Uvicorn)) {
    Write-Host "Missing backend\.venv — run README setup (venv + pip install)." -ForegroundColor Yellow
    exit 1
}
if (-not (Test-Path (Join-Path $Frontend "node_modules"))) {
    Write-Host "Missing frontend\node_modules — run npm install in frontend." -ForegroundColor Yellow
    exit 1
}

$backendCmd = "Set-Location -LiteralPath '$Backend'; & '$Uvicorn' main:app --reload --port 8000"
$frontendCmd = "Set-Location -LiteralPath '$Frontend'; npm run dev"

Start-Process powershell -ArgumentList @("-NoExit", "-NoProfile", "-Command", $backendCmd) -WindowStyle Minimized
Start-Process powershell -ArgumentList @("-NoExit", "-NoProfile", "-Command", $frontendCmd) -WindowStyle Minimized

Start-Sleep -Seconds 3
Start-Process "http://localhost:5173"

Write-Host "OK: http://localhost:5173" -ForegroundColor Green
Write-Host "Stop: close the two minimized PowerShell windows." -ForegroundColor Gray
