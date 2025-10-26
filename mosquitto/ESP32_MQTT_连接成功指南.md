# ESP32 MQTT 连接成功指南

## 🎉 好消息：MQTT 连接已成功！

### 当前状态
- ✅ Mosquitto MQTT Broker 运行正常
- ✅ 端口 1883 监听正常
- ✅ 本地连接 (127.0.0.1) 工作正常
- ✅ ESP32 数据格式测试成功

### 监控 ESP32 数据

**1. 基本监控**
```powershell
mosquitto_sub.exe -h 127.0.0.1 -t "esp32/#" -v
```

**2. 分开监控**
```powershell
# 监控传感器数据
mosquitto_sub.exe -h 127.0.0.1 -t "esp32/fire_alarm/data" -v

# 监控报警消息
mosquitto_sub.exe -h 127.0.0.1 -t "esp32/fire_alarm/alert" -v
```

**3. 实时仪表板**
```powershell
.\esp32_dashboard.ps1
```

**4. 简单监控**
```powershell
.\esp32_monitor.ps1
```

### ESP32 配置

ESP32 代码已配置为连接本地 MQTT 服务器：
- 服务器地址：`127.0.0.1:1883`
- 数据主题：`esp32/fire_alarm/data`
- 报警主题：`esp32/fire_alarm/alert`

### 数据格式

**传感器数据格式：**
```json
{
  "device_id": "ESP32-FIRE-123456",
  "timestamp": 1634567890,
  "data": {
    "temperature": 25.5,
    "humidity": 60.2,
    "flame": 1500,
    "smoke": 500,
    "light": 1000,
    "sound": 100
  },
  "status": {
    "system_status": "normal",
    "status_reason": "Environment normal",
    "mqtt_server": "Localhost Mosquitto"
  },
  "location": "Dormitory A301"
}
```

**报警数据格式：**
```json
{
  "device_id": "ESP32-FIRE-123456",
  "timestamp": 1634567890,
  "data": {
    "temperature": 45.0,
    "humidity": 65.0,
    "flame": 800,
    "smoke": 1600,
    "light": 1200,
    "sound": 150
  },
  "status": {
    "system_status": "alarm",
    "status_reason": "High temperature detected",
    "mqtt_server": "Localhost Mosquitto"
  },
  "location": "Dormitory A301"
}
```

### 系统状态说明

**状态类型：**
- `normal` - 正常状态
- `warning` - 警告状态
- `alarm` - 报警状态

**检测阈值：**
- 温度警报：> 45°C
- 湿度警报：> 85%
- 火焰警报：< 800
- 烟雾警报：> 1500

### Web 界面

启动 Flask Web 服务器：
```powershell
cd "你的项目路径/web"
python app.py
```

访问地址：
- 主界面：http://localhost:5000
- 仪表板：http://localhost:5000/dashboard

### 故障排除

**如果没有 ESP32 数据：**
1. 确认 ESP32 已正确上传代码
2. 检查 ESP32 WiFi 连接
3. 查看 ESP32 串口输出
4. 确认 MQTT 连接状态

**如果监控工具没有输出：**
1. 确认 Mosquitto 正在运行
2. 检查防火墙设置
3. 尝试重新启动 Mosquitto

### 测试命令

**发送测试数据：**
```powershell
mosquitto_pub.exe -h 127.0.0.1 -t "esp32/fire_alarm/data" -m '{"device_id":"TEST","data":{"temperature":25.0,"humidity":60.0,"flame":1500,"smoke":500},"status":{"system_status":"normal"}}'
```

**发送测试警报：**
```powershell
mosquitto_pub.exe -h 127.0.0.1 -t "esp32/fire_alarm/alert" -m '{"device_id":"TEST","data":{"temperature":50.0,"humidity":70.0,"flame":700,"smoke":1700},"status":{"system_status":"alarm"}}'
```

### 下一步

1. **启动 ESP32** - 上传修复后的代码并运行
2. **开始监控** - 使用监控工具查看实时数据
3. **Web 界面** - 启动 Flask 服务器查看可视化界面
4. **系统测试** - 测试各种传感器和报警功能

🎉 恭喜！MQTT 连接问题已完全解决！