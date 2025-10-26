@echo off
chcp 65001 >nul
echo Starting Mosquitto MQTT Broker...
echo =================================

cd /d "%~dp0"

echo Stopping existing service...
net stop mosquitto >nul 2>&1
timeout /t 2 >nul

echo Starting Mosquitto with new configuration...
echo Config file: mosquitto_simple.conf
echo Port: 1883 (all interfaces)
echo Allow anonymous: Yes

echo.
echo Starting service...
mosquitto.exe -c mosquitto_simple.conf -v

echo.
echo =================================
echo Service stopped
pause