# Script para iniciar tanto backend como frontend
# Uso: .\start-all.ps1

Write-Host "================================================" -ForegroundColor Cyan
Write-Host "  SmartControl - Iniciando Todo" -ForegroundColor Cyan
Write-Host "================================================" -ForegroundColor Cyan

# Detener procesos existentes
Write-Host "`n[1/4] Deteniendo procesos existentes..." -ForegroundColor Yellow
Stop-Process -Name "python","uvicorn","node" -Force -ErrorAction SilentlyContinue
Start-Sleep -Seconds 2

# Iniciar backend en una nueva ventana de PowerShell
Write-Host "[2/4] Iniciando backend..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList "-NoExit", "-File", "$PSScriptRoot\start-backend.ps1"
Start-Sleep -Seconds 3

# Iniciar frontend en una nueva ventana de PowerShell
Write-Host "[3/4] Iniciando frontend..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList "-NoExit", "-File", "$PSScriptRoot\start-frontend.ps1"
Start-Sleep -Seconds 2

# Mostrar URLs
Write-Host "`n[4/4] Servicios iniciados!" -ForegroundColor Green
Write-Host "================================================" -ForegroundColor Cyan
Write-Host "Backend:  http://localhost:8000" -ForegroundColor White
Write-Host "Frontend: http://localhost:5173" -ForegroundColor White
Write-Host "Docs API: http://localhost:8000/docs" -ForegroundColor White
Write-Host "================================================" -ForegroundColor Cyan
Write-Host "`nPresiona cualquier tecla para cerrar esta ventana..." -ForegroundColor Gray
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
