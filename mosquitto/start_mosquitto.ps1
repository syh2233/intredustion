# PowerShell script to start Mosquitto with custom configuration
Write-Host "正在启动Mosquitto MQTT Broker..." -ForegroundColor Green
Write-Host "=================================" -ForegroundColor Green

# Change to script directory
Set-Location $PSScriptRoot

Write-Host "停止现有服务..."
Stop-Process -Name "mosquitto" -Force -ErrorAction SilentlyContinue
Start-Sleep -Seconds 2

Write-Host "使用新配置启动Mosquitto..."
Write-Host "配置文件: mosquitto_simple.conf"
Write-Host "监听端口: 1883 (所有接口)"
Write-Host "允许匿名连接: 是"

Write-Host ""
Write-Host "正在启动服务..." -ForegroundColor Yellow

# Start Mosquitto with verbose output
& ".\mosquitto.exe" -c "mosquitto_simple.conf" -v

Write-Host ""
Write-Host "=================================" -ForegroundColor Green
Write-Host "服务已停止运行" -ForegroundColor Red
Read-Host "按 Enter 键退出"