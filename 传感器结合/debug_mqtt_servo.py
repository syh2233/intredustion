"""
调试版MQTT舵机控制 - 添加详细MQTT调试信息
"""

import time
import network
import socket
from machine import Pin, PWM
import ujson

# 配置
WIFI_SSID = "syh2031"
WIFI_PASSWORD = "12345678"
MQTT_SERVER = "22.tcp.cpolar.top"
MQTT_PORT = 11390
DEVICE_ID = "esp32_fire_alarm_01"
SERVO_PIN = 15

class DebugMQTT:
    def __init__(self, client_id, server, port):
        self.client_id = client_id
        self.server = server
        self.port = port
        self.sock = None
        self.connected = False
        self.last_ping = 0
        self.subscribe_topic = None

    def connect(self):
        """连接到MQTT服务器"""
        try:
            print(f"📡 正在连接MQTT: {self.server}:{self.port}")

            self.sock = socket.socket()
            self.sock.settimeout(15)
            addr = socket.getaddrinfo(self.server, self.port)[0][-1]
            self.sock.connect(addr)
            print("TCP连接成功")

            # 构建MQTT CONNECT消息
            protocol_name = b"MQTT"
            protocol_level = 4
            flags = 0x02
            keep_alive = 30

            var_header = bytearray()
            var_header.append(0)
            var_header.append(len(protocol_name))
            var_header.extend(protocol_name)
            var_header.append(protocol_level)
            var_header.append(flags)
            var_header.append(keep_alive >> 8)
            var_header.append(keep_alive & 0xFF)

            payload = bytearray()
            client_id_bytes = self.client_id.encode()
            payload.append(len(client_id_bytes) >> 8)
            payload.append(len(client_id_bytes) & 0xFF)
            payload.extend(client_id_bytes)

            remaining_length = len(var_header) + len(payload)

            connect_msg = bytearray()
            connect_msg.append(0x10)
            connect_msg.append(remaining_length)
            connect_msg.extend(var_header)
            connect_msg.extend(payload)

            print(f"📤 发送CONNECT包，长度: {len(connect_msg)}")
            self.sock.send(connect_msg)

            response = self.sock.recv(1024)
            print(f"📥 CONNACK响应: {response}")

            if len(response) >= 4 and response[0] == 0x20 and response[3] == 0x00:
                self.connected = True
                self.last_ping = time.time()
                print("✅ MQTT连接成功!")
                return True
            else:
                return_code = response[3] if len(response) > 3 else 255
                print(f"❌ MQTT连接失败，错误码: {return_code}")
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

    def subscribe(self, topic):
        """订阅MQTT主题 - 调试版本"""
        try:
            if not self.connected:
                return False

            print(f"📋 准备订阅主题: {topic}")
            self.subscribe_topic = topic

            # 构建SUBSCRIBE消息
            topic_bytes = topic.encode()
            topic_len = len(topic_bytes)
            packet_id = 1

            subscribe_msg = bytearray()
            subscribe_msg.append(0x82)

            remaining_len = 2 + 2 + topic_len + 1
            if remaining_len < 128:
                subscribe_msg.append(remaining_len)
            else:
                subscribe_msg.append(0x81)
                subscribe_msg.append(remaining_len - 128)

            subscribe_msg.append(packet_id >> 8)
            subscribe_msg.append(packet_id & 0xFF)
            subscribe_msg.append(topic_len >> 8)
            subscribe_msg.append(topic_len & 0xFF)
            subscribe_msg.extend(topic_bytes)
            subscribe_msg.append(0x00)

            print(f"📤 发送SUBSCRIBE包，长度: {len(subscribe_msg)}")
            print(f"📤 包内容: {[hex(b) for b in subscribe_msg]}")

            self.sock.send(subscribe_msg)

            # 等待SUBACK
            self.sock.settimeout(5)
            try:
                suback = self.sock.recv(1024)
                print(f"📥 SUBACK响应: {suback}")
                if suback and len(suback) >= 5:
                    if suback[0] == 0x90 and suback[4] == 0x00:
                        print("✅ 订阅确认成功!")
                        return True
                    else:
                        print(f"❌ 订阅失败，响应: {suback}")
                        return False
                else:
                    print("❌ 无效的SUBACK响应")
                    return False
            except OSError:
                print("⏰ SUBACK超时")
                return False

        except Exception as e:
            print(f"❌ 订阅失败: {e}")
            return False

    def check_msg(self):
        """检查接收到的MQTT消息 - 调试版本"""
        try:
            if not self.connected or not self.sock:
                return None

            self.sock.settimeout(0.1)
            try:
                data = self.sock.recv(512)
                if not data:
                    return None

                print(f"📥 收到原始数据: {data} (长度: {len(data)})")
                print(f"📥 十六进制: {[hex(b) for b in data]}")

                if len(data) < 2:
                    return None

                msg_type = (data[0] & 0xF0) >> 4
                print(f"📋 消息类型: {msg_type}")

                if msg_type == 3:  # PUBLISH
                    # 解析剩余长度
                    remaining_len = data[1]
                    pos = 2
                    if remaining_len >= 128:
                        remaining_len = data[2]
                        pos = 3
                        print(f"📋 扩展长度解码: {remaining_len}")

                    print(f"📋 剩余长度: {remaining_len}")

                    # 解析主题长度
                    if pos + 1 >= len(data):
                        return None

                    topic_len = (data[pos] << 8) | data[pos+1]
                    pos += 2
                    print(f"📋 主题长度: {topic_len}")

                    # 解析主题
                    if pos + topic_len > len(data):
                        return None

                    topic = data[pos:pos+topic_len].decode()
                    pos += topic_len
                    print(f"📋 主题: {topic}")

                    # 解析消息内容
                    message_len = remaining_len - topic_len - 2
                    if pos + message_len > len(data):
                        return None

                    message = data[pos:pos+message_len].decode()
                    print(f"📋 消息内容: {message}")

                    # 检查是否匹配订阅的主题
                    if self.subscribe_topic and topic == self.subscribe_topic:
                        print("✅ 匹配订阅主题!")
                        return message
                    else:
                        print(f"⚠️ 主题不匹配，订阅的: {self.subscribe_topic}, 收到的: {topic}")
                        return None

                elif msg_type == 9:  # SUBACK
                    print("📋 收到SUBACK消息")
                elif msg_type == 12:  # PINGRESP
                    print("📋 收到PINGRESP消息")
                else:
                    print(f"📋 收到其他类型消息: {msg_type}")

            except OSError:
                return None
        except Exception as e:
            print(f"❌ 检查消息异常: {e}")
            self.connected = False
            return None

class SimpleServo:
    def __init__(self, pin):
        self.pin = PWM(Pin(pin), freq=50)
        self.pin.duty(0)
        self.angle = 0
        print("🎯 舵机初始化完成")

    def set_angle(self, angle):
        angle = max(0, min(180, angle))
        duty = 25 + (angle * 103) // 180
        self.pin.duty(duty)
        self.angle = angle
        print(f"🎯 舵机实际转动到: {angle}° (占空比: {duty})")

def connect_wifi():
    """连接WiFi"""
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)

    if not wlan.isconnected():
        print("🔗 连接WiFi...")
        wlan.connect(WIFI_SSID, WIFI_PASSWORD)

        for i in range(20):
            if wlan.isconnected():
                break
            time.sleep(0.5)

    if wlan.isconnected():
        ip_info = wlan.ifconfig()
        print(f"✅ WiFi连接成功! IP: {ip_info[0]}")
        return True
    else:
        print("❌ WiFi连接失败")
        return False

def check_command_file():
    """检查是否有临时命令文件"""
    try:
        with open('servo_command.txt', 'r') as f:
            command = f.read().strip()
        # 删除文件
        import os
        os.remove('servo_command.txt')
        return command
    except:
        return None

def main():
    print("=== ESP32 MQTT舵机控制调试程序 ===")
    print("🔍 支持临时命令文件和MQTT控制")
    print()

    if not connect_wifi():
        print("❌ WiFi连接失败，但仍可处理临时命令文件")
        # WiFi失败也要继续，因为可能处理临时文件

    servo = SimpleServo(SERVO_PIN)

    mqtt_client = None
    mqtt_connected = False

    # 尝试连接MQTT
    try:
        mqtt_client = DebugMQTT(DEVICE_ID, MQTT_SERVER, MQTT_PORT)
        mqtt_connected = mqtt_client.connect()

        if mqtt_connected:
            control_topic = f"esp32/{DEVICE_ID}/control"
            if mqtt_client.subscribe(control_topic):
                print(f"🎯 开始监听MQTT控制命令...")
            else:
                print("⚠️ MQTT订阅失败，但仍可处理临时命令文件")
    except Exception as e:
        print(f"⚠️ MQTT连接失败: {e}")
        print("🔧 仅支持临时命令文件模式")

    loop_count = 0
    last_activity = time.time()
    last_file_check = time.time()

    try:
        while True:
            loop_count += 1
            current_time = time.time()

            # 检查临时命令文件（每5秒检查一次）
            if current_time - last_file_check > 5:
                file_command = check_command_file()
                if file_command:
                    print(f"📁 从临时文件读取命令: {file_command}")
                    last_activity = current_time

                    try:
                        command = ujson.loads(file_command)
                        device = command.get('device', '')
                        action = command.get('action', '')

                        print(f"🎛 解析文件命令 - 设备: {device}, 动作: {action}")

                        if device == 'servo':
                            if action == 'on':
                                servo.set_angle(180)
                                print("✅ 舵机已开启")
                            elif action == 'off':
                                servo.set_angle(90)
                                print("✅ 舵机已关闭")
                            elif action == 'test':
                                angle = command.get('angle', 0)
                                servo.set_angle(angle)
                                print(f"✅ 舵机测试 - 转到{angle}度")
                            else:
                                print(f"⚠️ 未知的舵机动作: {action}")
                        else:
                            print(f"⚠️ 非舵机控制命令: {device}")

                    except Exception as e:
                        print(f"❌ 临时文件JSON解析失败: {e}")

                last_file_check = current_time

            # 检查MQTT消息（如果连接成功）
            if mqtt_connected and mqtt_client:
                message = mqtt_client.check_msg()
                if message:
                    print(f"📨 收到MQTT消息: {message}")
                    last_activity = current_time

                    try:
                        command = ujson.loads(message)
                        device = command.get('device', '')
                        action = command.get('action', '')

                        print(f"🎛 解析MQTT命令 - 设备: {device}, 动作: {action}")

                        if device == 'servo':
                            if action == 'on':
                                servo.set_angle(180)
                                print("✅ 舵机已开启")
                            elif action == 'off':
                                servo.set_angle(90)
                                print("✅ 舵机已关闭")
                            elif action == 'test':
                                angle = command.get('angle', 0)
                                servo.set_angle(angle)
                                print(f"✅ 舵机测试 - 转到{angle}度")
                            else:
                                print(f"⚠️ 未知的舵机动作: {action}")
                        else:
                            print(f"⚠️ 非舵机控制命令: {device}")

                    except Exception as e:
                        print(f"❌ MQTT JSON解析失败: {e}")

            # 每60次循环检查状态
            if loop_count % 60 == 0:
                current_time = time.time()
                if current_time - last_activity > 120:  # 120秒无活动
                    print("⚠️ 120秒未收到任何命令，程序运行正常")
                    last_activity = current_time

            time.sleep(0.5)

    except KeyboardInterrupt:
        print("\n🏠 用户中断，程序退出")
    except Exception as e:
        print(f"\n❌ 程序异常: {e}")

if __name__ == "__main__":
    main()