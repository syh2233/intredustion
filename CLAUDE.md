# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is an ESP32-based dormitory fire alarm system project that implements real-time fire detection using multiple sensors (flame, smoke, temperature, humidity, light, sound) with a web monitoring interface. The system features a 5-layer architecture with MQTT communication, real-time monitoring, and both local and cloud deployment capabilities.

## Development Environment

### ESP32 Development
- **IDE**: Thonny IDE
- **Firmware**: MicroPython 1.19+
- **Core Libraries**: umqtt.simple/robust, ssd1306, dht, network, machine, socket
- **Sensor Interfaces**:
  - Flame sensor (GPIO14, ADC input) - 主要传感器
  - MQ-2 smoke sensor (GPIO34 ADC, GPIO2 digital)
  - DHT11 temperature/humidity sensor (GPIO4, digital)
  - BH1750 light sensor (GPIO21/22, I2C)
  - Sound sensor (GPIO13 ADC, GPIO35 digital)
  - OLED display (GPIO25/26, I2C)
  - Servo motor (GPIO15, PWM)

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
```

如果requirements.txt为空，手动安装核心依赖：
```bash
pip install flask flask-cors flask-socketio flask-sqlalchemy paho-mqtt python-dateutil
```

### Testing the System
```bash
# 运行ESP32主机-从机通信测试
cd 传感器结合
python test_master_slave.py

# 运行ESP32 MQTT连接测试 (需要在ESP32设备上运行)
python test_esp32_mqtt.py

# 运行系统模拟测试
python fire_alarm_simulation_simple.py

# 运行MQTT通用监控工具
python mqtt_monitor_universal.py
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

### 火灾报警判断逻辑 (main.py:416-463)
系统基于多传感器数据进行智能火灾报警判断：

```python
# 警报条件 (任一满足即触发)
flame_analog < 500     # 火焰传感器值低表示检测到火焰
mq2_analog < 1000     # MQ2烟雾传感器值低表示烟雾浓度高
temperature > 40       # 温度过高
light_level > 30       # 光照强度过高

# 警告条件 (任一满足即触发)
flame_analog < 1000    # 火焰传感器值偏低
mq2_analog < 1500      # 烟雾浓度中等
temperature > 35       # 温度偏高
light_level > 20       # 光照强度偏高
```

**状态分类**: 正常 → 警告 → 警报 (三级状态机制)
**舵机控制**: 连续3次警报才启动舵机，防止误报

### Communication Protocols
- **MQTT**: Real-time data transmission and alert notifications
- **HTTP**: Data upload and configuration queries
- **WebSocket**: Real-time web interface updates

## Hardware Configuration

### Pin Mapping (main.py:66-84)
- GPIO14: Flame sensor (ADC input) - 主要传感器
- GPIO34: MQ-2 smoke sensor (ADC input)
- GPIO2: MQ-2 smoke sensor (digital input)
- GPIO4: DHT11 temperature/humidity sensor (digital)
- GPIO13: Sound sensor (ADC input)
- GPIO35: Sound sensor (digital input)
- GPIO15: Servo motor (PWM output)
- GPIO21/22: BH1750 light sensor (I2C SDA/SCL)
- GPIO25/26: OLED display (I2C SDA/SCL)

### Safety Notes
- MQ-2 sensor requires 24-48 hour warm-up period for stability
- MQ-2 output voltage must be ≤3.3V when using 5V power supply
- Use voltage divider or op-amp to scale sensor outputs to ESP32 ADC range

## Database Schema

The system uses SQLite with these main tables (app.py:146-184):
- `sensor_data`: Stores real-time sensor readings including flame, smoke, temperature, humidity, light_level
- `alert_history`: Records fire alarm events with severity and resolution status
- `device_info`: Device information and status tracking
- All tables include device_id for multi-device support

## MQTT Topics

### Device Data Publishing (main.py:690-715)
- `esp32/{device_id}/data/json` - Sensor data with all readings
- `esp32/{device_id}/alert/fire` - Fire alarm notifications
- `esp32/{device_id}/alert/warning` - Warning notifications

### Server Subscriptions (app.py:84-86)
- `esp32/+/data/json` - Subscribe to all device sensor data
- `esp32/+/alert/#` - Subscribe to all alert types
- `esp32/+/status/#` - Subscribe to device status updates

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

### WebSocket Events (app.py:226-258)
- `sensor_data` - Real-time sensor data push (legacy interface)
- `devices_update` - Device status updates for 5-layer UI
- `alarm` - Fire alarm notifications with location and sensor data
- `alert_data` - Alert data push for real-time updates

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
├── 传感器结合/                   # ESP32核心代码文件夹
│   ├── main.py                 # ESP32主机主程序(1130行)
│   ├── esp32_slave_simple.py   # ESP32从机简化版(683行)
│   ├── esp32_slave.py          # ESP32从机完整版
│   ├── master_slave_config.py  # 主从机统一配置文件
│   ├── slave_config.py         # 从机独立配置文件
│   ├── host_udp_receiver.py    # UDP接收器(独立运行)
│   ├── test_master_slave.py    # 主从机通信测试
│   ├── test_esp32_mqtt.py      # MQTT连接测试
│   ├── flame_sensor_calibration.py # 火焰传感器校准
│   ├── mqtt_monitor.py         # MQTT监控工具
│   └── dht11_simple.py         # DHT11传感器测试
├── web/                        # Flask Web应用
│   ├── app.py                  # Flask主应用(618行)
│   ├── esp32_dht22_sensor.py   # ESP32传感器模拟器
│   ├── requirements.txt        # Python依赖
│   ├── templates/              # HTML模板
│   │   ├── index.html         # 5层架构主界面
│   │   ├── dashboard.html     # 详细监控仪表板
│   │   └── monitor.html       # 监控界面
│   ├── static/                 # 静态资源
│   │   ├── css/style.css      # 主样式表(17789行)
│   │   └── js/                # JavaScript文件
│   │       ├── main.js        # 主界面JS(39283行)
│   │       └── dashboard.js   # 仪表板JS(21572行)
│   └── .venv/                 # 虚拟环境
├── 整体/                      # 系统架构文档
├── 项目计划进度表/             # 项目管理文档
├── 烧录/                      # ESP32烧录相关文件
└── .claude/                   # Claude Code配置
```

## Key Implementation Details

### ESP32 Main Application (传感器结合/main.py)
- Uses custom MQTT client implementation for reliability
- Implements network connectivity testing and diagnostics
- Features OLED real-time display of sensor data
- Servo motor control for physical alarm activation
- Multi-sensor fusion with environmental adaptation

### Flask Web Server (web/app.py)
- Dual interface support: 5-layer architecture and detailed dashboard
- Real-time data processing via MQTT and WebSocket
- Automatic device registration and status tracking
- Timezone handling for Beijing time (UTC+8)
- Comprehensive error logging and diagnostics

### System Integration
- Supports both local deployment and cloud access via cpolar
- MQTT communication with public tunneling for remote access
- Database auto-creation and schema management
- Real-time alerts with multiple notification channels

### ESP32主机-从机系统架构 (Master-Slave System)
- **主从机通信**: ESP32主机通过UDP协议接收多个从机数据
- **主机功能**: 完整的传感器监测 + UDP服务器 + MQTT通信 + OLED显示
- **从机功能**: 简化的火焰和烟雾监测 + UDP数据发送 + LED状态指示
- **数据整合**: 主机整合自身传感器数据和所有从机数据，统一通过MQTT上传
- **多从机支持**: 支持同时连接多个从机ESP32设备
- **状态监控**: 主机实时监控所有从机的在线状态和数据

### 主机增强功能 (main.py更新)
- **UDP服务器**: 内置UDP服务器监听8888端口
- **从机管理**: 自动发现、注册和管理从机设备
- **数据处理**: 实时处理从机传感器数据并触发相应警报
- **状态监控**: 每30个循环检查从机在线状态，自动标记离线从机
- **数据整合**: 将从机数据与主机数据统一处理和显示

### 从机设计要点 (esp32_slave_simple.py)
- **硬件简化**: 只需火焰传感器(GPIO14)和MQ2烟雾传感器(GPIO34/2) + LED(GPIO5)
- **WiFi通信**: 与主机ESP32同一WiFi网络，自动连接到主机UDP服务器
- **状态指示**: LED指示灯显示系统状态(正常/警告/警报)
- **容错机制**: WiFi断开自动重连，数据发送失败自动重试
- **配置灵活**: 通过配置文件轻松修改主机IP和传感器阈值

### 部署配置
- **配置文件**: `master_slave_config.py` 统一管理主机和从机配置
- **主机IP**: 从机需要配置主机的实际IP地址
- **网络要求**: 主机和所有从机必须在同一WiFi网络下
- **端口配置**: UDP通信使用8888端口，确保网络允许UDP通信

## Development Notes
- 每次回答都使用中文回答我
- The project uses Chinese documentation and comments
- Hardware and software are designed for dormitory safety scenarios
- Emphasis on false alarm reduction and environmental adaptation
- Supports both local and cloud deployment options

## 代码开发规范
- ESP32代码使用MicroPython，采用模块化设计
- Web应用使用Flask框架，支持MQTT和WebSocket实时通信
- 数据库使用SQLite，支持多设备数据存储
- 配置文件统一管理，便于部署和维护
- 测试文件覆盖主要功能模块，确保系统稳定性

## 常见开发任务
1. **添加新传感器**: 修改main.py和对应的配置文件
2. **修改报警阈值**: 更新master_slave_config.py中的阈值设置
3. **扩展从机数量**: 在配置文件中添加新的从机配置
4. **自定义Web界面**: 修改web/templates/和web/static/中的文件
5. **调试MQTT连接**: 使用test_esp32_mqtt.py和mqtt_monitor.py工具
6. **测试主从机通信**: 使用test_master_slave.py进行通信测试