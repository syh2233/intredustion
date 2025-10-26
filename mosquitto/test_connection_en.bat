@echo off
chcp 65001 >nul
echo Testing Mosquitto Connection
echo =================================

cd /d "%~dp0"

echo 1. Testing local connection...
start /min cmd /c "mosquitto_sub.exe -h localhost -t test/local -t 1 -v"
timeout /t 1 >nul
mosquitto_pub.exe -h localhost -t test/local -m "Local connection test successful"
timeout /t 2 >nul

echo.
echo 2. Testing IP connection...
start /min cmd /c "mosquitto_sub.exe -h 192.168.24.23 -t test/ip -t 1 -v"
timeout /t 1 >nul
mosquitto_pub.exe -h 192.168.24.23 -t test/ip -m "IP connection test successful"
timeout /t 2 >nul

echo.
echo 3. Showing listening status...
netstat -an | findstr :1883

echo.
echo 4. Checking Mosquitto processes...
tasklist | findstr mosquitto

echo.
echo 5. Simple connection test...
echo Publishing test message...
mosquitto_pub.exe -h 192.168.24.23 -t test/simple -m "Hello from test"
echo Test message sent

echo.
echo 6. Testing ESP32 topic...
echo Publishing to ESP32 topic...
mosquitto_pub.exe -h 192.168.24.23 -t "esp32/fire_alarm/data" -m '{"device_id":"test","temperature":25.0,"humidity":60.0,"flame":1500,"smoke":500}'
echo ESP32 test message sent

echo.
echo =================================
echo Test completed!
echo.
echo If you see 1883 port in listening status, Mosquitto is running
echo To monitor ESP32 data, run:
echo mosquitto_sub.exe -h 192.168.24.23 -t "esp32/#" -v
echo.
pause