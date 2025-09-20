import machine
import time
import network
import socket
import ujson
import config
import random

# 初始化Wi-Fi
wlan = network.WLAN(network.STA_IF)

# 连接Wi-Fi（使用工作版本的方法）
def connect_wifi():
    print("📡 正在连接WiFi...")
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)

    if not wlan.isconnected():
        print(f"连接到: {config.WIFI_SSID}")
        wlan.connect(config.WIFI_SSID, config.WIFI_PASSWORD)

        # 等待连接
        timeout = 0
        while not wlan.isconnected() and timeout < 30:
            time.sleep(1)
            timeout += 1
            print(".", end="")

        print()

        if wlan.isconnected():
            print("✅ WiFi连接成功!")
            print(f"IP地址: {wlan.ifconfig()[0]}")
            return True
        else:
            print("❌ WiFi连接失败!")
            return False
    else:
        print("✅ WiFi已连接")
        print(f"IP地址: {wlan.ifconfig()[0]}")
        return True

# 生成模拟传感器数据
def generate_sensor_data():
    # 生成随机但合理的传感器数据
    flame_value = random.randint(800, 2000)  # 火焰传感器值
    smoke_value = random.randint(20, 150)    # 烟雾传感器值
    temperature = random.randint(20, 45)     # 温度（摄氏度）
    humidity = random.randint(30, 80)        # 湿度（百分比）

    return {
        "flame": flame_value,
        "smoke": smoke_value,
        "temperature": temperature,
        "humidity": humidity,
        "timestamp": time.time()
    }

# 火灾检测算法
def check_fire_alarm(data):
    if not data:
        return "normal"

    flame = data["flame"]
    smoke = data["smoke"]
    temp = data["temperature"]

    # 警报条件（任一满足即触发）
    if flame < 1000 or smoke > 100 or temp > 40:
        return "alarm"
    # 警告条件（任一满足即触发）
    elif flame < 1100 or smoke > 50 or temp > 35:
        return "warning"
    else:
        return "normal"

# 简化的MQTT客户端
class SimpleMQTTClient:
    def __init__(self, client_id, server, port):
        self.client_id = client_id
        self.server = server
        self.port = port
        self.sock = None
        self.connected = False
        self.last_ping = time.time()

    def connect(self):
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
        if not self.connected:
            return False

        try:
            # 检查是否需要发送PINGREQ
            current_time = time.time()
            if current_time - self.last_ping > 30:
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

    def disconnect(self):
        if self.sock and self.connected:
            try:
                self.sock.send(b"\xE0\x00")  # DISCONNECT
                self.sock.close()
            except:
                pass
            finally:
                self.connected = False

# MQTT客户端
mqtt_client = None

def connect_mqtt():
    global mqtt_client

    try:
        mqtt_client = SimpleMQTTClient(config.DEVICE_ID, config.MQTT_BROKER, config.MQTT_PORT)

        if mqtt_client.connect():
            print("✅ MQTT连接成功!")
            return True
        else:
            print("❌ MQTT连接失败!")
            return False

    except Exception as e:
        print(f"❌ MQTT连接异常: {e}")
        return False

# 发送数据到MQTT
def send_sensor_data(data, status):
    if not mqtt_client or not mqtt_client.connected:
        return False

    try:
        payload = {
            "device_id": config.DEVICE_ID,
            "flame": data["flame"],
            "smoke": data["smoke"],
            "temperature": data["temperature"],
            "humidity": data["humidity"],
            "status": status,
            "timestamp": data["timestamp"]
        }

        # 发送传感器数据
        topic = f"esp32/{config.DEVICE_ID}/data/json"
        if mqtt_client.publish(topic, ujson.dumps(payload)):
            print(f"📡 MQTT数据已发送")
        else:
            print(f"❌ MQTT发送失败")
            return False

        # 如果是警报状态，发送警报消息
        if status == "alarm":
            alert_msg = {
                "type": "fire",
                "level": "high",
                "data": payload,
                "message": "检测到火灾风险！"
            }
            mqtt_client.publish(f"esp32/{config.DEVICE_ID}/alert/fire", ujson.dumps(alert_msg))
        elif status == "warning":
            alert_msg = {
                "type": "warning",
                "level": "medium",
                "data": payload,
                "message": "环境异常警告"
            }
            mqtt_client.publish(f"esp32/{config.DEVICE_ID}/alert/warning", ujson.dumps(alert_msg))

        return True

    except Exception as e:
        print(f"❌ MQTT数据打包失败: {e}")
        return False

# 主循环
def main():
    print("ESP32火灾报警系统（模拟数据）启动...")

    # 连接Wi-Fi
    if not connect_wifi():
        print("无法连接Wi-Fi，系统退出")
        return

    # 连接MQTT
    if not connect_mqtt():
        print("无法连接MQTT，系统退出")
        return

    print("系统正常运行，发送模拟数据...")

    while True:
        try:
            # 生成模拟传感器数据
            sensor_data = generate_sensor_data()

            # 检测火灾状态
            status = check_fire_alarm(sensor_data)

            # 发送数据到MQTT
            send_sensor_data(sensor_data, status)

            # 打印调试信息
            print(f"状态: {status}, 火焰: {sensor_data['flame']}, 烟雾: {sensor_data['smoke']}, 温度: {sensor_data['temperature']}°C, 湿度: {sensor_data['humidity']}%")

            # 如果是警报状态，添加延迟演示效果
            if status == "alarm":
                print("⚠️  火灾警报！")
            elif status == "warning":
                print("⚠️  环境警告！")

            time.sleep(config.SENSOR_READ_INTERVAL)

        except Exception as e:
            print("主循环错误:", e)
            time.sleep(5)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("程序被中断")
        # 清理资源
        if mqtt_client:
            mqtt_client.publish(f"esp32/{config.DEVICE_ID}/status/online", "0", retain=True)
            mqtt_client.disconnect()
        print("系统已安全关闭")