# ESP32 WiFi和MQTT连接问题解决方案

## 问题分析

根据错误信息，发现两个主要问题：

1. **MQTT连接失败**：错误代码`-202`表示网络连接失败
2. **DHT22传感器错误**：`'DHT22' object has no attribute 'temperature'`

## 解决方案

### 1. WiFi连接问题

在原始代码中缺少WiFi连接步骤。ESP32需要先连接到WiFi网络，然后才能连接到MQTT服务器。

**修复内容：**
- 添加了`connect_wifi()`函数
- 在MQTT连接前先检查WiFi状态
- 添加了WiFi连接状态显示

### 2. DHT22传感器问题

DHT22传感器在使用前需要调用`measure()`方法来获取数据。

**修复内容：**
- 在初始化时立即测试DHT22传感器
- 添加了错误处理机制
- 如果DHT22失败，使用模拟数据

## 使用方法

### 1. 配置WiFi

修改代码中的WiFi配置：

```python
# WiFi configuration
WIFI_SSID = "Your_WiFi_SSID"      # 替换为你的WiFi名称
WIFI_PASSWORD = "Your_WiFi_Password"  # 替换为你的WiFi密码
```

### 2. 上传到ESP32

使用Thonny IDE将修复后的代码上传到ESP32：

```python
# 在Thonny中打开 esp32_working.py
# 修改WiFi配置
# 点击运行按钮上传到ESP32
```

### 3. 运行系统

上传后，系统会：

1. 自动连接到WiFi网络
2. 测试MQTT服务器连接
3. 初始化所有传感器
4. 开始监测火灾风险

### 4. 监控MQTT消息

如果MQTT连接成功，可以使用以下命令监控数据：

```bash
# 监控所有传感器数据
mosquitto_sub -h test.mosquitto.org -t "esp32/fire_alarm/data" -v

# 监控报警消息
mosquitto_sub -h test.mosquitto.org -t "esp32/fire_alarm/alert" -v
```

## 故障排除

### WiFi连接问题

如果WiFi连接失败，请检查：

1. WiFi名称和密码是否正确
2. ESP32是否在WiFi信号范围内
3. 路由器是否正常工作

### MQTT连接问题

如果MQTT连接失败但WiFi正常，可能是：

1. 防火墙阻止了MQTT端口（1883）
2. 公网MQTT服务器暂时不可用
3. 网络DNS解析问题

### DHT22传感器问题

如果DHT22传感器工作不正常：

1. 检查传感器连接是否正确
2. 确认GPIO32引脚连接
3. 检查传感器供电（3.3V）

## 系统状态说明

### 系统会显示以下状态：

- **WiFi Status**: 显示WiFi连接状态
- **MQTT Status**: 显示MQTT连接状态
- **Sensor Status**: 显示传感器工作状态
- **System Status**: 显示系统整体状态（正常/警告/报警）

### 工作模式：

1. **在线模式**：WiFi和MQTT都正常，数据实时上传
2. **本地模式**：WiFi或MQTT失败，系统本地运行但不上传数据

## 测试建议

1. **先测试WiFi连接**：确认ESP32能连接到WiFi
2. **测试MQTT连接**：确认能连接到公共MQTT服务器
3. **测试传感器**：确认所有传感器工作正常
4. **测试Web界面**：确认Flask服务器能接收数据

## 注意事项

1. 首次运行时，MQ-2烟雾传感器需要24-48小时预热
2. 确保所有传感器连接正确，电压在ESP32接受范围内
3. 系统会自动处理传感器故障，使用模拟数据继续运行
4. 在实际部署前，建议进行完整的系统测试