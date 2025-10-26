@echo off
echo 测试Mosquitto连接
echo =================================

cd /d "%~dp0"

echo 1. 测试本地连接...
start /min cmd /c "mosquitto_sub.exe -h localhost -t test/local -t 1 -v"
timeout /t 1 >nul
mosquitto_pub.exe -h localhost -t test/local -m "本地连接测试成功"
timeout /t 2 >nul

echo.
echo 2. 测试IP连接...
start /min cmd /c "mosquitto_sub.exe -h 192.168.24.23 -t test/ip -t 1 -v"
timeout /t 1 >nul
mosquitto_pub.exe -h 192.168.24.23 -t test/ip -m "IP连接测试成功"
timeout /t 2 >nul

echo.
echo 3. 显示监听状态...
netstat -an | findstr :1883

echo.
echo 4. 检查Mosquitto进程...
tasklist | findstr mosquitto

echo.
echo 5. 简单连接测试...
echo 正在发布测试消息...
mosquitto_pub.exe -h 192.168.24.23 -t test/simple -m "Hello from test"
echo 测试消息已发送

echo.
echo =================================
echo 测试完成！
echo.
echo 如果看到监听状态显示1883端口，说明Mosquitto正在运行
echo 如果要监控ESP32数据，请运行:
echo mosquitto_sub.exe -h 192.168.24.23 -t "esp32/#" -v
echo.
pause