# ESP32宿舍火灾报警系统 - 烧录指南

## 📋 烧录前准备

### 1. 硬件连接确认
请确保所有硬件已按照以下方式连接：

| 传感器/执行器 | ESP32引脚 | 说明 |
|-------------|----------|------|
| DHT22温湿度 | GPIO32 | 数据引脚 |
| 火焰传感器 | GPIO34 | AO模拟输出 |
| MQ-2烟雾 | GPIO35 | AO模拟输出 |
| 光照传感器 | GPIO33 | AO模拟输出 |
| 声音传感器 | GPIO25 | AO模拟输出 |
| 舵机 | GPIO26 | PWM控制 |
| 风扇 | GPIO23 | PWM控制 |
| 蜂鸣器 | GPIO27 | 数字输出 |
| OLED SDA | GPIO21 | I2C数据线 |
| OLED SCL | GPIO22 | I2C时钟线 |
| VCC | 3.3V | 电源正极 |
| GND | GND | 电源地 |

### 2. 必需文件准备
需要烧录到ESP32的文件：
- `main.py` - 主程序入口
- `esp32_dht22_sensor.py` - 主要功能程序
- `ssd1306.py` - OLED驱动库
- `umqtt/simple.py` - MQTT客户端库
- `dht.py` - DHT22传感器库

## 🔧 烧录步骤

### 步骤1：修改WiFi配置
首先修改 `esp32_dht22_sensor.py` 中的WiFi配置：

```python
# 第80-81行，修改为你的WiFi信息
WIFI_SSID = "你的WiFi名称"    # 例如： "TP-LINK_5G"
WIFI_PASSWORD = "你的WiFi密码"  # 例如： "12345678"
```

### 步骤2：连接ESP32到电脑
1. 用USB线连接ESP32到电脑
2. 打开Thonny IDE
3. 选择正确的解释器（MicroPython ESP32）

### 步骤3：上传文件到ESP32

#### 方法A：使用Thonny IDE（推荐）
1. **打开Thonny IDE**
2. **选择解释器**：运行 -> 选择解释器 -> MicroPython (ESP32)
3. **上传文件**：
   - 右键点击文件 -> 上传到 / 设备
   - 依次上传以下文件：
     - `ssd1306.py` (如果固件没有自带)
     - `dht.py` (如果固件没有自带)
     - `umqtt` 文件夹 (包含 simple.py)
     - `esp32_dht22_sensor.py`
     - `main.py`

#### 方法B：使用rshell（命令行）
```bash
# 安装rshell
pip install rshell

# 连接ESP32
rshell --port COM5

# 上传文件
cp esp32_dht22_sensor.py /pyboard/
cp main.py /pyboard/
cp ssd1306.py /pyboard/
cp dht.py /pyboard/
cp -r umqtt /pyboard/
```

### 步骤4：重启ESP32
1. **软重启**：在Thonny中按Ctrl+D
2. **硬重启**：按ESP32上的RST按钮

### 步骤5：查看启动日志
在Thonny的Shell窗口应该看到类似输出：
```
ESP32宿舍火灾报警系统启动
正在连接WiFi...
SSID: 你的WiFi名称
✅ WiFi连接成功
IP地址: 192.168.1.100
正在连接Cpolar MQTT: 22.tcp.cpolar.top:14871
✅ Cpolar MQTT连接成功
✅ 设备上线状态已发布
开始监测传感器数据...
```

## 🔍 故障排除

### 问题1：无法连接ESP32
**现象**：Thonny无法识别设备
**解决**：
- 检查USB连接
- 尝试更换USB线
- 检查设备管理器中的COM端口
- 按住BOOT按钮连接，然后松开

### 问题2：WiFi连接失败
**现象**：显示WiFi密码错误或找不到网络
**解决**：
- 确认WiFi名称和密码正确
- 确认WiFi信号强度良好
- 尝试连接手机热点测试

### 问题3：MQTT连接失败
**现象**：无法连接Cpolar MQTT
**解决**：
- 确认ESP32能访问互联网
- 检查Cpolar隧道是否正常运行
- 尝试用手机热点测试

### 问题4：传感器读取失败
**现象**：显示传感器数据无效
**解决**：
- 检查传感器接线
- 确认传感器供电正常
- 检查引脚配置是否正确

## 📱 测试验证

### 1. 测试Web监控
打开浏览器访问：https://75eff755.r40.cpolar.top
应该能看到：
- 实时传感器数据
- 设备状态显示
- 报警历史记录

### 2. 测试传感器数据
在Thonny Shell中应该看到：
```
温度: 25.5°C, 湿度: 60.0%
火焰: 1500, 烟雾: 800
光照: 800, 声音: 1200
```

### 3. 测试报警功能
- 用打火机靠近火焰传感器
- 用烟雾测试MQ-2传感器
- 观察OLED显示和蜂鸣器是否正常

## 🚀 快速启动清单

- [ ] 硬件连接完成
- [ ] 修改WiFi配置
- [ ] 准备所需库文件
- [ ] 上传所有文件到ESP32
- [ ] 重启设备
- [ ] 查看启动日志
- [ ] 测试Web监控界面
- [ ] 测试传感器功能

## 💡 提示

1. **首次烧录**：如果ESP32是全新的，可能需要先烧录MicroPython固件
2. **库文件**：确保所有必需的库文件都已上传
3. **引脚冲突**：检查是否有其他程序占用了相同引脚
4. **电源供应**：确保ESP32供电稳定，避免电压不足

---

**烧录完成！您的ESP32宿舍火灾报警系统应该正常运行了！** 🎉