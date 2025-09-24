'''
MQTT通信测试文件 - 基于main.py中的SimpleMQTTClient实现
测试ESP32到MQTT Broker的连接和数据发布
'''

from machine import Pin, SoftI2C
import time
import json
import network
import socket
import ssd1306

# ==================== 常量配置 ====================
DEVICE_ID = "esp32_mqtt_test_01"

# WiFi配置 (与main.py相同)
WIFI_SSID = "syh2031"
WIFI_PASSWORD = "12345678"

# MQTT配置 - 使用main.py中的公网端口映射
MQTT_SERVER = "22.tcp.cpolar.top"
MQTT_PORT = 10020

# OLED配置 (与从机相同)
OLED_SDA = 26  # OLED SDA引脚
OLED_SCL = 25  # OLED SCL引脚

# ==================== SimpleMQTTClient类 (从main.py复制) ====================
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

    def disconnect(self):
        """断开MQTT连接"""
        if self.sock:
            try:
                self.sock.send(b"\xE0\x00")  # DISCONNECT
                self.sock.close()
            except:
                pass
        self.connected = False
        print("MQTT连接已断开")

# ==================== 网络连通性测试函数 (从main.py复制) ====================
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

# ==================== OLED显示函数 ====================
def oled_show_message(title, line1="", line2="", line3=""):
    """在OLED上显示消息"""
    global oled
    if not oled:
        return

    try:
        oled.fill(0)
        oled.text(title, 0, 0)
        if line1:
            oled.text(line1, 0, 16)
        if line2:
            oled.text(line2, 0, 32)
        if line3:
            oled.text(line3, 0, 48)
        oled.show()
    except Exception as e:
        print(f"❌ OLED显示失败: {e}")

# ==================== 主测试函数 ====================
def main():
    """主测试函数"""
    print("🔧 MQTT通信测试开始")
    print("=" * 50)

    # 初始化OLED
    global oled
    try:
        i2c = SoftI2C(scl=Pin(OLED_SCL), sda=Pin(OLED_SDA))
        oled_width = 128
        oled_height = 64
        oled = ssd1306.SSD1306_I2C(oled_width, oled_height, i2c)
        oled.fill(0)
        oled.text("MQTT Test", 0, 0)
        oled.text("Starting...", 0, 16)
        oled.show()
        print("✅ OLED初始化成功")
    except Exception as e:
        print(f"❌ OLED初始化失败: {e}")
        oled = None

    # 连接WiFi
    oled_show_message("WiFi连接中...")
    print(f"📡 连接WiFi: {WIFI_SSID}")

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
        print(f"✅ WiFi连接成功!")
        print(f"   IP: {ip_info[0]}")
        print(f"   网关: {ip_info[2]}")
        oled_show_message("WiFi已连接", ip_info[0][:12])
        wifi_connected = True
    else:
        print("❌ WiFi连接失败")
        oled_show_message("WiFi失败", "测试退出")
        return

    # 网络诊断
    print("\n🔍 网络诊断开始...")
    oled_show_message("网络诊断中...")

    print(f"   ESP32 IP: {ip_info[0]}")
    print(f"   网关: {ip_info[2]}")
    print(f"   MQTT服务器: {MQTT_SERVER}")

    # 测试网络路由
    routing_ok = test_network_routing(ip_info[2], MQTT_SERVER)

    # 测试网络连通性
    print(f"\n🔍 测试到 {MQTT_SERVER}:{MQTT_PORT} 的连通性...")
    can_connect, error = test_network_connectivity(MQTT_SERVER, MQTT_PORT)

    if can_connect:
        print("✅ 网络连通性正常")
        oled_show_message("网络正常", "连接MQTT...")
    else:
        print(f"❌ 网络连通性测试失败: {error}")
        oled_show_message("网络异常", "测试失败")
        if "Host is unreachable" in error or "EHOSTUNREACH" in error:
            print("🔧 解决建议:")
            print("   1. 检查MQTT服务器IP地址是否正确")
            print("   2. 确保MQTT服务器在同一网络")
            print("   3. 检查路由器配置")
            print("   4. 检查防火墙设置")
        return

    # 创建MQTT客户端并连接
    oled_show_message("连接MQTT...")
    mqtt_client = SimpleMQTTClient(DEVICE_ID, MQTT_SERVER, MQTT_PORT)

    if mqtt_client.connect():
        oled_show_message("MQTT已连接", "开始测试")
        print("✅ MQTT连接成功，开始测试...")
    else:
        oled_show_message("MQTT失败", "测试退出")
        print("❌ MQTT连接失败，测试退出")
        return

    # 发送测试消息
    test_messages = [
        {
            "type": "test_message",
            "device_id": DEVICE_ID,
            "message": "Hello MQTT!",
            "timestamp": time.time()
        },
        {
            "type": "sensor_data",
            "device_id": DEVICE_ID,
            "flame": 1500,
            "smoke": 2000,
            "temperature": 25.6,
            "humidity": 65.2,
            "light": 150,
            "status": "normal",
            "timestamp": time.time()
        },
        {
            "type": "alert_test",
            "device_id": DEVICE_ID,
            "alert_type": "test",
            "level": "info",
            "message": "This is a test alert",
            "timestamp": time.time()
        }
    ]

    topics = [
        f"esp32/{DEVICE_ID}/data/json",
        f"esp32/{DEVICE_ID}/status/online",
        f"esp32/{DEVICE_ID}/alert/test",
        f"esp32/{DEVICE_ID}/heartbeat"
    ]

    # 测试消息发布
    print("\n📤 开始MQTT消息发布测试...")
    success_count = 0
    total_count = 0

    for i, message in enumerate(test_messages):
        for j, topic in enumerate(topics):
            total_count += 1
            print(f"\n--- 测试 {total_count}/{len(test_messages) * len(topics)} ---")
            print(f"主题: {topic}")
            print(f"消息: {message}")

            try:
                # 更新OLED显示
                oled_show_message(f"发送 {total_count}", f"主题 {j+1}")

                # 发布消息
                if mqtt_client.publish(topic, json.dumps(message)):
                    success_count += 1
                    print("✅ 消息发布成功")
                    oled_show_message(f"发送 {total_count}", "成功")
                else:
                    print("❌ 消息发布失败")
                    oled_show_message(f"发送 {total_count}", "失败")

                # 等待一下
                time.sleep(1)

            except Exception as e:
                print(f"❌ 发布异常: {e}")
                oled_show_message("发送异常", str(e)[:10])

    # 显示测试结果
    print(f"\n📊 测试结果:")
    print(f"   总计: {total_count}")
    print(f"   成功: {success_count}")
    print(f"   失败: {total_count - success_count}")
    print(f"   成功率: {success_count/total_count*100:.1f}%")

    if success_count == total_count:
        oled_show_message("测试完成", "全部成功! 🎉")
        print("🎉 所有测试通过!")
    else:
        oled_show_message("测试完成", f"{success_count}/{total_count}")
        print("⚠️ 部分测试失败")

    # 断开连接
    print("\n🔌 断开MQTT连接...")
    mqtt_client.disconnect()
    oled_show_message("MQTT已断开", "测试结束")

    print("✅ MQTT通信测试完成")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n测试被中断")
    except Exception as e:
        print(f"❌ 测试过程中出现错误: {e}")
        oled_show_message("测试错误", "请重试")