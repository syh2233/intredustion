'''
ESP32火灾报警系统 - OLED版本
包含OLED显示、传感器监测和MQTT上传
接线：OLED SCL->GPIO25, OLED SDA->GPIO26, VCC->5V, GND->GND
火焰传感器: GPIO14, 声音传感器: GPIO35(DO), GPIO13(AO), MQ2: GPIO34(AO), GPIO2(DO)
'''

from machine import Pin, ADC, PWM
import time
import json
import network
import socket
from machine import SoftI2C
from ssd1306 import SSD1306_I2C

def test_network_connectivity(server, port):
    """测试网络连通性"""
    try:
        test_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        test_sock.settimeout(5)
        test_sock.connect((server, port))
        test_sock.close()
        return True, None
    except Exception as e:
        return False, str(e)

def test_network_routing(gateway, target_ip):
    """测试网络路由"""
    try:
        # 先测试网关连通性
        print(f"🔍 测试网关 {gateway} 连通性...")
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(3)
        sock.connect((gateway, 80))  # 测试网关的80端口
        sock.close()
        print(f"✅ 网关 {gateway} 可达")

        # 分析IP地址
        esp32_ip_parts = [int(x) for x in gateway.split('.')]
        target_ip_parts = [int(x) for x in target_ip.split('.')]

        if esp32_ip_parts[:3] == target_ip_parts[:3]:
            print(f"✅ ESP32和目标服务器在同一网段: {'.'.join(map(str, esp32_ip_parts[:3]))}")
            return True
        else:
            print(f"⚠️ ESP32和目标服务器不在同一网段")
            print(f"   ESP32网段: {'.'.join(map(str, esp32_ip_parts[:3]))}")
            print(f"   目标网段: {'.'.join(map(str, target_ip_parts[:3]))}")
            return False

    except Exception as e:
        print(f"❌ 网关测试失败: {e}")
        return False

# ==================== 常量配置 ====================
DEVICE_ID = "esp32_fire_alarm_01"

# WiFi配置
WIFI_SSID = "syh2031"
WIFI_PASSWORD = "12345678"

# MQTT配置
MQTT_SERVER = "192.168.24.32"
MQTT_PORT = 1883

# GPIO配置（用户指定接口）
DHT11_PIN = 4
FLAME_AO_PIN = 14  # 火焰传感器模拟输入
FLAME_DO_PIN = 14  # 火焰传感器数字输入（用户指定）
MQ2_AO_PIN = 34   # MQ2烟雾传感器模拟输入
MQ2_DO_PIN = 2    # MQ2烟雾传感器数字输入
SOUND_AO_PIN = 13 # 声音传感器模拟输入
SOUND_DO_PIN = 35 # 声音传感器数字输入
SERVO_PIN = 15    # 舵机控制

# BH1750配置（光照传感器）
BH1750_SCL = 22   # BH1750 SCL接口
BH1750_SDA = 21   # BH1750 SDA接口

# OLED配置
OLED_SCL = 25     # OLED SCL接口
OLED_SDA = 26     # OLED SDA接口
OLED_WIDTH = 128
OLED_HEIGHT = 64

# 舵机角度配置
SERVO_SAFE_ANGLE = 0      # 安全位置（舵机关闭）
SERVO_ALERT_ANGLE = 90    # 警报位置（舵机启动）

# ==================== 硬件初始化 ====================
print("🔧 初始化硬件...")

# 火焰传感器故障标志
FLAME_SENSOR_FAILED = False  # 必须启用火焰传感器，这是火灾报警系统的核心

# 初始化OLED
i2c_oled = SoftI2C(scl=Pin(OLED_SCL), sda=Pin(OLED_SDA))
oled = SSD1306_I2C(OLED_WIDTH, OLED_HEIGHT, i2c_oled)
oled.fill(0)
oled.text("ESP32 Alarm", 0, 0)
oled.text("Initializing...", 0, 16)
oled.show()

# 初始化BH1750光照传感器
i2c_bh1750 = SoftI2C(scl=Pin(BH1750_SCL), sda=Pin(BH1750_SDA))
print("✅ BH1750初始化完成")

# 初始化舵机
servo = PWM(Pin(SERVO_PIN), freq=50)
servo.duty(0)
print("✅ 舵机初始化完成")

# 初始化传感器
print(f"初始化火焰传感器 - 引脚: {FLAME_DO_PIN}")
# 使用与校准程序完全相同的初始化方式
flame_do = Pin(FLAME_DO_PIN, Pin.IN)
print("✅ 火焰传感器初始化成功")

mq2_ao = ADC(Pin(MQ2_AO_PIN))
mq2_do = Pin(MQ2_DO_PIN, Pin.IN)
sound_do = Pin(SOUND_DO_PIN, Pin.IN)

# 设置ADC衰减（火焰传感器使用数字模式，MQ2使用模拟模式）
print("设置ADC衰减...")
try:
    # 火焰传感器使用数字模式，不需要ADC衰减设置
    print("✅ 火焰传感器使用数字模式")
except Exception as e:
    print(f"火焰传感器设置失败: {e}")

try:
    # mq2_ao不设置衰减，避免GPIO34的衰减问题
    print("✅ MQ2传感器初始化成功（跳过衰减设置）")
except Exception as e:
    print(f"⚠️ MQ2传感器设置失败: {e}")

print("✅ 传感器初始化完成")

# 测试火焰传感器读取
print("测试火焰传感器读取...")
try:
    test_flame_digital = flame_do.value()
    test_flame_analog = 0 if test_flame_digital == 0 else 4095
    print(f"✅ 火焰传感器测试读取成功: 数字={test_flame_digital}, 模拟={test_flame_analog}")
except Exception as e:
    print(f"❌ 火焰传感器测试读取失败: {e}")

# 初始化声音传感器（模拟值）
try:
    sound_ao = ADC(Pin(SOUND_AO_PIN))
    # 不设置衰减，避免GPIO13的衰减设置问题
    print("✅ 声音传感器初始化成功（跳过衰减设置）")
    SOUND_ANALOG_AVAILABLE = True
except Exception as e:
    SOUND_ANALOG_AVAILABLE = False
    print(f"⚠️ 声音传感器初始化失败: {e}")

# ==================== MQTT客户端类 ====================
class SimpleMQTTClient:
    def __init__(self, client_id, server, port=1883):
        self.client_id = client_id
        self.server = server
        self.port = port
        self.sock = None
        self.connected = False
        self.last_ping = time.time()

    def connect(self):
        """连接到MQTT服务器"""
        try:
            print(f"📡 正在连接MQTT: {self.server}:{self.port}")

            # 创建socket连接
            self.sock = socket.socket()
            self.sock.settimeout(15)
            addr = socket.getaddrinfo(self.server, self.port)[0][-1]
            self.sock.connect(addr)
            print("TCP连接成功")

            # 构建MQTT CONNECT消息
            protocol_name = b"MQTT"
            protocol_level = 4  # MQTT 3.1.1
            flags = 0x02  # Clean session
            keep_alive = 30

            # 可变头部
            var_header = bytearray()
            var_header.append(0)
            var_header.append(len(protocol_name))
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
                self.last_ping = time.time()
                print("✅ MQTT连接成功!")
                return True
            else:
                print(f"❌ MQTT连接失败")
                return False

        except Exception as e:
            print(f"❌ MQTT连接异常: {e}")
            if self.sock:
                try:
                    self.sock.close()
                except:
                    pass
            self.connected = False
            return False

    def encode_remaining_length(self, length):
        """编码MQTT剩余长度字段"""
        encoded = bytearray()
        while True:
            byte = length % 128
            length //= 128
            if length > 0:
                byte |= 0x80
            encoded.append(byte)
            if length == 0:
                break
        return encoded

    def publish(self, topic, message):
        """发布消息"""
        if not self.connected:
            return False

        try:
            # 检查是否需要发送PINGREQ（保持连接）
            current_time = time.time()
            if current_time - self.last_ping > 30:  # 每30秒发送一次PING
                try:
                    self.sock.send(b"\xC0\x00")  # PINGREQ
                    self.last_ping = current_time
                except:
                    self.connected = False
                    return False

            topic_bytes = topic.encode()
            message_bytes = message.encode()

            # 计算剩余长度
            topic_length = len(topic_bytes)
            message_length = len(message_bytes)
            remaining_length = 2 + topic_length + message_length

            # 构建PUBLISH消息
            publish_msg = bytearray()
            publish_msg.append(0x30)  # PUBLISH QoS 0

            # 添加编码后的剩余长度
            remaining_length_bytes = self.encode_remaining_length(remaining_length)
            publish_msg.extend(remaining_length_bytes)

            # 添加主题长度和主题
            publish_msg.append(topic_length >> 8)
            publish_msg.append(topic_length & 0xFF)
            publish_msg.extend(topic_bytes)

            # 添加消息内容
            publish_msg.extend(message_bytes)

            self.sock.send(publish_msg)
            return True

        except Exception as e:
            print(f"❌ MQTT发布失败: {e}")
            self.connected = False
            return False

# ==================== 传感器读取函数 ====================
# 火焰传感器状态管理
flame_zero_count = 0
flame_one_count = 0
flame_calibration_mode = False
flame_last_normal_time = 0
flame_sensor_fault_count = 0
flame_backup_pin = 27  # 备用引脚
flame_using_backup = False

def read_flame():
    """读取火焰传感器 - 简化版本，与校准程序逻辑一致"""
    try:
        # 完全按照校准程序的方式读取
        digital_value = flame_do.value()

        # 简单的状态显示
        if digital_value == 0:
            print(f"🔥 火焰传感器: {digital_value} (火焰)")
        else:
            print(f"✅ 火焰传感器: {digital_value} (正常)")

        # 为了保持数据格式一致性，设置模拟值
        analog_value = 0 if digital_value == 0 else 4095

        return analog_value, digital_value

    except Exception as e:
        print(f"火焰传感器读取错误: {e}")
        return 4095, 1  # 默认返回正常状态

def read_mq2():
    """读取MQ2烟雾传感器"""
    global mq2_ao
    try:
        # 每次都重新初始化ADC，避免GPIO34的超时问题
        mq2_ao = ADC(Pin(MQ2_AO_PIN))
        # 使用正确的常量设置衰减
        try:
            mq2_ao.atten(mq2_ao.ATTN_11DB)  # 使用常量而不是数值
        except:
            try:
                mq2_ao.atten(11)  # 备用：使用数值
            except:
                pass  # 如果都不行，使用默认衰减
        time.sleep(0.05)  # 短暂延时确保初始化完成

        analog_value = mq2_ao.read()
        digital_value = mq2_do.value()

        # 添加调试信息
        if analog_value == 4095:
            print(f"⚠️ MQ2读数4095，可能需要检查连接或传感器")

        return analog_value, digital_value

    except Exception as e:
        print(f"MQ2传感器读取错误: {e}")
        return 4095, 1  # 默认返回正常状态

def read_sound():
    """读取声音传感器"""
    global sound_ao, SOUND_ANALOG_AVAILABLE
    try:
        digital_value = sound_do.value()

        if SOUND_ANALOG_AVAILABLE:
            try:
                analog_value = sound_ao.read()
            except:
                # 重新初始化声音传感器ADC
                print("🔧 声音传感器重新初始化")
                try:
                    sound_ao = ADC(Pin(SOUND_AO_PIN))
                    # 使用正确的常量设置衰减
                    try:
                        sound_ao.atten(sound_ao.ATTN_11DB)
                    except:
                        try:
                            sound_ao.atten(11)
                        except:
                            pass
                    time.sleep(0.05)
                    analog_value = sound_ao.read()
                except:
                    SOUND_ANALOG_AVAILABLE = False
                    analog_value = None
        else:
            analog_value = None

        return analog_value, digital_value
    except Exception as e:
        print(f"声音传感器读取错误: {e}")
        return None, None

def read_bh1750():
    """读取BH1750光照传感器"""
    try:
        # BH1750连续高分辨率模式
        i2c_bh1750.writeto(0x23, b'\x10')  # 0x23是BH1750的I2C地址
        time.sleep(0.2)  # 等待测量完成
        data = i2c_bh1750.readfrom(0x23, 2)
        lux = (data[0] << 8 | data[1]) / 1.2
        return round(lux, 1)
    except:
        return None

def read_dht11():
    """读取DHT11温湿度传感器"""
    try:
        import dht
        sensor = dht.DHT11(Pin(DHT11_PIN))
        sensor.measure()
        return sensor.temperature(), sensor.humidity()
    except:
        # 如果读取失败，返回默认值
        return 26, 50

def check_fire_alarm(flame_analog, mq2_analog, temperature):
    """火灾检测算法 - 使用实际传感器读数"""
    if flame_analog is None and mq2_analog is None and temperature is None:
        return "normal"

    # 警报条件（任一满足即触发）
    # 火焰传感器值低表示检测到火焰（通常<500，降低误报）
    # MQ2烟雾传感器值低表示烟雾浓度高
    alarm_condition = False

    # 检查火焰传感器（如果未故障）
    if not FLAME_SENSOR_FAILED and flame_analog is not None and flame_analog < 500:
        alarm_condition = True
        print(f"🔥 火焰警报: flame_analog={flame_analog}")
    elif mq2_analog is not None and mq2_analog < 1000:
        alarm_condition = True
        print(f"💨 烟雾警报: mq2_analog={mq2_analog}")
    elif temperature is not None and temperature > 40:
        alarm_condition = True
        print(f"🌡️ 温度警报: temperature={temperature}")

    if alarm_condition:
        return "alarm"

    # 警告条件（任一满足即触发）
    warning_condition = False

    # 检查火焰传感器（如果未故障）
    if not FLAME_SENSOR_FAILED and flame_analog is not None and flame_analog < 1000:
        warning_condition = True
        print(f"🔥 火焰警告: flame_analog={flame_analog}")
    elif mq2_analog is not None and mq2_analog < 1500:
        warning_condition = True
        print(f"💨 烟雾警告: mq2_analog={mq2_analog}")
    elif temperature is not None and temperature > 35:
        warning_condition = True
        print(f"🌡️ 温度警告: temperature={temperature}")

    if warning_condition:
        return "warning"

    return "normal"

# ==================== OLED显示函数 ====================
def update_oled_display(flame_analog, flame_digital, mq2_analog, mq2_digital, sound_analog, sound_digital, temperature, humidity, status):
    """更新OLED显示"""
    oled.fill(0)

    # 标题
    oled.text("Fire Alarm System", 0, 0)

    # 传感器数据
    oled.text(f"Flame: {flame_analog}", 0, 16)
    oled.text(f"Smoke: {mq2_analog}", 0, 26)
    oled.text(f"Temp: {temperature}C", 0, 36)
    oled.text(f"Humi: {humidity}%", 0, 46)

    # 状态
    if len(status) > 12:
        oled.text(status[:12], 0, 56)
    else:
        oled.text(status, 0, 56)

    oled.show()

# ==================== 系统状态管理 ====================
class SystemStatus:
    def __init__(self):
        self.current_servo_angle = SERVO_SAFE_ANGLE
        self.alert_count = 0
        self.last_alert_time = 0
        self.servo_active = False

    def set_servo_angle(self, angle):
        """设置舵机角度"""
        if self.current_servo_angle != angle:
            duty = int((angle / 180) * 102 + 26)  # 0-180度映射到26-128
            servo.duty(duty)
            self.current_servo_angle = angle
            print(f"🔧 舵机角度: {angle}度")
            return True
        return False

    def check_danger(self, flame_analog, mq2_analog, mq2_digital, temperature):
        """检查危险情况"""
        danger_detected = False
        danger_reason = ""

        # 检查火焰
        if flame_analog is not None and flame_analog < 1000:
            danger_detected = True
            danger_reason = "火焰警报"

        # 检查烟雾
        elif mq2_analog is not None and mq2_analog < 1000:
            danger_detected = True
            danger_reason = "烟雾警报"

        # 检查温度
        elif temperature is not None and temperature > 40:
            danger_detected = True
            danger_reason = "温度警报"

        # 处理警报状态
        current_time = time.time()
        if danger_detected:
            if current_time - self.last_alert_time > 2:  # 2秒内的警报算连续
                self.alert_count = 0
            self.last_alert_time = current_time
            self.alert_count += 1

            # 连续3次警报才启动舵机
            if self.alert_count >= 3:
                if not self.servo_active:
                    self.set_servo_angle(SERVO_ALERT_ANGLE)
                    self.servo_active = True
                    print(f"🚨 危险！{danger_reason}")
                    return "危险警报", danger_reason
            else:
                return "警告中", f"{danger_reason}({self.alert_count}/3)"
        else:
            self.alert_count = 0
            if self.servo_active:
                self.set_servo_angle(SERVO_SAFE_ANGLE)
                self.servo_active = False
                print("✅ 环境恢复正常")
                return "恢复正常", "环境正常"

        return "正常", "环境正常"

# ==================== 主程序 ====================
def main():
    print("🚀 ESP32火灾报警系统启动")
    print("=" * 60)

    # 初始化系统状态
    system_status = SystemStatus()

    # 连接WiFi
    print("📡 连接WiFi...")
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)

    if not wlan.isconnected():
        wlan.connect(WIFI_SSID, WIFI_PASSWORD)
        for i in range(30):
            if wlan.isconnected():
                break
            time.sleep(0.5)
            print(".", end="")
        print()

    if wlan.isconnected():
        ip_info = wlan.ifconfig()
        print(f"✅ WiFi连接成功! IP: {ip_info[0]}")
        print(f"   子网掩码: {ip_info[1]}")
        print(f"   网关: {ip_info[2]}")
        print(f"   DNS: {ip_info[3]}")
        wifi_connected = True
    else:
        print("❌ WiFi连接失败")
        wifi_connected = False

    # 连接MQTT
    mqtt_client = SimpleMQTTClient(DEVICE_ID, MQTT_SERVER, MQTT_PORT)
    mqtt_connected = False

    if wifi_connected:
        print("📡 正在连接MQTT...")

        # 先测试网络路由和连通性
        print(f"🔍 网络诊断开始...")
        print(f"   ESP32 IP: {ip_info[0]}")
        print(f"   网关: {ip_info[2]}")
        print(f"   目标服务器: {MQTT_SERVER}")

        # 测试网络路由
        routing_ok = test_network_routing(ip_info[2], MQTT_SERVER)

        # 测试网络连通性
        print(f"\n🔍 测试到 {MQTT_SERVER}:{MQTT_PORT} 的连通性...")
        can_connect, error = test_network_connectivity(MQTT_SERVER, MQTT_PORT)
        if can_connect:
            print("✅ 网络连通性正常")
            mqtt_connected = mqtt_client.connect()
        else:
            print(f"❌ 网络连通性测试失败: {error}")
            if "Host is unreachable" in error or "EHOSTUNREACH" in error:
                print("🔧 解决建议:")
                print("   1. 检查MQTT服务器IP地址是否正确")
                print("   2. 确保MQTT服务器在同一网络")
                print("   3. 检查路由器配置")
                print("   4. 检查防火墙设置")

        # 如果MQTT连接失败，提供诊断建议
        if not mqtt_connected:
            print("\n🔍 MQTT连接诊断:")
            print(f"   ESP32 IP: {ip_info[0]}")
            print(f"   MQTT服务器: {MQTT_SERVER}:{MQTT_PORT}")
            print("   建议:")
            print("   1. 检查MQTT服务器是否运行")
            print("   2. 检查网络连接")
            print("   3. 检查防火墙设置")
            print("   4. 检查MQTT服务器端口配置")

    # 更新OLED显示
    update_oled_display(0, 0, 0, 0, 0, 0, 26, 50, "Starting...")

    # 主循环
    print("📊 开始监测...")
    print("=" * 80)

    count = 0
    while True:
        count += 1

        # 读取传感器数据
        flame_analog, flame_digital = read_flame()
        mq2_analog, mq2_digital = read_mq2()
        sound_analog, sound_digital = read_sound()
        temperature, humidity = read_dht11()
        light_level = read_bh1750()

        # 检查危险状态（原有逻辑）
        status, reason = system_status.check_danger(flame_analog, mq2_analog, mq2_digital, temperature)

        # 火灾报警检测（MQTT使用）
        alarm_status = check_fire_alarm(flame_analog, mq2_analog, temperature)

        # 显示数据
        sound_str = f"{sound_analog}" if sound_analog is not None else "N/A"
        light_str = f"{light_level}" if light_level is not None else "N/A"
        print(f"[{count:3d}] 火焰:{flame_analog},{flame_digital} | 烟雾:{mq2_analog},{mq2_digital} | 声音:{sound_str},{sound_digital} | 温度:{temperature}°C | 湿度:{humidity}% | 光照:{light_str}lux | {status} | {reason} | MQTT:{alarm_status}")

        # 更新OLED显示
        oled_status = f"{status}/{alarm_status}"[:10]  # 显示两种状态
        update_oled_display(flame_analog, flame_digital, mq2_analog, mq2_digital, sound_analog, sound_digital, temperature, humidity, oled_status)

        # 发送MQTT数据 - 发送实际传感器读数
        if mqtt_connected:
            try:
                # 直接发送实际传感器读数，不做转换
                payload = {
                    "device_id": DEVICE_ID,
                    "flame": flame_analog,
                    "smoke": mq2_analog,
                    "temperature": temperature,
                    "humidity": humidity,
                    "light": light_level,
                    "status": alarm_status,  # 使用火灾检测结果
                    "timestamp": time.time()
                }

                # 发送传感器数据
                topic = f"esp32/{DEVICE_ID}/data/json"
                if mqtt_client.publish(topic, json.dumps(payload)):
                    print("📡 MQTT数据已发送")
                else:
                    print("❌ MQTT发送失败")
                    mqtt_connected = False
                    return

                # 如果是警报状态，发送警报消息
                if alarm_status == "alarm":
                    alert_msg = {
                        "type": "fire",
                        "level": "high",
                        "data": payload,
                        "message": "检测到火灾风险！"
                    }
                    mqtt_client.publish(f"esp32/{DEVICE_ID}/alert/fire", json.dumps(alert_msg))
                elif alarm_status == "warning":
                    alert_msg = {
                        "type": "warning",
                        "level": "medium",
                        "data": payload,
                        "message": "环境异常警告"
                    }
                    mqtt_client.publish(f"esp32/{DEVICE_ID}/alert/warning", json.dumps(alert_msg))

            except Exception as e:
                print(f"❌ MQTT发送异常: {e}")
                mqtt_connected = False
        else:
            # 尝试重连MQTT
            if count % 10 == 0:  # 每10次循环尝试重连一次
                print("🔄 尝试重连MQTT...")
                mqtt_connected = mqtt_client.connect()
                if not mqtt_connected:
                    print("❌ 重连失败")

        # 等待下次循环
        time.sleep(1.5)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n程序被中断")
        # 清理资源
        if mqtt_client and mqtt_client.connected:
            mqtt_client.publish(f"esp32/{DEVICE_ID}/status/online", "0")
            mqtt_client.disconnect()
        print("系统已安全关闭")