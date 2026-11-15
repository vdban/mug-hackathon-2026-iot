# Helper Script: Open an instant HTTPS tunnel to local FastAPI backend (port 8000)
# so external visitors opening https://smart-aquarium-mug-2026.web.app can control real MongoDB + Datadog.

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host " Frutiger Aqua Public Backend Tunnel (localhost.run via SSH)" -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "1. Hay dam bao FastAPI backend dang chay o cong 8000:" -ForegroundColor Yellow
Write-Host "   cd backend; python -m uvicorn app.main:app --host 127.0.0.1 --port 8000"
Write-Host ""
Write-Host "2. Sau khi SSH ket noi thanh cong, copy URL https://xxxxx.lhr.life hien ra ben duoi." -ForegroundColor Yellow
Write-Host "3. Chia se link cho ban be / giam khao:" -ForegroundColor Green
Write-Host "   https://smart-aquarium-mug-2026.web.app/?api=<DAN_URL_TUNNEL_VAO_DAY>"
Write-Host ""
Write-Host "Dang mo tunnel toi 127.0.0.1:8000 (Nhan Ctrl+C de dung)..." -ForegroundColor Cyan

ssh -o StrictHostKeyChecking=no -R 80:127.0.0.1:8000 nokey@localhost.run
