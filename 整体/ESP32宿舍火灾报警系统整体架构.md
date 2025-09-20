# 基于ESP32的宿舍火灾报警系统整体架构

---

## 1. 课题总体设计

### （1）系统架构规划
确定宿舍火灾报警系统的整体框架，包括：
- **感知层**：火焰传感器、MQ-2烟雾传感器
- **控制层**：ESP32主控
- **执行层**：报警、OLED显示
- **应用层**：Flask Web平台

构建完整的火灾检测、报警、监控体系。

### （2）功能模块划分
划分以下功能模块：
- **传感器数据采集模块**
- **数据处理与判断模块**
- **本地显示与报警模块**
- **网络通信模块**
- **Web监控模块**

明确各模块间的数据流向和交互方式。

---

## 2. 硬件设计

### （1）器件选型及分析

| 器件 | 型号/规格 | 功能说明 | 技术特点 |
|------|-----------|----------|----------|
| **ESP32模块** | ESP32-WROOM-32 | 主控制器 | 双核处理器、Wi-Fi、ADC、I2C接口 |
| **火焰传感器** | 红外火焰传感器 | 火焰检测 | 红外光谱检测、抗光干扰 |
| **MQ-2传感器** | MQ-2气体传感器 | 烟雾检测 | 可燃气体检测、需预热 |
| **OLED显示屏** | 0.96寸 SSD1306 | 本地显示 | I2C接口、128×64分辨率 |
| **风扇执行器** | 5V直流风扇 | 散热降温 | 自动温控、PWM调速 |
| **电源管理** | 5V/3.3V稳压 | 供电管理 | 稳压输出、滤波保护 |

### （2）电路设计

#### 传感器接口电路
- 火焰传感器：GPIO34 (ADC1_CH6)
- MQ-2传感器：GPIO35 (ADC1_CH7)
- 信号调理：确保输出电压在0-3.3V范围内

#### ESP32接口电路
- I2C接口：GPIO21/SDA、GPIO22/SCL（OLED）
- GPIO输出：风扇控制信号
- ADC输入：传感器模拟信号采集

#### 保护电路
- 输入信号保护电路
- 风扇续流二极管保护
- 电源滤波和去耦电路

### （3）PCB设计

#### 布局规划
- 合理布局ESP32主控、传感器接口、OLED接口
- 缩短信号连线，减少电磁干扰
- 电源管理区域独立布局

#### 布线优化
- 模拟信号线短而粗
- 数字信号线与模拟信号线分离
- 电源线加粗处理
- 关键信号线屏蔽保护

### （4）组装调试

#### 硬件组装
- 按电路图连接各模块
- 焊接接口端子
- 连接外部设备

#### 初步调试
- 通电测试各模块功能
- 测量关键节点电压
- 验证传感器输出信号

#### 故障排除
- 解决传感器信号不稳定问题
- 修复OLED显示异常
- 确保风扇驱动正常工作

---

## 3. 硬件平台软件程序编程

### （1）开发环境搭建
- **IDE**：Thonny IDE
- **固件**：MicroPython for ESP32
- **库文件**：urequests、ssd1306、network等
- **MQTT库**：umqtt.simple、umqtt.robust

### （2）程序设计

#### 数据采集程序
```python
# 传感器数据采集
def read_sensors():
    flame_value = read_flame_sensor()  # GPIO34
    smoke_value = read_smoke_sensor()  # GPIO35
    return apply_filter(flame_value, smoke_value)
```

#### 数据处理与判断
- 火灾检测算法
- 动态阈值判断
- 防误报逻辑
- 去抖处理

#### 本地显示程序
- OLED驱动程序
- 传感器数据显示
- 报警状态显示
- 系统状态指示

#### 网络通信程序
- Wi-Fi连接管理
- HTTP POST数据上传
- MQTT实时数据传输
- 断网重连机制
- 数据缓存策略

#### MQTT通信程序
```python
# MQTT客户端配置
from umqtt.robust import MQTTClient
import ujson
import utime
import ussl
import urequests

# MQTT配置（支持SSL）
MQTT_CLIENT = MQTTClient(
    client_id=DEVICE_ID,
    server=MQTT_BROKER,
    port=MQTT_PORT,
    user=MQTT_USER,
    password=MQTT_PASS,
    ssl=True,  # 启用SSL
    ssl_params={
        'server_hostname': MQTT_BROKER,
        'cert_reqs': ussl.CERT_NONE  # 生产环境应使用证书验证
    }
)

# 连接回调
def mqtt_connect():
    try:
        MQTT_CLIENT.connect()
        print("MQTT连接成功")
        # 发布设备上线状态
        publish_status("online")
        return True
    except:
        print("MQTT连接失败")
        return False

# 发布传感器数据
def publish_sensor_data(flame, smoke, alert):
    payload = {
        "device_id": DEVICE_ID,
        "timestamp": utime.time(),
        "data": {
            "flame": flame,
            "smoke": smoke
        },
        "status": {
            "alert": alert,
            "wifi_rssi": get_wifi_rssi()
        }
    }
    
    try:
        MQTT_CLIENT.publish(MQTT_TOPIC_DATA, ujson.dumps(payload))
        print("MQTT数据发布成功")
    except:
        print("MQTT数据发布失败")

# 发布报警信息
def publish_alert(alert_type, severity):
    payload = {
        "device_id": DEVICE_ID,
        "alert_type": alert_type,
        "severity": severity,
        "timestamp": utime.time(),
        "location": "宿舍A栋301"
    }
    
    try:
        MQTT_CLIENT.publish(MQTT_TOPIC_ALERT, ujson.dumps(payload))
        print("MQTT报警发布成功")
    except:
        print("MQTT报警发布失败")

# 发布设备状态
def publish_status(status):
    payload = {
        "device_id": DEVICE_ID,
        "status": status,
        "timestamp": utime.time()
    }
    
    try:
        MQTT_CLIENT.publish(MQTT_TOPIC_STATUS, ujson.dumps(payload))
    except:
        pass
```

#### 设备控制程序
- 风扇PWM控制
- 报警状态管理
- 自动散热功能

### （3）代码优化与测试

#### 优化方向
- 数据采集算法优化
- 网络通信功耗优化
- 显示刷新频率优化
- 内存管理优化

#### 测试内容
- 传感器数据准确性测试
- 报警判断正确性测试
- 网络传输可靠性测试
- 长时间稳定性测试

---

## 4. 通信协议设计

### （1）协议选择
- **HTTP协议**：用于配置查询、历史数据获取
- **MQTT协议**：用于实时数据传输、报警推送
- **数据格式**：JSON
- **通信方式**：POST请求 + 发布订阅

### （2）数据格式定义

#### 上传数据格式
```json
{
  "device_id": "ESP32-001",
  "flame": 1032,
  "smoke": 1450,
  "alert": true,
  "timestamp": "2024-01-01T12:00:00"
}
```

#### 响应数据格式
```json
{
  "status": "success",
  "message": "Data received",
  "server_time": "2024-01-01T12:00:01"
}
```

### （3）协议实现

#### ESP32端实现
- 数据封装
- HTTP POST发送
- 错误处理
- 重试机制

#### 服务器端实现
- 数据接收
- JSON解析
- 数据存储
- 响应返回

### （4）错误处理机制
- 网络异常处理
- 数据发送失败重试
- 本地数据缓存
- 连接状态监控

---

## 5. 云平台设计

### （1）通信协议架构

#### HTTP + MQTT 双协议设计
系统采用HTTP和MQTT双协议架构，满足不同场景需求：

**HTTP协议**：
- 用于初始配置和数据查询
- RESTful API接口
- 请求-响应模式
- 适用于Web端数据获取

**MQTT协议**：
- 用于实时数据传输
- 发布-订阅模式
- 低功耗、低带宽
- 适用于实时报警和监控

### （2）MQTT架构设计

#### MQTT Broker配置
```yaml
# 私有云MQTT Broker配置
broker:
  host: "your-domain.com"  # 你的域名
  port: 8883              # SSL加密端口
  username: "esp32_user"
  password: "secure_password"
  qos: 1
  retain: true
  ssl: true               # 启用SSL
```

#### 主题设计 (Topic Design)
```
# 设备数据上报
esp32/{device_id}/data/json          # 传感器数据JSON格式
esp32/{device_id}/data/structured     # 结构化数据
esp32/{device_id}/status/online      # 设备上线状态
esp32/{device_id}/status/offline     # 设备离线状态
esp32/{device_id}/alert/fire          # 火灾报警
esp32/{device_id}/alert/smoke         # 烟雾报警

# 服务器下发指令
server/{device_id}/cmd/reset         # 重置设备
server/{device_id}/cmd/config        # 配置更新
server/{device_id}/cmd/reboot        # 重启设备
server/{device_id}/cmd/threshold     # 阈值调整

# 系统管理主题
system/all/broadcast                 # 系统广播
system/all/heartbeat                 # 心跳检测
system/monitor/status               # 监控状态
```

#### MQTT数据格式
```json
// 传感器数据发布
{
  "device_id": "ESP32-001",
  "timestamp": "2024-01-01T12:00:00Z",
  "data": {
    "flame": 1032,
    "smoke": 1450,
    "temperature": 25.5,
    "humidity": 65.0
  },
  "status": {
    "alert": false,
    "battery": 85,
    "wifi_rssi": -65
  }
}

// 报警数据发布
{
  "device_id": "ESP32-001", 
  "alert_type": "fire",
  "severity": "high",
  "timestamp": "2024-01-01T12:00:00Z",
  "sensor_values": {
    "flame": 450,
    "smoke": 2100
  },
  "location": "宿舍A栋301"
}
```

### （3）私有云平台集成

#### 私有云架构设计
采用MQTT Broker与Flask后端服务器集成的私有云架构：

**核心组件**：
- **Mosquitto MQTT Broker**：轻量级开源MQTT消息服务器
- **Flask Web服务器**：提供RESTful API和Web界面
- **SQLite数据库**：数据存储和历史记录
- **Nginx反向代理**：端口映射和负载均衡
- **Let's Encrypt SSL证书**：安全加密传输

#### 私有云部署架构
```
[ESP32设备] → Internet → [路由器端口映射] → [Nginx] → [Mosquitto Broker]
                                      ↓
                                [Flask服务器] ← → [SQLite数据库]
                                      ↓
                                [Web客户端]
```

#### 端口映射配置

**Linux方案（Nginx）**：
```nginx
# Nginx配置示例
server {
    listen 80;
    server_name mqtt.example.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl;
    server_name mqtt.example.com;
    
    ssl_certificate /etc/letsencrypt/live/mqtt.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/mqtt.example.com/privkey.pem;
    
    # MQTT端口映射 (WebSocket支持)
    location /mqtt {
        proxy_pass http://localhost:1883;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
    }
    
    # Web界面端口映射
    location / {
        proxy_pass http://localhost:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

**Windows方案（IIS）**：
1. 安装IIS功能（包含URL重写和反向代理）
2. 配置反向代理规则：
   - MQTT WebSocket代理到localhost:8083
   - Web界面代理到localhost:5000

**Windows方案（Apache）**：
```apache
# httpd.conf 配置
LoadModule proxy_module modules/mod_proxy.so
LoadModule proxy_http_module modules/mod_proxy_http.so
LoadModule proxy_wstunnel_module modules/mod_proxy_wstunnel.so
LoadModule ssl_module modules/mod_ssl.so

# SSL虚拟主机
<VirtualHost *:443>
    ServerName mqtt.example.com
    SSLEngine on
    SSLCertificateFile "C:\certs\server.pem"
    SSLCertificateKeyFile "C:\certs\server.key"
    
    # WebSocket代理
    ProxyPass /mqtt ws://localhost:8083
    ProxyPassReverse /mqtt ws://localhost:8083
    
    # Web界面代理
    ProxyPass / http://localhost:5000/
    ProxyPassReverse / http://localhost:5000/
</VirtualHost>
```

#### Mosquitto配置

**Linux配置**：
```conf
# /etc/mosquitto/mosquitto.conf
listener 1883
protocol mqtt

listener 8883
protocol mqtt
certfile /etc/mosquitto/certs/server.pem
keyfile /etc/mosquitto/certs/server.key

listener 8083
protocol websockets

allow_anonymous false
password_file /etc/mosquitto/passwd
acl_file /etc/mosquitto/acl

# 日志配置
log_dest file /var/log/mosquitto/mosquitto.log
log_type error
log_type warning
log_type notice
log_type information
```

**Windows配置**：
```conf
# C:\Program Files\mosquitto\mosquitto.conf
listener 1883
protocol mqtt

listener 8883
protocol mqtt
certfile C:\certs\server.pem
keyfile C:\certs\server.key

listener 8083
protocol websockets

allow_anonymous false
password_file C:\Program Files\mosquitto\pwfile

# 日志配置
log_dest file C:\Program Files\mosquitto\mosquitto.log
log_type error
log_type warning
log_type notice
log_type information
```

#### 安全配置
- **设备认证**：MQTT用户名/密码认证
- **SSL/TLS加密**：所有通信采用HTTPS和MQTTS
- **访问控制**：基于主题的ACL权限控制
- **端口安全**：仅开放必要端口（80/443/1883/8883）
- **防火墙配置**：限制IP访问频率

#### Windows私有云部署步骤

1. **Windows服务器准备**
   - Windows 10/11 专业版或企业版
   - 启用IIS功能（可选，用于Web托管）
   - 配置静态IP地址
   - 开放防火墙端口

2. **安装Mosquitto MQTT Broker (Windows版)**
   - 下载：https://mosquitto.org/download/
   - 安装：运行mosquitto-2.x.x-install-windows-x64.exe
   - 安装路径：C:\Program Files\mosquitto\
   - 服务安装：以管理员身份运行
     ```cmd
     cd "C:\Program Files\mosquitto"
     mosquitto install
     net start mosquitto
     ```

3. **配置MQTT用户认证**
   ```cmd
   cd "C:\Program Files\mosquitto"
   mosquitto_passwd -c pwfile esp32_user
   # 输入密码
   ```

4. **修改Mosquitto配置文件**
   编辑 `C:\Program Files\mosquitto\mosquitto.conf`：
   ```conf
   listener 1883
   protocol mqtt
   
   listener 8883
   protocol mqtt
   certfile C:\certs\server.pem
   keyfile C:\certs\server.key
   
   listener 8083
   protocol websockets
   
   allow_anonymous false
   password_file C:\Program Files\mosquitto\pwfile
   
   log_dest file C:\Program Files\mosquitto\mosquitto.log
   log_type error
   log_type warning
   log_type notice
   log_type information
   ```

5. **安装Python和Flask应用**
   ```cmd
   # 安装Python（如果未安装）
   # 下载：https://www.python.org/downloads/
   
   # 安装依赖包
   pip install flask flask-cors flask-mqtt flask-socketio paho-mqtt
   
   # 启动Flask应用
   python app.py
   ```

6. **配置SSL证书（可选）**
   - 使用Let's Encrypt Windows客户端：win-acme
   - 或使用自签名证书（仅测试用）
   ```cmd
   # 生成自签名证书
   openssl req -x509 -newkey rsa:4096 -keyout key.pem -out cert.pem -days 365 -nodes
   ```

7. **配置端口映射**
   - 登录路由器管理界面
   - 设置端口转发（Port Forwarding）：
     - 外部端口80 → 内部IP:80
     - 外部端口443 → 内部IP:443  
     - 外部端口8883 → 内部IP:8883
     - 外部端口8083 → 内部IP:8083

8. **Windows防火墙配置**
   - 打开"Windows Defender 防火墙"
   - 添加入站规则：
     - TCP端口1883（MQTT）
     - TCP端口8883（MQTTS）
     - TCP端口8083（MQTT WebSocket）
     - TCP端口5000（Flask应用）

9. **启动服务**
   ```cmd
   # 重启Mosquitto服务
   net stop mosquitto
   net start mosquitto
   
   # 启动Flask应用
   python app.py
   ```

#### Windows服务自启动配置
1. **Mosquitto服务**：已自动配置为Windows服务
2. **Flask应用自启动**：
   - 使用Windows任务计划程序
   - 或创建Windows服务（使用nssm工具）

#### 使用nssm将Flask应用注册为Windows服务
```cmd
# 下载nssm：https://nssm.cc/
nssm install FlaskService "C:\Python39\python.exe" "C:\project\app.py"
nssm start FlaskService
```

### （4）本地服务器平台设计

#### 技术栈
- **后端框架**：Flask
- **数据库**：SQLite
- **API设计**：RESTful
- **MQTT集成**：Flask-MQTT
- **实时通信**：Flask-SocketIO
- **跨域支持**：Flask-CORS

#### 功能模块
- 设备接入管理
- MQTT消息订阅和发布
- 数据存储管理
- API接口服务
- 实时数据处理
- WebSocket实时推送

#### MQTT集成示例
```python
# Flask MQTT集成
from flask_mqtt import Mqtt
from flask_socketio import SocketIO

app = Flask(__name__)
mqtt = Mqtt(app)
socketio = SocketIO(app)

# 订阅设备数据
@mqtt.on_connect()
def handle_connect(client, userdata, flags, rc):
    mqtt.subscribe('esp32/+/data/json')
    mqtt.subscribe('esp32/+/alert/#')
    mqtt.subscribe('esp32/+/status/#')

# 处理传感器数据
@mqtt.on_message()
def handle_mqtt_message(client, userdata, msg):
    topic = msg.topic.decode()
    payload = msg.payload.decode()
    
    if '/data/json' in topic:
        data = json.loads(payload)
        save_to_database(data)
        socketio.emit('sensor_data', data)
    
    elif '/alert/' in topic:
        send_alert_notification(payload)
        socketio.emit('alert_data', payload)
```

### （5）桌面WEB端设计开发

#### 界面设计
- **实时监控面板**：显示当前传感器数据和报警状态
- **历史数据查询**：图表展示历史趋势
- **设备管理界面**：设备状态监控和配置
- **报警记录管理**：报警历史和统计分析

#### 技术实现
- **前端技术**：HTML5 + CSS3 + JavaScript
- **图表库**：Chart.js
- **UI框架**：Bootstrap
- **实时通信**：Ajax轮询

#### 核心功能
```javascript
// 实时数据获取
function fetchSensorData() {
    fetch('/api/data/recent?limit=20')
        .then(response => response.json())
        .then(data => updateDisplay(data));
}

// 定时刷新
setInterval(fetchSensorData, 1500);
```

### （6）移动端适配设计

#### 响应式设计
- **移动优先**：采用Bootstrap响应式布局
- **触摸优化**：按钮和交互元素适配触摸操作
- **屏幕适配**：支持不同尺寸移动设备

#### 功能简化
- 简化界面布局
- 突出核心功能
- 优化操作流程

#### 通知推送
- **浏览器通知**：Web Notification API
- **报警提醒**：实时推送报警信息
- **状态更新**：设备状态变化通知

---

## 系统特点

### 🔥 **检测精准**
- 多传感器融合检测
- 动态阈值自适应
- 防误报算法优化

### 📡 **通信可靠**
- HTTP协议稳定传输
- 断网重连机制
- 数据缓存保护

### 🖥️ **界面友好**
- 响应式Web界面
- 实时数据可视化
- 移动端完美适配

### 🔧 **部署简单**
- 硬件模块化设计
- 软件配置简单
- 维护成本低廉

---

*本架构设计专为宿舍场景优化，具备高可靠性、易部署、低成本等特点。*