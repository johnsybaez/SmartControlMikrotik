# Script para iniciar el backend de SmartControl
# Uso: .\start-backend.ps1

Write-Host "================================================" -ForegroundColor Cyan
Write-Host "  SmartControl - Iniciando Backend" -ForegroundColor Cyan
Write-Host "================================================" -ForegroundColor Cyan

# Detener procesos existentes
Write-Host "`n[1/3] Deteniendo procesos existentes..." -ForegroundColor Yellow
Stop-Process -Name "python","uvicorn" -Force -ErrorAction SilentlyContinue
Start-Sleep -Seconds 2

# Cambiar al directorio backend
Write-Host "[2/3] Cambiando al directorio backend..." -ForegroundColor Yellow
Set-Location -Path "$PSScriptRoot\backend"

# Iniciar uvicorn
Write-Host "[3/3] Iniciando servidor FastAPI..." -ForegroundColor Yellow
& "$PSScriptRoot\.venv\Scripts\python.exe" "$PSScriptRoot\backend\scripts\generate_dev_cert.py"
Write-Host "`nServidor corriendo en: https://0.0.0.0:8000" -ForegroundColor Green
Write-Host "Presiona CTRL+C para detener`n" -ForegroundColor Gray

& "$PSScriptRoot\.venv\Scripts\uvicorn.exe" app.main:app --host 0.0.0.0 --port 8000 --reload --ssl-keyfile "$PSScriptRoot\certs\dev-key.pem" --ssl-certfile "$PSScriptRoot\certs\dev-cert.pem"
