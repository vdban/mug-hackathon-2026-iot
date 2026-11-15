@echo off
chcp 65001 >nul
title Frutiger Aqua Smart Aquarium - Backend & Wokwi Auto-Bridge
cd /d "%~dp0backend"
powershell -NoProfile -Command "if (Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue) { exit 0 } else { exit 1 }"
if %errorlevel%==0 (
    echo Backend & Wokwi Auto-Bridge dang chay san tren cong 8000!
    start "" "http://127.0.0.1:8000/"
    timeout /t 3 >nul
    exit /b 0
)
echo Dang khoi dong FastAPI Backend + Wokwi Auto-Bridge...
start "" cmd /c "timeout /t 3 >nul && start http://127.0.0.1:8000/"
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
