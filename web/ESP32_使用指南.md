# ESP32 硬件使用指南

## 🎯 准备工作

### 1. 硬件连接
确保以下传感器正确连接到ESP32：
- **DHT22温湿度传感器**: GPIO32
- **火焰传感器**: GPIO34
- **烟雾传感器(MQ-2)**: GPIO35
- **光照传感器**: GPIO33
- **声音传感器**: GPIO25
- **舵机**: GPIO26
- **风扇**: GPIO19
- **蜂鸣器**: GPIO27
- **OLED显示屏**: GPIO21(SDA), GPIO22(SCL)

### 2. 软件准备
- **Thonny IDE**: 用于编写和上传代码到ESP32
- **MicroPython固件**: 确保ESP32已刷入MicroPython
- **驱动程序**: 确保USB转串口驱动已安装

## 📋 代码选择

### 完整版本 - `esp32_working.py`
- ✅ 包含所有传感器功能
- ✅ 完整的火灾报警逻辑
- ✅ OLED显示支持
- ✅ 舵机、风扇、蜂鸣器控制
- 🔄 代码复杂，适合完整测试

### 简化测试版本 - `esp32_mqtt_test.py`
- ✅ 专注于MQTT连接测试
- ✅ 使用模拟数据
- ✅ 代码简单，容易调试
- 🔄 适合快速验证连接

## 🔧 使用步骤

### 步骤1: 启动MQTT服务器
```powershell
# 在电脑上启动Mosquitto
cd E:\mos\mosquitto
.\start_mosquitto.ps1
```

### 步骤2: 启动监控
```powershell
# 新开PowerShell窗口，监控ESP32数据
cd E:\mos\mosquitto
mosquitto_sub.exe -h 127.0.0.1 -t "esp32/#" -v
```

### 步骤3: 上传代码到ESP32
1. **连接ESP32**到电脑
2. **打开Thonny IDE**
3. **选择正确的串口** (Tools -> Options -> Interpreter)
4. **打开代码文件** (`esp32_mqtt_test.py` 或 `esp32_working.py`)
5. **点击运行按钮** 或按F5

### 步骤4: 验证连接
观察监控窗口是否有数据输出。

## 📊 预期输出

### 简化测试版本输出
```
ESP32 MQTT连接测试
==================
设备ID: ESP32-TEST-1634567890
正在连接WiFi...
连接到: syh2031
........
✅ WiFi连接成功!
IP地址: 192.168.24.100
尝试连接 Network Mosquitto...
✅ MQTT连接成功!
✅ 开始发送测试数据...
按 Ctrl+C 停止
[1] ✅ 数据已发送
    温度: 25.3°C
    湿度: 62.1%
    火焰: 1542
    烟雾: 567
```

### 监控窗口输出
```
esp32/fire_alarm/data {"device_id":"ESP32-TEST-1634567890","timestamp":1634567890,"data":{"temperature":25.3,"humidity":62.1,"flame":1542,"smoke":567},"status":{"system_status":"normal","status_reason":"Test running"},"location":"Test Location","test_count":1}
```

## 🐛 故障排除

### 1. WiFi连接失败
- **检查SSID和密码**: 确认`WIFI_SSID`和`WIFI_PASSWORD`正确
- **检查信号强度**: 确保ESP32在WiFi信号范围内
- **重启ESP32**: 断电重启ESP32

### 2. MQTT连接失败
- **检查服务器地址**: 确认`192.168.24.23`是正确的IP
- **检查防火墙**: 确保Windows防火墙允许1883端口
- **检查Mosquitto**: 确认Mosquitto正在运行

### 3. 代码无法运行
- **MicroPython版本**: 确保使用兼容的MicroPython固件
- **语法错误**: 检查代码是否有语法错误
- **内存不足**: ESP32内存不足时尝试简化代码

### 4. 传感器读取失败
- **接线检查**: 确认传感器接线正确
- **电源检查**: 确认传感器供电正常
- **GPIO冲突**: 确认GPIO引脚没有冲突

## 📝 代码修改

### 修改WiFi配置
```python
# 在代码中找到以下部分
WIFI_SSID = "你的WiFi名称"
WIFI_PASSWORD = "你的WiFi密码"
```

### 修改MQTT服务器
```python
# 如果需要使用其他MQTT服务器
MQTT_SERVERS = [
    {"server": "新的服务器地址", "port": 1883, "name": "服务器名称"},
]
```

### 修改发送频率
```python
# 在main循环中修改sleep时间
time.sleep(10)  # 改为想要的秒数
```

## 🎯 下一步

### 1. 测试成功后
- 尝试完整版本 `esp32_working.py`
- 连接真实传感器
- 测试报警功能

### 2. 进阶功能
- 集成Web界面
- 添加数据存储
- 实现远程控制

## 📞 技术支持

如果遇到问题：
1. 检查串口输出是否有错误信息
2. 确认所有硬件连接正确
3. 验证网络连接正常
4. 查看代码中的调试信息

---

## 🎉 成功标准

当看到以下输出时，表示测试成功：
- ✅ WiFi连接成功
- ✅ MQTT连接成功
- ✅ 数据发送成功
- ✅ 监控窗口收到数据

祝测试顺利！🚀