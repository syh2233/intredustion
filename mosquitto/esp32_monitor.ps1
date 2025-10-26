# ESP32 MQTT Monitor
Write-Host "ESP32 MQTT Monitor" -ForegroundColor Green
Write-Host "=================" -ForegroundColor Green

Set-Location $PSScriptRoot

Write-Host "Starting to monitor ESP32 topics..." -ForegroundColor Yellow
Write-Host "Press Ctrl+C to stop monitoring" -ForegroundColor Cyan
Write-Host ""

# Start monitoring all ESP32 topics
try {
    & ".\mosquitto_sub.exe" -h 127.0.0.1 -t "esp32/#" -v
} catch {
    Write-Host "Error monitoring: $_" -ForegroundColor Red
}

Write-Host ""
Write-Host "Monitoring stopped" -ForegroundColor Red