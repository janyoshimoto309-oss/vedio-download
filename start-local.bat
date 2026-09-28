@echo off
setlocal
cd /d "%~dp0"

set "BACKEND=%~dp0backend"
set "FRONTEND=%~dp0frontend"
set "UVICORN=%BACKEND%\.venv\Scripts\uvicorn.exe"

if not exist "%UVICORN%" (
    echo Missing backend\.venv - see README setup.
    pause
    exit /b 1
)
if not exist "%FRONTEND%\node_modules\" (
    echo Missing frontend\node_modules - run npm install in frontend.
    pause
    exit /b 1
)

start "vedio-download-backend" /min cmd /k cd /d "%BACKEND%" ^&^& "%UVICORN%" main:app --reload --port 8000
start "vedio-download-frontend" /min cmd /k cd /d "%FRONTEND%" ^&^& npm run dev

timeout /t 3 /nobreak >nul
start "" "http://localhost:5173"

echo Started: http://localhost:5173
echo Stop: close vedio-download-backend and vedio-download-frontend windows.
timeout /t 4 /nobreak >nul
