# PowerShell script to test Mosquitto connection
Write-Host "测试Mosquitto连接" -ForegroundColor Green
Write-Host "=================================" -ForegroundColor Green

Set-Location $PSScriptRoot

Write-Host "1. 测试本地连接..." -ForegroundColor Yellow
Start-Process cmd.exe -ArgumentList "/c", "mosquitto_sub.exe -h localhost -t test/local -t 1 -v" -WindowStyle Hidden
Start-Sleep -Seconds 1
& ".\mosquitto_pub.exe" -h localhost -t test/local -m "本地连接测试成功"
Start-Sleep -Seconds 2

Write-Host ""
Write-Host "2. 测试IP连接..." -ForegroundColor Yellow
Start-Process cmd.exe -ArgumentList "/c", "mosquitto_sub.exe -h 192.168.24.23 -t test/ip -t 1 -v" -WindowStyle Hidden
Start-Sleep -Seconds 1
& ".\mosquitto_pub.exe" -h 192.168.24.23 -t test/ip -m "IP连接测试成功"
Start-Sleep -Seconds 2

Write-Host ""
Write-Host "3. 显示监听状态..." -ForegroundColor Yellow
netstat -an | findstr :1883

Write-Host ""
Write-Host "4. 检查Mosquitto进程..." -ForegroundColor Yellow
Get-Process | Where-Object {$_.Name -like "*mosquitto*"} | Format-Table Id, ProcessName, StartTime

Write-Host ""
Write-Host "5. 简单连接测试..." -ForegroundColor Yellow
Write-Host "正在发布测试消息..."
& ".\mosquitto_pub.exe" -h 192.168.24.23 -t test/simple -m "Hello from test"
Write-Host "测试消息已发送" -ForegroundColor Green

Write-Host ""
Write-Host "=================================" -ForegroundColor Green
Write-Host "测试完成！" -ForegroundColor Green
Write-Host ""
Write-Host "如果看到监听状态显示1883端口，说明Mosquitto正在运行" -ForegroundColor Cyan
Write-Host "如果要监控ESP32数据，请运行:" -ForegroundColor Cyan
Write-Host "mosquitto_sub.exe -h 192.168.24.23 -t `"esp32/#`" -v" -ForegroundColor Cyan
Write-Host ""
Read-Host "按 Enter 键退出"