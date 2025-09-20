#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ESP32宿舍火灾报警系统 - 完整传感器模块 (本地Mosquitto版)
==============================================================

功能：
- DHT22温湿度传感器读取
- 火焰传感器检测
- MQ-2烟雾传感器检测
- 光照传感器检测
- 声音传感器检测
- OLED显示控制
- 舵机控制
- 蜂鸣器报警
- 风扇控制
- 本地MQTT通信

硬件连接：
- DHT22数据引脚 -> GPIO32
- 火焰传感器AO -> GPIO34
- MQ-2烟雾传感器AO -> GPIO35
- 光照传感器AO -> GPIO33
- 声音传感器AO -> GPIO25
- 舵机控制 -> GPIO26
- 风扇控制 -> GPIO19（避免与OLED冲突）
- 蜂鸣器 -> GPIO27
- OLED SDA -> GPIO23, SCL -> GPIO18, VCC -> 5V, GND -> GND

网络配置：
- WiFi: ESP32连接到本地网络
- MQTT: 使用本地Mosquitto服务器 (192.168.24.32:1883)
- Web监控: http://localhost:5000 或 http://192.168.24.32:5000

使用前配置：
1. 已配置为你的WiFi网络 (syh2031)
2. 已配置为本地MQTT服务器 (192.168.24.32:1883)
3. 确保电脑的Mosquitto服务器正在运行
4. 确保ESP32能正常连接到WiFi网络
"""

import machine
import time
import dht
import json
import network
import socket
import sys
import ssd1306
from machine import Pin, ADC, PWM

# 传感器引脚配置
DHT_PIN = 32          # DHT22温湿度传感器
FLAME_PIN = 34        # 火焰传感器
SMOKE_PIN = 35        # MQ-2烟雾传感器
LIGHT_PIN = 33        # 光照传感器
SOUND_PIN = 25        # 声音传感器
SERVO_PIN = 26        # 舵机控制
FAN_PIN = 19          # 风扇控制（改为GPIO19，避免与OLED冲突）
BUZZER_PIN = 27       # 蜂鸣器
OLED_SDA_PIN = 23     # OLED SDA（与参考方案一致）
OLED_SCL_PIN = 18     # OLED SCL（与参考方案一致）

# 初始化传感器（添加ADC衰减设置）
dht_sensor = dht.DHT22(machine.Pin(DHT_PIN))
flame_adc = ADC(Pin(FLAME_PIN))
flame_adc.atten(ADC.ATTN_11DB)  # 0-3.3V范围
smoke_adc = ADC(Pin(SMOKE_PIN))
smoke_adc.atten(ADC.ATTN_11DB)  # 0-3.3V范围
light_adc = ADC(Pin(LIGHT_PIN))
light_adc.atten(ADC.ATTN_11DB)  # 0-3.3V范围
sound_adc = ADC(Pin(SOUND_PIN))
sound_adc.atten(ADC.ATTN_11DB)  # 0-3.3V范围

class SimpleMQTTClient:
    """简化的MQTT客户端"""
    def __init__(self, client_id, server, port):
        self.client_id = client_id
        self.server = server
        self.port = port
        self.sock = None
        self.connected = False

    def connect(self):
        """连接到MQTT服务器"""
        try:
            print(f"正在连接MQTT: {self.server}:{self.port}")

            # 创建socket连接
            self.sock = socket.socket()
            self.sock.settimeout(10)
            addr = socket.getaddrinfo(self.server, self.port)[0][-1]
            self.sock.connect(addr)
            print("TCP连接成功")

            # 构建MQTT CONNECT消息
            protocol_name = b"MQTT"
            protocol_level = 4  # MQTT 3.1.1
            flags = 0x02  # Clean session
            keep_alive = 60

            # 可变头部
            var_header = bytearray()
            # 协议名长度字段 (MSB + LSB)
            var_header.append(0)  # MSB of protocol name length
            var_header.append(len(protocol_name))  # LSB of protocol name length
            var_header.extend(protocol_name)
            var_header.append(protocol_level)
            var_header.append(flags)
            var_header.append(keep_alive >> 8)
            var_header.append(keep_alive & 0xFF)

            # 负载
            payload = bytearray()
            client_id_bytes = self.client_id.encode()
            payload.append(len(client_id_bytes) >> 8)
            payload.append(len(client_id_bytes) & 0xFF)
            payload.extend(client_id_bytes)

            # 剩余长度
            remaining_length = len(var_header) + len(payload)

            # 完整消息
            connect_msg = bytearray()
            connect_msg.append(0x10)  # CONNECT
            connect_msg.append(remaining_length)
            connect_msg.extend(var_header)
            connect_msg.extend(payload)

            # 发送连接消息
            self.sock.send(connect_msg)

            # 等待CONNACK
            response = self.sock.recv(1024)

            if len(response) >= 4 and response[0] == 0x20 and response[3] == 0x00:
                self.connected = True
                print("✅ MQTT连接成功!")
                return True
            else:
                print(f"❌ MQTT连接失败: {response}")
                return False

        except Exception as e:
            print(f"❌ MQTT连接异常: {e}")
            if self.sock:
                self.sock.close()
            self.connected = False
            return False

    def publish(self, topic, message):
        """发布消息"""
        if not self.connected:
            return False

        try:
            topic_bytes = topic.encode()
            message_bytes = message.encode()

            # Calculate remaining length
            topic_length = len(topic_bytes)
            message_length = len(message_bytes)
            remaining_length = 2 + topic_length + message_length

            # Check if message is too long
            if remaining_length > 127:
                print(f"Warning: Message too long ({remaining_length} bytes), truncating...")
                # Truncate message
                max_message_length = 127 - 2 - topic_length
                message_bytes = message_bytes[:max_message_length]
                message_length = len(message_bytes)
                remaining_length = 2 + topic_length + message_length

            # Build PUBLISH message
            publish_msg = bytearray()
            publish_msg.append(0x30)  # PUBLISH QoS 0

            # Add remaining length
            publish_msg.append(remaining_length)

            # Add topic length
            publish_msg.append(topic_length >> 8)
            publish_msg.append(topic_length & 0xFF)

            # Add topic name
            publish_msg.extend(topic_bytes)

            # Add message content
            publish_msg.extend(message_bytes)

            self.sock.send(publish_msg)
            return True

        except Exception as e:
            print(f"Publish failed: {e}")
            return False

    def disconnect(self):
        """断开连接"""
        if self.sock and self.connected:
            try:
                self.sock.send(b"\xE0\x00")  # DISCONNECT
                self.sock.close()
            except:
                pass
            finally:
                self.connected = False
fan_pwm = PWM(Pin(FAN_PIN), freq=1000, duty=0)
buzzer_pin = Pin(BUZZER_PIN, Pin.OUT)

# 初始化舵机（需要50Hz频率）
servo_pwm = PWM(Pin(SERVO_PIN), freq=50, duty=0)

# 初始化OLED显示（使用参考方案：SDA->GPIO23, SCL->GPIO18）
try:
    # 使用与参考实验相同的SoftI2C配置
    i2c = machine.SoftI2C(sda=machine.Pin(OLED_SDA_PIN), scl=machine.Pin(OLED_SCL_PIN))
    print(f"✅ I2C初始化成功 (SDA:GPIO{OLED_SDA_PIN}, SCL:GPIO{OLED_SCL_PIN})")
except Exception as e:
    print(f"❌ I2C初始化失败: {e}")
    i2c = None

# 初始化OLED
try:
    if i2c is not None:
        # 扫描I2C设备
        devices = i2c.scan()
        print(f"I2C设备扫描: {devices}")

        if 0x3C in devices:
            oled = ssd1306.SSD1306_I2C(128, 64, i2c)
            print("✅ OLED初始化成功 (地址:0x3C)")
        else:
            print("❌ 未检测到OLED设备 (0x3C)")
            oled = None
    else:
        print("❌ I2C未初始化，跳过OLED")
        oled = None
except Exception as e:
    print(f"❌ OLED初始化失败: {e}")
    oled = None

# WiFi配置 (使用你的WiFi网络)
WIFI_SSID = "syh2031"
WIFI_PASSWORD = "12345678"

# 本地MQTT配置 (使用你电脑的Mosquitto服务器)
MQTT_SERVER = "192.168.24.32"  # 电脑的真实IP
MQTT_PORT = 1883                 # 本地Mosquitto端口
MQTT_USER = ""                    # 用户名(匿名连接)
MQTT_PASSWORD = ""                # 密码(匿名连接)
DEVICE_ID = "ESP32-DHT22-TEST"  # 设备ID

# MQTT主题
MQTT_TOPIC_DATA = f"esp32/{DEVICE_ID}/data/json"
MQTT_TOPIC_ALERT = f"esp32/{DEVICE_ID}/alert/fire"
MQTT_TOPIC_STATUS = f"esp32/{DEVICE_ID}/status/online"

# 火灾报警阈值
FLAME_THRESHOLD = 1200    # 火焰传感器阈值（0-4095，数值越小越可能有火）
SMOKE_THRESHOLD = 1200   # 烟雾传感器阈值（0-4095，数值越大烟雾越浓）
TEMP_THRESHOLD = 40      # 温度阈值（°C）
HUMIDITY_THRESHOLD = 80  # 湿度阈值（%）

# 警告阈值（低于报警阈值）
FLAME_WARN_THRESHOLD = 1100
SMOKE_WARN_THRESHOLD = 800
TEMP_WARN_THRESHOLD = 35
HUMIDITY_WARN_THRESHOLD = 70

# 环境传感器阈值
LIGHT_DARK_THRESHOLD = 500    # 光照暗阈值（0-4095，数值越小越暗）
SOUND_LOUD_THRESHOLD = 2000  # 声音响阈值（0-4095，数值越大声音越响）

# 数据读取间隔（秒）
READ_INTERVAL = 3

# 系统状态
SYSTEM_STATUS_NORMAL = "normal"
SYSTEM_STATUS_WARNING = "warning"
SYSTEM_STATUS_ALARM = "alarm"

current_status = SYSTEM_STATUS_NORMAL
status_cooldown = 0

def connect_wifi():
    """连接WiFi网络"""
    try:
        # 关闭WiFi以重新初始化
        ap_if = network.WLAN(network.AP_IF)
        ap_if.active(False)

        # 等待一下
        time.sleep(1)

        # 启动STA模式
        sta_if = network.WLAN(network.STA_IF)
        sta_if.active(True)

        print("正在连接WiFi...")
        print(f"SSID: {WIFI_SSID}")

        # 连接WiFi
        sta_if.connect(WIFI_SSID, WIFI_PASSWORD)

        # 等待连接
        for i in range(30):  # 最多等待30秒
            status = sta_if.status()
            if status == network.STAT_GOT_IP:
                print("✅ WiFi连接成功")
                print(f"IP地址: {sta_if.ifconfig()[0]}")
                return True
            elif status == network.STAT_CONNECTING:
                print(f"连接中... ({i+1}/30)")
            elif status == network.STAT_WRONG_PASSWORD:
                print("❌ WiFi密码错误")
                return False
            elif status == network.STAT_NO_AP_FOUND:
                print("❌ 找不到WiFi网络")
                return False
            elif status == network.STAT_CONNECT_FAIL:
                print("❌ WiFi连接失败")
                return False
            else:
                print(f"连接状态: {status}")

            time.sleep(1)

        print("❌ WiFi连接超时")
        return False

    except Exception as e:
        print(f"❌ WiFi连接异常: {e}")
        return False

def connect_mqtt():
    """连接本地MQTT服务器"""
    try:
        client = SimpleMQTTClient(DEVICE_ID, MQTT_SERVER, MQTT_PORT)
        if client.connect():
            # 发布设备上线状态
            status_data = {
                "device_id": DEVICE_ID,
                "status": "online",
                "connection_type": "local_mosquitto",
                "timestamp": time.time()
            }
            client.publish(MQTT_TOPIC_STATUS, json.dumps(status_data))
            print(f"✅ 设备上线状态已发布")
            return client
        else:
            return None
    except Exception as e:
        print(f"❌ 本地MQTT连接失败: {e}")
        return None

def connect_mqtt_with_retry(max_retries=3):
    """带重连机制的MQTT连接"""
    for attempt in range(max_retries):
        print(f"MQTT连接尝试 {attempt + 1}/{max_retries}")
        client = connect_mqtt()
        if client:
            return client
        print(f"连接失败，5秒后重试...")
        time.sleep(5)

    print("❌ MQTT连接重试次数用尽")
    return None

def read_all_sensors():
    """
    读取所有传感器数据

    Returns:
        dict: 包含所有传感器数据的字典
    """
    try:
        # 读取DHT22温湿度（添加错误处理）
        temperature = None
        humidity = None

        for dht_attempt in range(3):
            try:
                dht_sensor.measure()
                temperature = dht_sensor.temperature()
                humidity = dht_sensor.humidity()
                if temperature is not None and humidity is not None:
                    break
                print(f"DHT22读取尝试 {dht_attempt + 1} 返回None，重试...")
                time.sleep(1)
            except Exception as dht_error:
                print(f"DHT22读取尝试 {dht_attempt + 1} 失败: {dht_error}")
                if dht_attempt < 2:  # 最后一次不等待
                    time.sleep(1)

        if temperature is None or humidity is None:
            print("❌ DHT22传感器多次读取失败，使用模拟数据")
            temperature = 25.0  # 模拟温度
            humidity = 60.0    # 模拟湿度

        # 读取火焰传感器（多次采样取平均值）
        flame_samples = []
        for _ in range(5):
            flame_samples.append(flame_adc.read())
            time.sleep(0.01)
        flame_value = sum(flame_samples) // len(flame_samples)

        # 读取MQ-2烟雾传感器（多次采样取平均值）
        smoke_samples = []
        for _ in range(5):
            smoke_samples.append(smoke_adc.read())
            time.sleep(0.01)
        smoke_value = sum(smoke_samples) // len(smoke_samples)

        # 读取光照传感器（多次采样取平均值）
        light_samples = []
        for _ in range(5):
            light_samples.append(light_adc.read())
            time.sleep(0.01)
        light_value = sum(light_samples) // len(light_samples)

        # 读取声音传感器（多次采样取最大值）
        sound_samples = []
        for _ in range(10):
            sound_samples.append(sound_adc.read())
            time.sleep(0.005)
        sound_value = max(sound_samples)

        # 数据有效性检查
        if temperature is None or humidity is None:
            print("错误：DHT22传感器返回None值")
            return None

        if not (-40 <= temperature <= 80):
            print(f"警告：温度值可能异常: {temperature}°C")

        if not (0 <= humidity <= 100):
            print(f"警告：湿度值可能异常: {humidity}%")

        print(f"温度: {temperature:.1f}°C, 湿度: {humidity:.1f}%")
        print(f"火焰: {flame_value}, 烟雾: {smoke_value}")
        print(f"光照: {light_value}, 声音: {sound_value}")

        return {
            'temperature': temperature,
            'humidity': humidity,
            'flame': flame_value,
            'smoke': smoke_value,
            'light': light_value,
            'sound': sound_value
        }

    except Exception as e:
        print(f"读取传感器失败: {e}")
        return None

def check_system_status(sensor_data):
    """
    检查系统状态（正常→警告→警报三级机制）

    Args:
        sensor_data: 传感器数据字典

    Returns:
        tuple: (status, reason) 状态和原因
    """
    if sensor_data is None:
        return SYSTEM_STATUS_NORMAL, "传感器数据无效"

    temp = sensor_data['temperature']
    humidity = sensor_data['humidity']
    flame = sensor_data['flame']
    smoke = sensor_data['smoke']

    # 警报条件（任一满足即触发警报）
    alarm_reasons = []
    if flame < FLAME_THRESHOLD:
        alarm_reasons.append(f"火焰检测({flame}<{FLAME_THRESHOLD})")
    if smoke > SMOKE_THRESHOLD:
        alarm_reasons.append(f"烟雾检测({smoke}>{SMOKE_THRESHOLD})")
    if temp > TEMP_THRESHOLD:
        alarm_reasons.append(f"高温报警({temp}>{TEMP_THRESHOLD}°C)")
    if humidity > HUMIDITY_THRESHOLD:
        alarm_reasons.append(f"高湿度报警({humidity}>{HUMIDITY_THRESHOLD}%)")

    if len(alarm_reasons) > 0:
        return SYSTEM_STATUS_ALARM, ", ".join(alarm_reasons)

    # 警告条件（任一满足即触发警告）
    warning_reasons = []
    if flame < FLAME_WARN_THRESHOLD:
        warning_reasons.append(f"火焰偏低({flame}<{FLAME_WARN_THRESHOLD})")
    if smoke > SMOKE_WARN_THRESHOLD:
        warning_reasons.append(f"烟雾偏高({smoke}>{SMOKE_WARN_THRESHOLD})")
    if temp > TEMP_WARN_THRESHOLD:
        warning_reasons.append(f"温度偏高({temp}>{TEMP_WARN_THRESHOLD}°C)")
    if humidity > HUMIDITY_WARN_THRESHOLD:
        warning_reasons.append(f"湿度偏高({humidity}>{HUMIDITY_WARN_THRESHOLD}%)")

    if len(warning_reasons) > 0:
        return SYSTEM_STATUS_WARNING, ", ".join(warning_reasons)

    return SYSTEM_STATUS_NORMAL, "环境正常"

def control_servo(angle, system_status):
    """
    控制舵机角度

    Args:
        angle: 舵机角度 (0-180度)
        system_status: 系统状态
    """
    try:
        # 将角度转换为PWM占空比 (0.5ms-2.5ms 对应 0-180度)
        duty = int(26 + (angle / 180) * 103)  # 26-129 对应 0-180度
        servo_pwm.duty(duty)
        print(f"舵机角度: {angle}°, PWM: {duty}")
    except Exception as e:
        print(f"舵机控制失败: {e}")

def control_buzzer(system_status, sound_level):
    """
    控制蜂鸣器

    Args:
        system_status: 系统状态
        sound_level: 声音传感器数值
    """
    try:
        if system_status == SYSTEM_STATUS_ALARM:
            # 警报状态：快速蜂鸣
            buzzer_pin.value(1)
            time.sleep(0.1)
            buzzer_pin.value(0)
            time.sleep(0.1)
        elif system_status == SYSTEM_STATUS_WARNING or sound_level > SOUND_LOUD_THRESHOLD:
            # 警告状态或声音过大：慢速蜂鸣
            buzzer_pin.value(1)
            time.sleep(0.3)
            buzzer_pin.value(0)
        else:
            # 正常状态：关闭蜂鸣器
            buzzer_pin.value(0)
    except Exception as e:
        print(f"蜂鸣器控制失败: {e}")

def control_fan(temperature, system_status):
    """
    根据系统状态控制风扇转速

    Args:
        temperature: 当前温度
        system_status: 系统状态
    """
    try:
        if system_status == SYSTEM_STATUS_ALARM:
            # 警报状态：风扇全速运转
            fan_pwm.duty(1023)  # 100% 占空比
            print("风扇全速运转（警报模式）")
        elif system_status == SYSTEM_STATUS_WARNING or temperature > 30:
            # 警告状态或高温：风扇中等转速
            fan_pwm.duty(512)   # 50% 占空比
            print("风扇中等转速（警告/高温模式）")
        else:
            # 正常状态：关闭风扇
            fan_pwm.duty(0)     # 0% 占空比
            print("风扇关闭（正常模式）")
    except Exception as e:
        print(f"风扇控制失败: {e}")

def update_oled_display(sensor_data, system_status, status_reason):
    """
    更新OLED显示（支持三级状态显示）

    Args:
        sensor_data: 传感器数据
        system_status: 系统状态
        status_reason: 状态原因
    """
    try:
        oled.fill(0)  # 清空显示

        if system_status == SYSTEM_STATUS_ALARM:
            # 警报显示
            oled.text("🔥 火灾警报!", 0, 0, 1)
            oled.text(status_reason[:20], 0, 16, 1)
            oled.text(f"T:{sensor_data['temperature']:.0f}C", 0, 32, 1)
            oled.text(f"烟雾:{sensor_data['smoke']}", 64, 32, 1)
            oled.text(f"火焰:{sensor_data['flame']}", 0, 48, 1)
            oled.text(f"声音:{sensor_data['sound']}", 64, 48, 1)
        elif system_status == SYSTEM_STATUS_WARNING:
            # 警告显示
            oled.text("⚠️ 环境警告", 0, 0, 1)
            oled.text(status_reason[:20], 0, 16, 1)
            oled.text(f"T:{sensor_data['temperature']:.0f}C", 0, 32, 1)
            oled.text(f"H:{sensor_data['humidity']:.0f}%", 64, 32, 1)
            oled.text(f"光照:{sensor_data['light']}", 0, 48, 1)
            oled.text(f"声音:{sensor_data['sound']}", 64, 48, 1)
        else:
            # 正常显示
            oled.text("宿舍监控正常", 0, 0, 1)
            oled.text(f"T:{sensor_data['temperature']:.0f}C", 0, 16, 1)
            oled.text(f"H:{sensor_data['humidity']:.0f}%", 64, 16, 1)
            oled.text(f"光照:{sensor_data['light']}", 0, 32, 1)
            oled.text(f"声音:{sensor_data['sound']}", 64, 32, 1)
            oled.text(f"火焰:{sensor_data['flame']}", 0, 48, 1)
            oled.text(f"烟雾:{sensor_data['smoke']}", 64, 48, 1)

        oled.show()  # 更新显示

    except Exception as e:
        print(f"OLED显示失败: {e}")

def send_sensor_data(mqtt_client, sensor_data, system_status, status_reason):
    """
    通过MQTT发送传感器数据到服务器

    Args:
        mqtt_client: MQTT客户端对象
        sensor_data: 传感器数据字典
        system_status: 系统状态
        status_reason: 状态原因
    """
    try:
        # 构造数据包
        data = {
            "device_id": DEVICE_ID,
            "timestamp": time.time(),
            "data": {
                "temperature": round(sensor_data['temperature'], 1),
                "humidity": round(sensor_data['humidity'], 1),
                "flame": sensor_data['flame'],
                "smoke": sensor_data['smoke'],
                "light": sensor_data['light'],
                "sound": sensor_data['sound']
            },
            "status": {
                "system_status": system_status,
                "status_reason": status_reason,
                "wifi_rssi": get_wifi_rssi()
            },
            "environment": {
                "is_dark": sensor_data['light'] < LIGHT_DARK_THRESHOLD,
                "is_loud": sensor_data['sound'] > SOUND_LOUD_THRESHOLD
            }
        }

        # 转换为JSON字符串
        payload = json.dumps(data)

        # 发送到MQTT主题
        mqtt_client.publish(MQTT_TOPIC_DATA, payload)

        print(f"数据已发送到 {MQTT_TOPIC_DATA}")
        print(f"数据内容: {payload}")

    except Exception as e:
        print(f"发送MQTT数据失败: {e}")

def send_alert_data(mqtt_client, alert_type, severity, sensor_data):
    """
    发送报警数据到MQTT服务器

    Args:
        mqtt_client: MQTT客户端对象
        alert_type: 报警类型
        severity: 严重程度
        sensor_data: 传感器数据
    """
    try:
        alert_data = {
            "device_id": DEVICE_ID,
            "alert_type": alert_type,
            "severity": severity,
            "timestamp": time.time(),
            "sensor_values": {
                "flame": sensor_data['flame'],
                "smoke": sensor_data['smoke'],
                "temperature": sensor_data['temperature'],
                "humidity": sensor_data['humidity'],
                "light": sensor_data['light'],
                "sound": sensor_data['sound']
            },
            "environment": {
                "is_dark": sensor_data['light'] < LIGHT_DARK_THRESHOLD,
                "is_loud": sensor_data['sound'] > SOUND_LOUD_THRESHOLD
            },
            "location": "宿舍A栋301"
        }

        payload = json.dumps(alert_data)
        mqtt_client.publish(MQTT_TOPIC_ALERT, payload)

        print(f"报警数据已发送到 {MQTT_TOPIC_ALERT}")
        print(f"报警内容: {payload}")

    except Exception as e:
        print(f"发送报警数据失败: {e}")

def get_wifi_rssi():
    """获取WiFi信号强度"""
    try:
        sta_if = network.WLAN(network.STA_IF)
        if sta_if.isconnected():
            return sta_if.status('rssi')
        return None
    except:
        return None

def main():
    """主函数"""
    print("ESP32宿舍火灾报警系统启动")

    global current_status, status_cooldown

    # 连接WiFi
    if not connect_wifi():
        print("无法连接WiFi，程序退出")
        sys.exit(1)

    # 连接本地MQTT (带重连机制)
    mqtt_client = connect_mqtt_with_retry(max_retries=3)
    if mqtt_client is None:
        print("无法连接本地MQTT服务器，程序退出")
        sys.exit(1)

    print("开始监测传感器数据...")

    # 主循环
    while True:
        try:
            # 读取所有传感器数据
            sensor_data = read_all_sensors()

            if sensor_data is not None:
                # 检查系统状态（三级机制）
                new_status, status_reason = check_system_status(sensor_data)

                # 状态变化处理
                if new_status != current_status and status_cooldown == 0:
                    if new_status == SYSTEM_STATUS_ALARM:
                        # 触发警报
                        print(f"🔥 火灾警报触发: {status_reason}")
                        send_alert_data(mqtt_client, "fire", "high", sensor_data)
                        status_cooldown = 10  # 10秒冷却时间
                        # 警报时舵机转到最大角度
                        control_servo(180, new_status)
                    elif new_status == SYSTEM_STATUS_WARNING:
                        # 触发警告
                        print(f"⚠️ 环境警告: {status_reason}")
                        send_alert_data(mqtt_client, "warning", "medium", sensor_data)
                        # 警告时舵机转到中等角度
                        control_servo(90, new_status)
                    elif current_status == SYSTEM_STATUS_ALARM:
                        # 从警报恢复
                        print("✅ 火灾警报解除")
                        # 恢复时舵机回到初始位置
                        control_servo(0, new_status)
                    elif current_status == SYSTEM_STATUS_WARNING:
                        # 从警告恢复
                        print("✅ 环境警告解除")
                        # 恢复时舵机回到初始位置
                        control_servo(0, new_status)

                    current_status = new_status

                # 控制所有执行器
                control_fan(sensor_data['temperature'], current_status)
                control_buzzer(current_status, sensor_data['sound'])

                # 如果光照太暗，舵机模拟调节（例如打开窗帘）
                if sensor_data['light'] < LIGHT_DARK_THRESHOLD:
                    control_servo(45, current_status)  # 半开状态

                # 更新OLED显示
                update_oled_display(sensor_data, current_status, status_reason)

                # 发送传感器数据
                send_sensor_data(mqtt_client, sensor_data, current_status, status_reason)

            else:
                print("传感器读取失败，跳过此次循环")

            # 处理状态冷却
            if status_cooldown > 0:
                status_cooldown -= 1

            # 等待下一次读取
            time.sleep(READ_INTERVAL)

        except KeyboardInterrupt:
            print("\n程序被用户中断")
            break
        except Exception as e:
            print(f"主循环错误: {e}")
            time.sleep(5)  # 出错后等待5秒再继续

    # 清理资源
    try:
        fan_pwm.duty(0)      # 关闭风扇
        buzzer_pin.value(0)   # 关闭蜂鸣器
        servo_pwm.duty(0)     # 舵机回零
        mqtt_client.disconnect()
        print("MQTT连接已断开")
        oled.fill(0)
        oled.text("系统已停止", 0, 0, 1)
        oled.show()
    except:
        pass

    print("程序结束")

if __name__ == "__main__":
    main()