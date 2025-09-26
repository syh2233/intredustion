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
import ssd1306

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
pending_slave_mqtt_data = None  # 待发送的从机MQTT数据

# WiFi配置
WIFI_SSID = "syh2031"
WIFI_PASSWORD = "12345678"

# MQTT配置 - 使用公网端口映射·
MQTT_SERVER = "22.tcp.cpolar.top"
MQTT_PORT = 10020

# GPIO配置（用户指定接口）
DHT11_PIN = 4
FLAME_DO_PIN = 14  # 火焰传感器数字输入（0=有火，1=无火）
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
SERVO_SAFE_ANGLE = 90      # 安全位置（舵机关闭）
SERVO_ALERT_ANGLE = 0      # 警报位置（舵机启动）

# ==================== 硬件初始化 ====================
print("🔧 初始化硬件...")

# 火焰传感器故障标志
FLAME_SENSOR_FAILED = False  # 必须启用火焰传感器，这是火灾报警系统的核心

# 初始化BH1750光照传感器
i2c_bh1750 = SoftI2C(scl=Pin(BH1750_SCL), sda=Pin(BH1750_SDA))
print("✅ BH1750初始化完成")

# 初始化OLED显示屏
print(f"初始化OLED显示屏 - SDA:GPIO{OLED_SDA}, SCL:GPIO{OLED_SCL}")
try:
    i2c = SoftI2C(scl=Pin(OLED_SCL), sda=Pin(OLED_SDA), freq=400000)
    oled_width = 128
    oled_height = 64
    oled = ssd1306.SSD1306_I2C(oled_width, oled_height, i2c)
    oled.fill(0)
    oled.text("ESP32 Alarm", 0, 0)
    oled.text("Initializing...", 0, 16)
    oled.show()
    print("✅ OLED显示屏初始化成功")
except Exception as e:
    print(f"❌ OLED显示屏初始化失败: {e}")
    oled = None

# 初始化舵机
servo = PWM(Pin(SERVO_PIN), freq=50)
servo.duty(0)
print("✅ 舵机初始化完成")

# 初始化传感器
print(f"初始化火焰传感器 - 引脚: {FLAME_DO_PIN} (数字模式)")
# 使用数字读取火焰传感器
flame_do = Pin(FLAME_DO_PIN, Pin.IN)
print("✅ 火焰传感器初始化成功")

mq2_ao = ADC(Pin(MQ2_AO_PIN))
mq2_do = Pin(MQ2_DO_PIN, Pin.IN)
sound_do = Pin(SOUND_DO_PIN, Pin.IN)

# MQ2传感器不设置衰减，避免GPIO34的衰减问题
print("✅ MQ2传感器初始化成功（跳过衰减设置）")

print("✅ 传感器初始化完成")

# 测试火焰传感器读取
print("测试火焰传感器读取...")
try:
    test_flame_value = flame_do.value()
    flame_status = "检测到火焰" if test_flame_value == 0 else "正常"
    print(f"✅ 火焰传感器测试读取成功: 数字值={test_flame_value} ({flame_status})")
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

# ==================== UDP服务器类 ====================
class UDPServer:
    def __init__(self, port=8888):
        self.port = port
        self.socket = None
        self.running = False
        self.broadcast_socket = None
        self.slave_send_socket = None

    def start(self):
        """启动UDP服务器"""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.socket.bind(('0.0.0.0', self.port))
            self.socket.settimeout(0.1)  # 设置超时以避免阻塞主循环

            # 创建发送socket用于向从机发送数据
            self.slave_send_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.slave_send_socket.settimeout(1.0)

            self.running = True
            print(f"✅ UDP服务器启动成功，监听端口: {self.port}")
            return True
        except Exception as e:
            print(f"❌ UDP服务器启动失败: {e}")
            return False

    def receive_data(self):
        """接收UDP数据"""
        if not self.running or not self.socket:
            return None

        try:
            data, addr = self.socket.recvfrom(512)
            client_ip = addr[0]
            client_port = addr[1]

            # 添加调试信息：显示所有收到的UDP数据
            print(f"📨 收到UDP数据 - 来自: {client_ip}:{client_port}, 大小: {len(data)}字节")

            # 解析JSON数据
            try:
                json_data = json.loads(data.decode('utf-8'))
                print(f"📦 数据类型: {json_data.get('type', 'unknown')}")
                return json_data, client_ip, client_port
            except json.JSONDecodeError:
                print(f"❌ JSON解析失败 - 来自 {client_ip}:{client_port}")
                print(f"   原始数据: {data}")
                return None

        except Exception as e:
            # MicroPython socket超时或其他异常
            print(f"❌ UDP接收错误: {e}")
            return None

    def send_response(self, target_ip, target_port, response_data):
        """发送响应数据"""
        if not self.running or not self.socket:
            return False

        try:
            json_data = json.dumps(response_data)
            self.socket.sendto(json_data.encode(), (target_ip, target_port))
            print(f"📤 已发送响应到 {target_ip}:{target_port}")
            return True
        except Exception as e:
            print(f"❌ 发送响应失败: {e}")
            return False

    def send_master_data_to_slaves(self, slave_devices, master_data):
        """向所有从机发送主机数据"""
        if not self.slave_send_socket:
            return False

        try:
            success_count = 0
            for slave_id, slave_info in slave_devices.items():
                if slave_info['status'] == 'online':
                    slave_ip = slave_info['ip']
                    # 从机接收端口是8889
                    slave_port = 8889

                    # 构建主机数据消息
                    master_message = {
                        "type": "master_data",
                        "timestamp": time.time(),
                        "data": master_data
                    }

                    # 发送数据
                    json_data = json.dumps(master_message)
                    self.slave_send_socket.sendto(json_data.encode(), (slave_ip, slave_port))
                    success_count += 1

            if success_count > 0:
                print(f"📤 主机数据已发送到{success_count}个从机")
            return success_count > 0

        except Exception as e:
            print(f"❌ 发送主机数据到从机失败: {e}")
            return False

    def stop(self):
        """停止UDP服务器"""
        if self.socket:
            self.socket.close()
        if self.broadcast_socket:
            self.broadcast_socket.close()
        if self.slave_send_socket:
            self.slave_send_socket.close()
        self.running = False
        print("UDP服务器已停止")

# ==================== 从机数据处理类 ====================
class SlaveDataManager:
    def __init__(self):
        self.slave_devices = {}  # 存储从机信息
        self.slave_data = {}     # 存储从机传感器数据
        self.master_data = {}    # 存储主机传感器数据，用于同步给从机

    def process_slave_data(self, data, client_ip, client_port=None):
        """处理从机数据"""
        try:
            message_type = data.get('type', 'unknown')
            slave_id = data.get('slave_id', 'unknown')

            # 更新从机信息
            if slave_id not in self.slave_devices:
                self.slave_devices[slave_id] = {
                    'slave_id': slave_id,
                    'slave_name': data.get('slave_name', slave_id),
                    'ip': client_ip,
                    'last_seen': time.time(),
                    'status': 'online',
                    'sensors': data.get('sensors', {})
                }
                print(f"📱 新从机注册: {slave_id} ({client_ip})")
            else:
                self.slave_devices[slave_id]['last_seen'] = time.time()
                self.slave_devices[slave_id]['status'] = 'online'

            # 处理不同类型的消息
            if message_type == 'sensor_data':
                return self.process_sensor_data(data, slave_id)
            elif message_type == 'startup':
                return self.process_startup_data(data, slave_id, client_ip)
            elif message_type == 'test':
                print(f"🔧 收到测试消息 - 从机: {slave_id}")
                return True
            elif message_type == 'discover':
                return self.process_discover_request(data, slave_id, client_ip, client_port)
            else:
                print(f"⚠️ 未知消息类型: {message_type}")
                return False

        except Exception as e:
            print(f"❌ 从机数据处理错误: {e}")
            return False

    def process_sensor_data(self, data, slave_id):
        """处理传感器数据"""
        try:
            sensors = data.get('sensors', {})
            overall_status = data.get('overall_status', 'normal')
            sequence = data.get('sequence', 0)

            # 提取传感器数据
            flame_data = sensors.get('flame', {})
            mq2_data = sensors.get('mq2_smoke', {})

            flame_analog = flame_data.get('analog', 0)
            flame_status = flame_data.get('status', 'normal')
            mq2_analog = mq2_data.get('analog', 0)
            mq2_status = mq2_data.get('status', 'normal')

            # 存储从机数据
            self.slave_data[slave_id] = {
                'flame_analog': flame_analog,
                'flame_status': flame_status,
                'mq2_analog': mq2_analog,
                'mq2_status': mq2_status,
                'overall_status': overall_status,
                'timestamp': time.time(),
                'sequence': sequence
            }

            # 更新从机设备信息
            if slave_id in self.slave_devices:
                self.slave_devices[slave_id]['last_seen'] = time.time()
                self.slave_devices[slave_id]['status'] = 'online'

            # 打印接收到的数据
            print(f"📨 从机数据 - {slave_id} 序列:{sequence}")
            print(f"   火焰:{flame_analog}({flame_status}) | 烟雾:{mq2_analog}({mq2_status}) | 整体:{overall_status}")

            # 准备从机数据用于MQTT发送
            slave_mqtt_data = {
                "type": "sensor_data",
                "slave_id": slave_id,
                "slave_name": self.slave_devices[slave_id].get('slave_name', slave_id),
                "slave_location": self.slave_devices[slave_id].get('slave_location', '未知位置'),
                "timestamp": time.time(),
                "sensors": {
                    "flame": {
                        "analog": flame_analog,
                        "digital": 1 if flame_status == 'normal' else 0,
                        "status": flame_status
                    },
                    "mq2_smoke": {
                        "analog": mq2_analog,
                        "digital": 1 if mq2_status == 'normal' else 0,
                        "status": mq2_status
                    }
                },
                "overall_status": overall_status,
                "sequence": sequence
            }

            # 通过全局变量发送到MQTT (需要在主循环中处理)
            global pending_slave_mqtt_data
            pending_slave_mqtt_data = slave_mqtt_data

            # 检查是否需要触发警报
            if overall_status == 'alarm':
                print(f"🚨 从机{slave_id}检测到火灾风险！")
                return True
            elif overall_status == 'warning':
                print(f"⚠️  从机{slave_id}环境异常！")
                return True

            return True

        except Exception as e:
            print(f"❌ 传感器数据处理错误: {e}")
            return False

    def process_startup_data(self, data, slave_id, client_ip):
        """处理启动数据"""
        try:
            slave_name = data.get('slave_name', slave_id)
            sensors = data.get('sensors', [])

            print(f"📱 从机启动 - {slave_name} ({slave_id}) IP:{client_ip}")
            print(f"   传感器: {', '.join(sensors)}")

            # 更新从机信息
            self.slave_devices[slave_id].update({
                'slave_name': slave_name,
                'ip': client_ip,
                'sensors': sensors,
                'last_seen': time.time(),
                'status': 'online'
            })

            return True

        except Exception as e:
            print(f"❌ 启动数据处理错误: {e}")
            return False

    def update_master_data(self, flame_analog, flame_status, mq2_analog, mq2_status, temperature, humidity, status):
        """更新主机传感器数据"""
        self.master_data = {
            'flame_analog': flame_analog,
            'flame_status': flame_status,
            'mq2_analog': mq2_analog,
            'mq2_status': mq2_status,
            'temperature': temperature,
            'humidity': humidity,
            'status': status,
            'timestamp': time.time()
        }

    def check_slave_status(self):
        """检查从机状态"""
        current_time = time.time()
        offline_slaves = []

        for slave_id, info in self.slave_devices.items():
            if current_time - info['last_seen'] > 60:  # 60秒未收到数据认为离线
                info['status'] = 'offline'
                offline_slaves.append(slave_id)

        if offline_slaves:
            print(f"⚠️  以下从机可能离线: {', '.join(offline_slaves)}")

        return len(offline_slaves)

    def process_discover_request(self, data, slave_id, client_ip, client_port):
        """处理从机发现请求"""
        try:
            print(f"🔍 收到从机发现请求 - {slave_id} ({client_ip}:{client_port})")

            # 获取主机IP地址
            host_ip = network.WLAN(network.STA_IF).ifconfig()[0]
            print(f"📡 主机IP: {host_ip}, 准备响应到 {client_ip}:{client_port}")

            # 构建响应数据
            response = {
                "type": "discover_response",
                "host_id": DEVICE_ID,
                "host_name": "主机-01",
                "host_ip": host_ip,
                "host_port": 8888,
                "timestamp": time.time(),
                "message": f"主机{host_ip}响应发现请求"
            }

            # 通过UDP服务器发送响应
            if hasattr(self, 'udp_server') and self.udp_server:
                print(f"📤 正在发送发现响应到 {client_ip}:{client_port}")
                result = self.udp_server.send_response(client_ip, client_port, response)
                if result:
                    print(f"✅ 发现响应发送成功")
                else:
                    print(f"❌ 发现响应发送失败")
                return result
            else:
                print("❌ UDP服务器不可用，无法发送响应")
                return False

        except Exception as e:
            print(f"❌ 处理发现请求错误: {e}")
            return False

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
    """读取火焰传感器 - 数字模式"""
    try:
        # 读取数字值
        digital_value = flame_do.value()

        # 数字值：0=检测到火焰，1=正常
        if digital_value == 0:  # 检测到火焰
            print(f"🔥 火焰传感器: 检测到火焰!")
            analog_value = 0  # 用于显示的模拟值
        else:  # 正常状态
            print(f"✅ 火焰传感器: 正常")
            analog_value = 1500  # 用于显示的模拟值，设置为高值避免误报警

        return analog_value, digital_value

    except Exception as e:
        print(f"❌ 火焰传感器读取错误: {e}")
        return 1, 1  # 默认返回正常状态

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
        from machine import Pin
        import time
        pin = Pin(4)
        # 发送启动信号
        pin.init(Pin.OUT)
        pin.value(0)
        time.sleep_ms(20)
        pin.value(1)

        # 切换到输入模式并记录信号
        pin.init(Pin.IN, Pin.PULL_UP)

        changes = []
        last_value = 1
        last_time = time.ticks_us()

        start_time = time.ticks_us()
        while time.ticks_diff(time.ticks_us(), start_time) < 50000:
            current_value = pin.value()
            if current_value != last_value:
                current_time = time.ticks_us()
                duration = time.ticks_diff(current_time, last_time)
                changes.append((last_value, duration))
                last_value = current_value
                last_time = current_time
            time.sleep_us(1)

        # 解析数据
        if len(changes) < 10:
            return 26, 50

        bits = []
        for i in range(2, len(changes), 2):
            if i + 1 < len(changes):
                high_duration = changes[i][1]
                bit = 1 if high_duration > 50 else 0
                bits.append(bit)
                if len(bits) >= 40:
                    break

        if len(bits) < 40:
            return 26, 50

        # 转换为字节数据
        data = bytearray(5)
        for i in range(5):
            for j in range(8):
                data[i] = (data[i] << 1) | bits[i*8 + j]

        # 校验和检查
        checksum = (data[0] + data[1] + data[2] + data[3]) & 0xFF
        if checksum != data[4]:
            return 26, 50

        # 返回温度和湿度
        temperature = data[2]
        humidity = data[0]

        if 0 <= humidity <= 95 and 0 <= temperature <= 50:
            return temperature, humidity
        else:
            return 26, 50
    except:
        # 如果读取失败，返回默认值
        return 26, 50

def check_fire_alarm(flame_analog, mq2_analog, temperature, light_level):
    """火灾检测算法 - 使用实际传感器读数"""
    if flame_analog is None and mq2_analog is None and temperature is None and light_level is None:
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
    elif light_level is not None and light_level > 120:
        alarm_condition = True
        print(f"💡 光照警报: light_level={light_level}")

    if alarm_condition:
        return "alarm"

    # 警告条件（任一满足即触发）
    warning_condition = False

    # 检查火焰传感器（如果未故障）
    if not FLAME_SENSOR_FAILED and flame_analog is not None and flame_analog < 1000:
        warning_condition = True
        print(f"🔥 火焰警告: flame_analog={flame_analog}")
    elif mq2_analog is not None and mq2_analog < 1200:
        warning_condition = True
        print(f"💨 烟雾警告: mq2_analog={mq2_analog}")
    elif temperature is not None and temperature > 35:
        warning_condition = True
        print(f"🌡️ 温度警告: temperature={temperature}")
    elif light_level is not None and light_level > 120:
        warning_condition = True
        print(f"💡 光照警告: light_level={light_level}")

    if warning_condition:
        return "warning"

    return "normal"

# ==================== OLED显示函数 ====================
def update_oled_display(flame_analog, flame_digital, mq2_analog, mq2_digital, sound_analog, sound_digital, temperature, humidity, light_level, status, slave_data_manager=None):
    """更新OLED显示 - 修复字符截断问题"""
    if oled is None:
        return  # OLED不可用，直接返回

    oled.fill(0)

    # 第1行：标题（简化）
    oled.text("ALARM", 0, 0)

    # 第2行：火焰和烟雾 - 使用8像素行间距
    oled.text(f"F:{flame_analog}", 0, 8)
    oled.text(f"M:{mq2_analog}", 64, 8)

    # 第3行：温度和湿度
    oled.text(f"T:{temperature}", 0, 16)
    oled.text(f"H:{humidity}", 64, 16)

    # 第4行：光照
    if light_level is not None:
        light_val = min(light_level, 999)  # 限制为3位数
        oled.text(f"L:{light_val}", 0, 24)
    else:
        oled.text("L:---", 0, 24)

    # 第5行：系统状态
    if status == "normal":
        status_text = "OK"
    elif status == "warning":
        status_text = "WARN"
    else:
        status_text = "ALRM"
    oled.text(f"ST:{status_text}", 64, 24)

    # 第6行：从机信息
    if slave_data_manager and slave_data_manager.slave_data:
        online_count = sum(1 for info in slave_data_manager.slave_devices.values() if info['status'] == 'online')
        oled.text(f"SL:{online_count}", 0, 32)
    else:
        oled.text("SL:0", 0, 32)

    # 第7行：运行时间
    current_time = time.ticks_ms()
    time_seconds = (current_time // 1000) % 60
    oled.text(f"T:{time_seconds}s", 64, 32)

    # 第8行：从机火焰数据（如果有）
    if slave_data_manager and slave_data_manager.slave_data:
        first_slave_id = list(slave_data_manager.slave_data.keys())[0]
        slave_data = slave_data_manager.slave_data[first_slave_id]
        slave_flame = min(slave_data.get('flame_analog', 0), 999)
        oled.text(f"SF:{slave_flame}", 0, 40)

    # 第9行：从机烟雾数据（如果有）
    if slave_data_manager and slave_data_manager.slave_data:
        slave_mq2 = min(slave_data.get('mq2_analog', 0), 999)
        oled.text(f"SM:{slave_mq2}", 64, 40)

    oled.show()

def update_oled_simple(title, line1="", line2="", line3=""):
    """简单的OLED显示函数"""
    if oled is None:
        return  # OLED不可用，直接返回

    oled.fill(0)
    oled.text(title, 0, 0)
    if line1:
        oled.text(line1, 0, 16)
    if line2:
        oled.text(line2, 0, 32)
    if line3:
        oled.text(line3, 0, 48)
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

    def check_danger(self, flame_analog, mq2_analog, mq2_digital, temperature, light_level):
        """检查危险情况"""
        danger_detected = False
        danger_reason = ""

        # 检查火焰
        if flame_analog is not None and flame_analog < 500:
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

        # 检查光照
        elif light_level is not None and light_level > 120:
            danger_detected = True
            danger_reason = "光照警报"

        # 处理警报状态
        current_time = time.time()
        if danger_detected:
            # 不重置计数，继续累计
            self.last_alert_time = current_time
            self.alert_count += 1

            print(f"📊 警报计数: {self.alert_count}/3, 原因: {danger_reason}")

            # 连续3次警报才启动舵机
            if self.alert_count >= 3:
                if not self.servo_active:
                    self.set_servo_angle(SERVO_ALERT_ANGLE)
                    self.servo_active = True
                    print(f"🚨 危险！{danger_reason} - 启动舵机！")
                    return "危险警报", danger_reason
                else:
                    # 舵机已经启动，继续显示警报状态
                    return "危险警报", danger_reason
            else:
                return "警告中", f"{danger_reason}({self.alert_count}/3)"
        else:
            # 只有当环境真正正常（且舵机已启动）时才重置计数和关闭舵机
            if current_time - self.last_alert_time > 3:
                # 只有在舵机已经启动且环境正常超过3秒才重置
                if self.servo_active:
                    self.alert_count = 0
                    self.set_servo_angle(SERVO_SAFE_ANGLE)
                    self.servo_active = False
                    print("✅ 环境恢复正常 - 舵机关闭")
                    return "恢复正常", "环境正常"
                else:
                    # 舵机未启动，正常计数
                    pass

        return "正常", "环境正常"

# ==================== 主程序 ====================
def main():
    print("🚀 ESP32火灾报警系统启动")
    print("=" * 60)

    # 初始化系统状态
    system_status = SystemStatus()

    # 初始化从机数据管理器
    slave_manager = SlaveDataManager()

    # 初始化UDP服务器
    udp_server = UDPServer(port=8888)

    # 将UDP服务器引用传递给从机管理器
    slave_manager.udp_server = udp_server

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

    # 启动UDP服务器
    if wifi_connected:
        udp_success = udp_server.start()
        if udp_success:
            print(f"✅ UDP服务器启动成功，等待从机连接...")
        else:
            print("❌ UDP服务器启动失败")

    # 更新OLED显示
    update_oled_display(0, 0, 0, 0, 0, 0, 26, 50, 0, "Starting...", slave_manager)

    # 主循环
    print("📊 开始监测...")
    print("=" * 80)

    count = 0
    slave_check_count = 0
    while True:
        count += 1
        slave_check_count += 1

        # 读取传感器数据
        flame_analog, flame_digital = read_flame()
        mq2_analog, mq2_digital = read_mq2()
        sound_analog, sound_digital = read_sound()
        temperature, humidity = read_dht11()
        light_level = read_bh1750()

        # 检查危险状态（原有逻辑）
        status, reason = system_status.check_danger(flame_analog, mq2_analog, mq2_digital, temperature, light_level)

        # 火灾报警检测（MQTT使用）
        alarm_status = check_fire_alarm(flame_analog, mq2_analog, temperature, light_level)

        # 接收从机UDP数据
        if wifi_connected and udp_server.running:
            udp_data = udp_server.receive_data()
            if udp_data:
                json_data, client_ip, client_port = udp_data
                slave_manager.process_slave_data(json_data, client_ip, client_port)

        # 每30个循环检查一次从机状态并发送主机数据
        if slave_check_count >= 30:
            offline_count = slave_manager.check_slave_status()
            if offline_count > 0:
                print(f"⚠️  有{offline_count}个从机离线")

            # 发送主机数据到从机
            if slave_manager.master_data and slave_manager.slave_devices:
                udp_server.send_master_data_to_slaves(slave_manager.slave_devices, slave_manager.master_data)

            slave_check_count = 0

        # 确定传感器状态
        if flame_analog < 500:
            flame_status = "alarm"
        elif flame_analog < 1000:
            flame_status = "warning"
        else:
            flame_status = "normal"

        if mq2_analog < 1000:
            mq2_status = "alarm"
        elif mq2_analog < 1200:
            mq2_status = "warning"
        else:
            mq2_status = "normal"

        # 更新主机数据到从机管理器
        slave_manager.update_master_data(flame_analog, flame_status, mq2_analog, mq2_status, temperature, humidity, status)

        # 显示数据
        sound_str = f"{sound_analog}" if sound_analog is not None else "N/A"
        light_str = f"{light_level}" if light_level is not None else "N/A"
        print(f"[{count:3d}] 火焰:{flame_analog},{flame_digital} | 烟雾:{mq2_analog},{mq2_digital} | 声音:{sound_str},{sound_digital} | 温度:{temperature}°C | 湿度:{humidity}% | 光照:{light_str}lux | {status} | {reason} | MQTT:{alarm_status}")

        # 更新OLED显示
        oled_status = f"{status}/{alarm_status}"[:10]  # 显示两种状态
        update_oled_display(flame_analog, flame_digital, mq2_analog, mq2_digital, sound_analog, sound_digital, temperature, humidity, light_level, oled_status, slave_manager)

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

                # 发送从机数据（如果有）
                global pending_slave_mqtt_data
                if pending_slave_mqtt_data:
                    try:
                        slave_topic = f"esp32/{pending_slave_mqtt_data['slave_id']}/data/json"
                        if mqtt_client.publish(slave_topic, json.dumps(pending_slave_mqtt_data)):
                            print(f"📤 从机MQTT数据已发送: {pending_slave_mqtt_data['slave_id']}")
                        else:
                            print(f"❌ 从机MQTT发送失败: {pending_slave_mqtt_data['slave_id']}")

                        # 清空待发送数据
                        pending_slave_mqtt_data = None
                    except Exception as e:
                        print(f"❌ 从机MQTT发送异常: {e}")

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