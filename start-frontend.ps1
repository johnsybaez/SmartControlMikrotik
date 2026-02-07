# Script para iniciar el frontend de SmartControl
# Uso: .\start-frontend.ps1

Write-Host "================================================" -ForegroundColor Cyan
Write-Host "  SmartControl - Iniciando Frontend" -ForegroundColor Cyan
Write-Host "================================================" -ForegroundColor Cyan

# Detener procesos node existentes
Write-Host "`n[1/3] Deteniendo procesos existentes..." -ForegroundColor Yellow
Get-Process | Where-Object { $_.ProcessName -eq "node" -and $_.Path -like "*SmartControl*" } | Stop-Process -Force -ErrorAction SilentlyContinue
Start-Sleep -Seconds 2

# Cambiar al directorio frontend
Write-Host "[2/3] Cambiando al directorio frontend..." -ForegroundColor Yellow
Set-Location -Path "$PSScriptRoot\frontend"

# Iniciar Vite
Write-Host "[3/3] Iniciando servidor Vite..." -ForegroundColor Yellow
& "$PSScriptRoot\.venv\Scripts\python.exe" "$PSScriptRoot\backend\scripts\generate_dev_cert.py"
Write-Host "`nServidor corriendo en: https://localhost:5173" -ForegroundColor Green
Write-Host "Presiona CTRL+C para detener`n" -ForegroundColor Gray

npm run dev
