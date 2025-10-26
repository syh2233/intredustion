# PowerShell script to test Mosquitto connection (English version)
Write-Host "Testing Mosquitto Connection" -ForegroundColor Green
Write-Host "=================================" -ForegroundColor Green

Set-Location $PSScriptRoot

Write-Host "1. Testing local connection..." -ForegroundColor Yellow
Start-Process cmd.exe -ArgumentList "/c", "mosquitto_sub.exe -h localhost -t test/local -t 1 -v" -WindowStyle Hidden
Start-Sleep -Seconds 1
& ".\mosquitto_pub.exe" -h localhost -t test/local -m "Local connection test successful"
Start-Sleep -Seconds 2

Write-Host ""
Write-Host "2. Testing IP connection..." -ForegroundColor Yellow
Start-Process cmd.exe -ArgumentList "/c", "mosquitto_sub.exe -h 192.168.24.32 -t test/ip -t 1 -v" -WindowStyle Hidden
Start-Sleep -Seconds 1
& ".\mosquitto_pub.exe" -h 192.168.24.32 -t test/ip -m "IP connection test successful"
Start-Sleep -Seconds 2

Write-Host ""
Write-Host "3. Showing listening status..." -ForegroundColor Yellow
netstat -an | findstr :1883

Write-Host ""
Write-Host "4. Checking Mosquitto processes..." -ForegroundColor Yellow
Get-Process | Where-Object {$_.Name -like "*mosquitto*"} | Format-Table Id, ProcessName, StartTime

Write-Host ""
Write-Host "5. Simple connection test..." -ForegroundColor Yellow
Write-Host "Publishing test message..."
& ".\mosquitto_pub.exe" -h 192.168.24.32 -t test/simple -m "Hello from test"
Write-Host "Test message sent" -ForegroundColor Green

Write-Host ""
Write-Host "6. Testing ESP32 topic..." -ForegroundColor Yellow
Write-Host "Publishing to ESP32 topic..."
& ".\mosquitto_pub.exe" -h 192.168.24.32 -t "esp32/fire_alarm/data" -m '{"device_id":"test","temperature":25.0,"humidity":60.0,"flame":1500,"smoke":500}'
Write-Host "ESP32 test message sent" -ForegroundColor Green

Write-Host ""
Write-Host "=================================" -ForegroundColor Green
Write-Host "Test completed!" -ForegroundColor Green
Write-Host ""
Write-Host "If you see 1883 port in listening status, Mosquitto is running" -ForegroundColor Cyan
Write-Host "To monitor ESP32 data, run:" -ForegroundColor Cyan
Write-Host "mosquitto_sub.exe -h 192.168.24.32 -t `"esp32/#`" -v" -ForegroundColor Cyan
Write-Host ""
Read-Host "Press Enter to exit"