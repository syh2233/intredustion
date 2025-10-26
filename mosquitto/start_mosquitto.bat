@echo off
echo 正在启动Mosquitto MQTT Broker...
echo =================================

cd /d "%~dp0"

echo 停止现有服务...
net stop mosquitto >nul 2>&1
timeout /t 2 >nul

echo 使用新配置启动Mosquitto...
echo 配置文件: mosquitto_simple.conf
echo 监听端口: 1883 (所有接口)
echo 允许匿名连接: 是

echo.
echo 正在启动服务...
mosquitto.exe -c mosquitto_simple.conf -v

echo.
echo =================================
echo 服务已停止运行
pause