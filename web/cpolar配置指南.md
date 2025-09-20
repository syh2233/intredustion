# ESP32宿舍火灾报警系统 - Cpolar内网穿透配置
# =================================================

## 🎉 Cpolar配置成功！

你的私有云平台已经通过cpolar成功映射到公网，现在可以从任何地方访问！

## 🌐 公网访问地址

### 1. Web监控界面
```
https://3b89539d.r40.cpolar.top
```
- ✅ 支持HTTPS加密访问
- ✅ 实时监控界面
- ✅ 历史数据图表
- ✅ 设备管理功能

### 2. MQTT Broker (ESP32设备连接)
```
服务器地址: 22.tcp.cpolar.top
端口: 10067
协议: TCP
```

### 3. MQTT WebSocket (Web实时通信)
```
服务器地址: 22.tcp.cpolar.top
端口: 13519
协议: TCP
```

## 📱 ESP32设备配置

### MicroPython MQTT配置示例
```python
import machine
import network
import ujson
import utime
from umqtt.simple import MQTTClient

# Cpolar MQTT配置
MQTT_BROKER = "22.tcp.cpolar.top"  # Cpolar域名
MQTT_PORT = 10067                 # Cpolar映射端口
MQTT_USER = ""                    # 用户名(如配置了认证)
MQTT_PASS = ""                    # 密码

# 设备信息
DEVICE_ID = "ESP32-DORM-001"
TOPIC_DATA = f"esp32/{DEVICE_ID}/data/json"
TOPIC_ALERT = f"esp32/{DEVICE_ID}/alert/fire"

def connect_mqtt():
    """连接MQTT服务器"""
    try:
        client = MQTTClient(DEVICE_ID, MQTT_BROKER, MQTT_PORT, MQTT_USER, MQTT_PASS)
        client.connect()
        print(f"MQTT连接成功: {MQTT_BROKER}:{MQTT_PORT}")
        return client
    except Exception as e:
        print(f"MQTT连接失败: {e}")
        return None

def send_sensor_data(client, flame, smoke, temperature, humidity, alert=False):
    """发送传感器数据"""
    try:
        data = {
            "device_id": DEVICE_ID,
            "flame": flame,
            "smoke": smoke,
            "temperature": temperature,
            "humidity": humidity,
            "alert": alert,
            "timestamp": utime.time()
        }
        
        client.publish(TOPIC_DATA, ujson.dumps(data))
        print(f"数据发送成功: {data}")
    except Exception as e:
        print(f"数据发送失败: {e}")

# 使用示例
client = connect_mqtt()
if client:
    # 模拟发送数据
    send_sensor_data(client, 1234, 567, 25.5, 60.0, False)
```

## 🧪 测试公网访问

### 1. 测试Web界面
打开浏览器访问: https://3b89539d.r40.cpolar.top

应该看到:
- ✅ ESP32宿舍火灾报警系统监控界面
- ✅ 实时数据图表
- ✅ 设备状态显示

### 2. 测试MQTT连接
```python
# Python MQTT测试
import paho.mqtt.client as mqtt

def on_connect(client, userdata, flags, rc):
    print(f"连接结果: {rc}")
    client.subscribe("esp32/+/data/json")

def on_message(client, userdata, msg):
    print(f"收到消息: {msg.topic} - {msg.payload.decode()}")

client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message

client.connect("22.tcp.cpolar.top", 10067, 60)
client.loop_start()
```

### 3. 测试API接口
```bash
# 测试数据获取
curl https://3b89539d.r40.cpolar.top/api/data/recent?limit=5

# 测试设备列表
curl https://3b89539d.r40.cpolar.top/api/devices

# 测试报警记录
curl https://3b89539d.r40.cpolar.top/api/alerts
```

## ⚠️ 注意事项

### 1. Cpolar免费版限制
- **带宽限制**: 免费版有流量限制
- **稳定性**: 隧道可能不稳定，需要定期重连
- **域名变化**: 每次重启可能变化，需要更新配置

### 2. MQTT连接优化
```python
# 添加重连机制
def connect_with_retry(max_retries=3):
    for i in range(max_retries):
        client = connect_mqtt()
        if client:
            return client
        print(f"重连中... ({i+1}/{max_retries})")
        utime.sleep(5)
    return None
```

### 3. Web界面配置
如果需要更新WebSocket连接地址，修改 `templates/index.html` 中的Socket.IO配置：

```javascript
// 更新为cpolar域名
const socket = io('https://3b89539d.r40.cpolar.top', {
    secure: true,
    transports: ['websocket']
});
```

## 🔧 生产环境建议

### 1. 升级Cpolar套餐
- 购买付费套餐获得稳定隧道
- 获得固定二级域名
- 提升带宽和稳定性

### 2. 替代方案
- **DDNS + 端口映射**: 如果有公网IP
- **云服务器**: 阿里云/腾讯云等
- **Ngrok**: 类似的内网穿透工具

### 3. 安全增强
- 启用MQTT用户认证
- 配置HTTPS证书
- 设置访问密码
- 定期更新cpolar客户端

## 🚀 现在你可以做什么？

1. **从任何地方访问**: https://3b89539d.r40.cpolar.top
2. **部署ESP32设备**: 使用MQTT配置连接到公网
3. **实时监控**: 查看传感器数据和报警信息
4. **远程管理**: 设备状态监控和配置

## 📞 故障排除

### 常见问题
1. **Web界面无法访问**
   - 检查cpolar客户端是否运行
   - 确认本地Flask服务正常

2. **MQTT连接失败**
   - 验证端口号和地址
   - 检查网络连接
   - 确认cpolar隧道状态

3. **数据传输不稳定**
   - 这是免费版正常现象
   - 考虑升级付费版或使用更稳定方案

---

**恭喜！你的ESP32宿舍火灾报警系统现在已经可以通过公网访问了！** 🎉