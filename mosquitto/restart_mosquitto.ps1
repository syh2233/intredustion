# Script to restart Mosquitto with minimal configuration
Write-Host "Restarting Mosquitto with Minimal Configuration" -ForegroundColor Green
Write-Host "================================================" -ForegroundColor Green

Set-Location $PSScriptRoot

# Stop existing Mosquitto processes
Write-Host "Stopping existing Mosquitto processes..." -ForegroundColor Yellow
Get-Process | Where-Object {$_.Name -like "*mosquitto*"} | Stop-Process -Force
Write-Host "Waiting for processes to stop..." -ForegroundColor Cyan
Start-Sleep -Seconds 3

# Check if any processes are still running
$remainingProcesses = Get-Process | Where-Object {$_.Name -like "*mosquitto*"}
if ($remainingProcesses) {
    Write-Host "Warning: Some Mosquitto processes are still running:" -ForegroundColor Red
    $remainingProcesses | ForEach-Object {
        Write-Host "  $($_.Name) (PID: $($_.Id))"
    }
    Write-Host "Attempting to force stop..." -ForegroundColor Yellow
    $remainingProcesses | Stop-Process -Force
    Start-Sleep -Seconds 2
}

# Start Mosquitto with minimal configuration
Write-Host "Starting Mosquitto with minimal configuration..." -ForegroundColor Yellow
Write-Host "Config file: mosquitto_minimal.conf" -ForegroundColor Cyan
Write-Host "Configuration:" -ForegroundColor Cyan
Write-Host "  listener 1883" -ForegroundColor White
Write-Host "  allow_anonymous true" -ForegroundColor White

Write-Host ""
Write-Host "Starting Mosquitto..." -ForegroundColor Green

try {
    & ".\mosquitto.exe" -c "mosquitto_minimal.conf" -v
} catch {
    Write-Host "Error starting Mosquitto: $_" -ForegroundColor Red
}

Write-Host ""
Write-Host "================================================" -ForegroundColor Green
Write-Host "Mosquitto stopped" -ForegroundColor Red
Read-Host "Press Enter to exit"