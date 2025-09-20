# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is an ESP32-based dormitory fire alarm system project that implements real-time fire detection using multiple sensors (flame, smoke, temperature, humidity) with a web monitoring interface.

## Development Environment

### ESP32 Development
- **IDE**: Thonny IDE
- **Firmware**: MicroPython 1.19+
- **Core Libraries**: umqtt.simple/robust, ssd1306, urequests, network, machine
- **Sensor Interfaces**: 
  - Flame sensor (GPIO34, ADC input)
  - MQ-2 smoke sensor (GPIO35, ADC input) 
  - DHT22 temperature/humidity sensor (GPIO32, digital)
  - OLED display (GPIO21/22, I2C)

### Server Development
- **Backend**: Flask 3.0+
- **Database**: SQLite 3.35+
- **MQTT Broker**: Mosquitto 2.0+
- **Python Version**: 3.9+
- **Key Dependencies**: flask-cors, flask-mqtt, flask-socketio, paho-mqtt

## Common Development Commands

### Running the Flask Web Server
```bash
cd web
python app.py
```
访问地址：http://localhost:5000 (5层架构界面) 或 http://localhost:5000/dashboard (详细仪表板)

### Installing Dependencies
```bash
cd web
pip install -r requirements.txt
# 如果requirements.txt为空，手动安装核心依赖：
pip install flask flask-cors flask-mqtt flask-socketio paho-mqtt flask-sqlalchemy
```

### Testing the System
```bash
# 运行完整系统测试
cd web
python test_system.py

# 运行快速场景测试
python test_quick_scenarios.py

# 运行火灾报警场景测试
python test_fire_alarm_scenarios.py

# 测试cpolar内网穿透
python test_cpolar.py
```

### Setting up Mosquitto MQTT Broker (Windows)
```bash
# Install Mosquitto for Windows
# Download from: https://mosquitto.org/download/
# Install as Windows service:
cd "C:\Program Files\mosquitto"
mosquitto install
net start mosquitto

# 验证MQTT服务运行状态
mosquitto_sub -t "test" -v
```

## Project Architecture

### System Layers
- **感知层 (Perception)**: Flame sensor, MQ-2 smoke sensor, DHT22 temperature/humidity sensor
- **控制层 (Control)**: ESP32 main controller with fire detection algorithms
- **执行层 (Execution)**: OLED display, cooling fan, alarm indicators  
- **应用层 (Application)**: Flask web platform with real-time monitoring

### Key Algorithms
- **Dynamic Threshold Adjustment**: Automatically adjusts detection thresholds based on environmental conditions
- **Multi-sensor Fusion**: Combines flame, smoke, temperature, and humidity data for accurate fire detection
- **False Alarm Prevention**: Uses consecutive detection and trend analysis to reduce false positives

### 火灾报警判断逻辑 (app.py:368-380)
系统基于多传感器数据进行智能火灾报警判断：

```python
# 警报条件 (任一满足即触发)
flame_value < 1000    # 火焰传感器值低表示检测到火焰
smoke_level > 100    # 烟雾浓度过高
temperature > 40      # 温度过高

# 警告条件 (任一满足即触发)
flame_value < 1100    # 火焰传感器值偏低
smoke_level > 50     # 烟雾浓度中等
temperature > 35      # 温度偏高
```

**状态分类**: 正常 → 警告 → 警报 (三级状态机制)

### Communication Protocols
- **MQTT**: Real-time data transmission and alert notifications
- **HTTP**: Data upload and configuration queries
- **WebSocket**: Real-time web interface updates

## Hardware Configuration

### Pin Mapping
- GPIO34: Flame sensor (ADC input)
- GPIO35: MQ-2 smoke sensor (ADC input) 
- GPIO32: DHT22 temperature/humidity sensor (digital)
- GPIO21/22: OLED display (I2C SDA/SCL)
- GPIO23: Fan control (PWM output)

### Safety Notes
- MQ-2 sensor requires 24-48 hour warm-up period for stability
- MQ-2 output voltage must be ≤3.3V when using 5V power supply
- Use voltage divider or op-amp to scale sensor outputs to ESP32 ADC range

## Database Schema

The system uses SQLite with these main tables:
- `sensor_data`: Stores real-time sensor readings
- `alert_history`: Records fire alarm events
- `environment_alerts`: Environmental risk warnings
- `devices`: Device information and status
- `environment_thresholds`: Configurable thresholds

## MQTT Topics

### Device Data Publishing
- `esp32/{device_id}/data/json` - Sensor data
- `esp32/{device_id}/status/online` - Device online status
- `esp32/{device_id}/alert/fire` - Fire alarm notifications

### Server Commands
- `server/{device_id}/cmd/config` - Configuration updates
- `server/{device_id}/cmd/reboot` - Device restart
- `server/{device_id}/cmd/threshold` - Threshold adjustments

## API Endpoints

### Data APIs
- `POST /api/data` - 接收传感器数据 (备用HTTP接口)
- `GET /api/data/recent?limit=20&device_id=` - 获取最近的传感器数据
- `GET /api/data/range?start=&end=&device_id=` - 获取指定时间范围的数据

### Device APIs (火灾报警系统专用)
- `GET /api/devices` - 获取所有设备状态和火灾报警状态
- `GET /api/history` - 获取最近24小时的报警历史

### Alert APIs  
- `GET /api/alerts` - 获取报警历史记录
- Note: 实际报警处理通过MQTT主题 `esp32/{device_id}/alert/fire` 实现

### WebSocket Events
- `connect` - 客户端连接事件，发送初始设备数据
- `disconnect` - 客户端断开连接事件
- `request_device_update` - 请求设备状态更新
- `devices_update` - 服务器推送设备状态更新
- `alarm` - 火灾报警通知推送
- `sensor_data` - 传感器实时数据推送 (旧接口)
- `alert_data` - 报警数据推送
- `connection_status` - 连接状态确认

## Testing and Validation

### Hardware Testing
```bash
# Test individual sensors using MicroPython REPL
# Connect to ESP32 via Thonny IDE
import machine
adc = machine.ADC(machine.Pin(34))
print(adc.read())  # Read flame sensor
```

### Web Interface Testing
- Access web interface at: http://localhost:5000
- Real-time data updates every 1.5 seconds
- Mobile-responsive design supported

## Deployment Considerations

### Private Cloud Setup
- Supports Windows server deployment with port forwarding
- Uses Nginx/IIS reverse proxy for SSL termination
- Mosquitto MQTT broker for real-time messaging
- Automatic backup and data retention policies

### Network Configuration
- Required ports: 80/443 (web), 1883/8883 (MQTT), 8083 (MQTT WebSocket)
- Supports DDNS for dynamic IP addresses
- SSL/TLS encryption for all communications

### 内网穿透配置 (Cpolar)
项目支持通过cpolar实现内网穿透，可以从公网访问：

```bash
# 启动cpolar隧道
cpolar http 5000          # Web界面隧道
cpolar tcp 1883          # MQTT Broker隧道

# 测试公网访问
python test_cpolar.py
```

**配置文件**: `web/cpolar配置指南.md` 包含详细的公网访问地址和ESP32配置示例。

**主要功能**:
- HTTPS加密的Web监控界面
- MQTT Broker公网访问
- WebSocket实时通信支持
- ESP32设备远程连接

## File Structure
```
/
├── web/                          # Flask web application
│   ├── app.py                   # Main Flask application with MQTT, WebSocket, API routes
│   ├── requirements.txt         # Python dependencies
│   ├── test_system.py          # Complete system integration tests
│   ├── test_quick_scenarios.py # Quick test scenarios
│   ├── test_fire_alarm_scenarios.py # Fire alarm specific tests
│   ├── test_cpolar.py          # Cpolar tunnel testing
│   ├── cpolar配置指南.md        # Cpolar configuration guide
│   ├── 端口映射配置指南.md      # Port mapping guide
│   ├── templates/              # HTML templates
│   │   ├── index.html         # 5-layer architecture main interface
│   │   ├── dashboard.html     # Detailed monitoring dashboard
│   │   └── index_old.html     # Legacy interface
│   ├── static/                # Static assets
│   │   ├── css/
│   │   │   └── style.css      # Main stylesheet
│   │   └── js/
│   │       ├── main.js        # Main interface JavaScript
│   │       └── dashboard.js   # Dashboard JavaScript
│   └── .venv/                 # Virtual environment
├── 整体/                      # System architecture documents
├── 项目计划进度表/             # Project planning documents
└── .claude/                   # Claude Code configuration
```

## Development Notes
- 每次回答都使用中文回答我
- The project uses Chinese documentation and comments
- Hardware and software are designed for dormitory safety scenarios
- Emphasis on false alarm reduction and environmental adaptation
- Supports both local and cloud deployment options