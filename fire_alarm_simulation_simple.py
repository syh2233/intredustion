'''
ESP32火灾报警系统 - 模拟数据简化版本
跳过OLED初始化，专门用于MQTT性能测试
'''

from machine import Pin, ADC, PWM
import time
import json
import network
import socket
import random
import math

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
DEVICE_ID = "esp32_fire_alarm_sim_01"

# WiFi配置
WIFI_SSID = "syh2031"
WIFI_PASSWORD = "12345678"

# MQTT配置
MQTT_SERVER = "192.168.24.32"
MQTT_PORT = 1883

# 模拟数据配置
SIMULATION_MODE = "normal"  # normal, warning, alarm, random
SIMULATION_SPEED = 1.5  # 数据发送间隔（秒）

# ==================== 模拟数据生成器 ====================
class SensorSimulator:
    def __init__(self):
        self.time_counter = 0
        self.base_flame = 1500
        self.base_smoke = 50
        self.base_temperature = 26
        self.base_humidity = 50
        self.base_sound = 100

        # 性能统计
        self.data_count = 0
        self.mqtt_success_count = 0
        self.mqtt_fail_count = 0
        self.start_time = time.time()

    def generate_flame_data(self):
        """生成火焰传感器模拟数据"""
        self.time_counter += 1

        if SIMULATION_MODE == "normal":
            # 正常状态：火焰值较高（1500-2000）
            variation = random.randint(-200, 200)
            flame_value = max(1000, min(2000, self.base_flame + variation))

        elif SIMULATION_MODE == "warning":
            # 警告状态：火焰值中等（1000-1200）
            if random.random() < 0.3:  # 30%概率出现警告值
                flame_value = random.randint(1000, 1200)
            else:
                flame_value = random.randint(1300, 1500)

        elif SIMULATION_MODE == "alarm":
            # 警报状态：火焰值低（500-900）
            if random.random() < 0.5:  # 50%概率出现警报值
                flame_value = random.randint(500, 900)
            else:
                flame_value = random.randint(1000, 1300)

        else:  # random
            # 随机模式：完全随机
            flame_value = random.randint(500, 2000)

        return flame_value

    def generate_smoke_data(self):
        """生成烟雾传感器模拟数据"""
        if SIMULATION_MODE == "normal":
            # 正常状态：烟雾值低（20-60）
            smoke_value = random.randint(20, 60)

        elif SIMULATION_MODE == "warning":
            # 警告状态：烟雾值中等（50-80）
            if random.random() < 0.3:
                smoke_value = random.randint(50, 80)
            else:
                smoke_value = random.randint(20, 50)

        elif SIMULATION_MODE == "alarm":
            # 警报状态：烟雾值高（80-150）
            if random.random() < 0.5:
                smoke_value = random.randint(80, 150)
            else:
                smoke_value = random.randint(40, 80)

        else:  # random
            smoke_value = random.randint(20, 150)

        return smoke_value

    def generate_temperature_data(self):
        """生成温度传感器模拟数据"""
        if SIMULATION_MODE == "normal":
            # 正常状态：温度正常（24-28°C）
            temp = random.randint(24, 28)

        elif SIMULATION_MODE == "warning":
            # 警告状态：温度偏高（32-36°C）
            if random.random() < 0.3:
                temp = random.randint(32, 36)
            else:
                temp = random.randint(26, 32)

        elif SIMULATION_MODE == "alarm":
            # 警报状态：温度高（38-45°C）
            if random.random() < 0.5:
                temp = random.randint(38, 45)
            else:
                temp = random.randint(30, 38)

        else:  # random
            temp = random.randint(20, 45)

        return temp

    def generate_humidity_data(self):
        """生成湿度传感器模拟数据"""
        # 湿度相对稳定，受温度轻微影响
        base_humidity = 50
        variation = random.randint(-10, 10)
        humidity = max(30, min(80, base_humidity + variation))
        return humidity

    def generate_sound_data(self):
        """生成声音传感器模拟数据"""
        # 声音数据相对独立
        sound_analog = random.randint(50, 500)
        sound_digital = 1 if sound_analog > 300 else 0
        return sound_analog, sound_digital

    def get_all_sensor_data(self):
        """获取所有传感器模拟数据"""
        flame = self.generate_flame_data()
        smoke = self.generate_smoke_data()
        temperature = self.generate_temperature_data()
        humidity = self.generate_humidity_data()
        sound_analog, sound_digital = self.generate_sound_data()

        # 为了与原代码兼容，转换为原始格式
        flame_original = 0 if flame < 1000 else 1  # 转换为数字输出
        mq2_analog = max(0, 2000 - smoke)  # 转换为MQ2模拟值格式
        mq2_digital = 1 if smoke > 100 else 0  # 转换为数字输出

        self.data_count += 1

        return {
            'flame_value': flame_original,
            'flame_normalized': flame,
            'mq2_analog': mq2_analog,
            'mq2_digital': mq2_digital,
            'smoke_normalized': smoke,
            'sound_analog': sound_analog,
            'sound_digital': sound_digital,
            'temperature': temperature,
            'humidity': humidity
        }

    def get_performance_stats(self):
        """获取性能统计"""
        elapsed_time = time.time() - self.start_time
        if elapsed_time > 0:
            data_rate = self.data_count / elapsed_time
            success_rate = (self.mqtt_success_count / max(1, self.mqtt_success_count + self.mqtt_fail_count)) * 100
        else:
            data_rate = 0
            success_rate = 0

        return {
            'total_data_points': self.data_count,
            'mqtt_success': self.mqtt_success_count,
            'mqtt_failed': self.mqtt_fail_count,
            'data_rate': data_rate,
            'success_rate': success_rate,
            'uptime': elapsed_time
        }

# ==================== 初始化 ====================
print("🔧 初始化模拟数据系统（简化版本）...")

# 初始化传感器模拟器
sensor_sim = SensorSimulator()
print("✅ 传感器模拟器初始化完成")

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

# ==================== 传感器读取函数（模拟） ====================
def read_flame():
    """读取火焰传感器（模拟）"""
    data = sensor_sim.get_all_sensor_data()
    return data['flame_value']

def read_mq2():
    """读取MQ2烟雾传感器（模拟）"""
    data = sensor_sim.get_all_sensor_data()
    return data['mq2_analog'], data['mq2_digital']

def read_sound():
    """读取声音传感器（模拟）"""
    data = sensor_sim.get_all_sensor_data()
    return data['sound_analog'], data['sound_digital']

def read_dht11():
    """读取DHT11温湿度传感器（模拟）"""
    data = sensor_sim.get_all_sensor_data()
    return data['temperature'], data['humidity']

def check_fire_alarm(flame_value, mq2_analog, temperature):
    """火灾检测算法 - 基于main_sim.py的逻辑"""
    if flame_value is None and mq2_analog is None and temperature is None:
        return "normal"

    # 转换火焰值（0表示检测到火焰，需要转换为低值）
    flame_normalized = 500 if flame_value == 0 else 1500

    # 转换MQ2值（值越低表示烟雾越浓）
    smoke_normalized = 2000 - mq2_analog if mq2_analog is not None else 50

    # 警报条件（任一满足即触发）
    if flame_normalized < 1000 or smoke_normalized > 100 or (temperature is not None and temperature > 40):
        return "alarm"
    # 警告条件（任一满足即触发）
    elif flame_normalized < 1100 or smoke_normalized > 50 or (temperature is not None and temperature > 35):
        return "warning"
    else:
        return "normal"

# ==================== 系统状态管理 ====================
class SystemStatus:
    def __init__(self):
        self.alert_count = 0
        self.last_alert_time = 0

    def check_danger(self, flame_value, mq2_analog, mq2_digital, temperature):
        """检查危险情况"""
        danger_detected = False
        danger_reason = ""

        # 检查火焰
        if flame_value is not None and flame_value == 0:
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
            if current_time - self.last_alert_time > 2:
                self.alert_count = 0
            self.last_alert_time = current_time
            self.alert_count += 1

            if self.alert_count >= 3:
                print(f"🚨 危险！{danger_reason}")
                return "危险警报", danger_reason
            else:
                return "警告中", f"{danger_reason}({self.alert_count}/3)"
        else:
            self.alert_count = 0
            return "正常", "环境正常"

        return "正常", "环境正常"

# ==================== 主程序 ====================
def main():
    print("🚀 ESP32火灾报警系统（模拟数据简化版本）启动")
    print("=" * 60)
    print(f"📊 模拟模式: {SIMULATION_MODE}")
    print(f"⏱️  数据间隔: {SIMULATION_SPEED}秒")
    print("💡 跳过OLED初始化，专注MQTT性能测试")
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
        wifi_connected = True
    else:
        print("❌ WiFi连接失败")
        wifi_connected = False

    # 连接MQTT
    mqtt_client = SimpleMQTTClient(DEVICE_ID, MQTT_SERVER, MQTT_PORT)
    mqtt_connected = False

    if wifi_connected:
        print("📡 正在连接MQTT...")

        # 网络诊断
        print(f"🔍 网络诊断开始...")
        print(f"   ESP32 IP: {ip_info[0]}")
        print(f"   网关: {ip_info[2]}")
        print(f"   目标服务器: {MQTT_SERVER}")

        # 测试网络连通性
        can_connect, error = test_network_connectivity(MQTT_SERVER, MQTT_PORT)
        if can_connect:
            print("✅ 网络连通性正常")
            mqtt_connected = mqtt_client.connect()
        else:
            print(f"❌ 网络连通性测试失败: {error}")

    # 主循环
    print("📊 开始模拟数据监测...")
    print("=" * 80)

    count = 0
    while True:
        count += 1

        # 生成模拟传感器数据
        sensor_data = sensor_sim.get_all_sensor_data()
        flame_value = sensor_data['flame_value']
        mq2_analog = sensor_data['mq2_analog']
        mq2_digital = sensor_data['mq2_digital']
        sound_analog = sensor_data['sound_analog']
        sound_digital = sensor_data['sound_digital']
        temperature = sensor_data['temperature']
        humidity = sensor_data['humidity']

        # 检查危险状态（原有逻辑）
        status, reason = system_status.check_danger(flame_value, mq2_analog, mq2_digital, temperature)

        # 火灾报警检测（MQTT使用）
        alarm_status = check_fire_alarm(flame_value, mq2_analog, temperature)

        # 显示数据
        sound_str = f"{sound_analog}" if sound_analog is not None else "N/A"
        print(f"[{count:3d}] 火焰:{flame_value} | 烟雾:{mq2_analog},{mq2_digital} | 声音:{sound_str},{sound_digital} | 温度:{temperature}°C | 湿度:{humidity}% | {status} | {reason} | MQTT:{alarm_status}")

        # 发送MQTT数据 - 使用与原代码相同的格式
        if mqtt_connected:
            try:
                payload = {
                    "device_id": DEVICE_ID,
                    "flame": sensor_data['flame_normalized'],
                    "smoke": sensor_data['smoke_normalized'],
                    "temperature": temperature,
                    "humidity": humidity,
                    "status": alarm_status,
                    "timestamp": time.time(),
                    "simulation_mode": SIMULATION_MODE,
                    "data_count": sensor_sim.data_count
                }

                # 发送传感器数据
                topic = f"esp32/{DEVICE_ID}/data/json"
                if mqtt_client.publish(topic, json.dumps(payload)):
                    print("📡 MQTT数据已发送")
                    sensor_sim.mqtt_success_count += 1
                else:
                    print("❌ MQTT发送失败")
                    sensor_sim.mqtt_fail_count += 1
                    mqtt_connected = False

                # 如果是警报状态，发送警报消息
                if alarm_status == "alarm":
                    alert_msg = {
                        "type": "fire",
                        "level": "high",
                        "data": payload,
                        "message": "检测到火灾风险！（模拟数据）"
                    }
                    mqtt_client.publish(f"esp32/{DEVICE_ID}/alert/fire", json.dumps(alert_msg))
                elif alarm_status == "warning":
                    alert_msg = {
                        "type": "warning",
                        "level": "medium",
                        "data": payload,
                        "message": "环境异常警告（模拟数据）"
                    }
                    mqtt_client.publish(f"esp32/{DEVICE_ID}/alert/warning", json.dumps(alert_msg))

            except Exception as e:
                print(f"❌ MQTT发送异常: {e}")
                sensor_sim.mqtt_fail_count += 1
                mqtt_connected = False
        else:
            # 尝试重连MQTT
            if count % 10 == 0:  # 每10次循环尝试重连一次
                print("🔄 尝试重连MQTT...")
                mqtt_connected = mqtt_client.connect()
                if not mqtt_connected:
                    print("❌ 重连失败")

        # 每60秒显示一次性能统计
        if count % 40 == 0:  # 40 * 1.5秒 = 60秒
            stats = sensor_sim.get_performance_stats()
            print(f"\n📊 性能统计:")
            print(f"   总数据点: {stats['total_data_points']}")
            print(f"   MQTT成功: {stats['mqtt_success']}")
            print(f"   MQTT失败: {stats['mqtt_failed']}")
            print(f"   数据速率: {stats['data_rate']:.2f} 数据点/秒")
            print(f"   成功率: {stats['success_rate']:.1f}%")
            print(f"   运行时间: {stats['uptime']:.1f}秒")
            print()

        # 等待下次循环
        time.sleep(SIMULATION_SPEED)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n程序被中断")
        print("📊 最终性能统计:")
        stats = sensor_sim.get_performance_stats()
        print(f"   总数据点: {stats['total_data_points']}")
        print(f"   MQTT成功: {stats['mqtt_success']}")
        print(f"   MQTT失败: {stats['mqtt_failed']}")
        print(f"   数据速率: {stats['data_rate']:.2f} 数据点/秒")
        print(f"   成功率: {stats['success_rate']:.1f}%")
        print(f"   运行时间: {stats['uptime']:.1f}秒")
        print("系统已安全关闭")