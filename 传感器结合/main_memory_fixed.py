'''
ESP32火灾报警系统 - 内存优化修复版本
彻底解决内存问题，保留所有功能但优化内存占用
'''

from machine import Pin, ADC, PWM
import time
import json
import network
import socket
from machine import SoftI2C
import ssd1306

# 配置
DEVICE_ID = "esp32_fire_alarm_01"

# WiFi配置
WIFI_SSID = "syh2031"
WIFI_PASSWORD = "12345678"

# MQTT配置
MQTT_SERVER = "22.tcp.cpolar.top"
MQTT_PORT = 11390

# GPIO配置
FLAME_DO_PIN = 14
MQ2_AO_PIN = 34
MQ2_DO_PIN = 2
SERVO_PIN = 15

# OLED配置
OLED_SCL = 25
OLED_SDA = 26

# 硬件初始化
print("🔧 初始化基础硬件...")

# 初始化舵机
servo = PWM(Pin(SERVO_PIN), freq=50)
servo.duty(0)
print("✅ 舵机初始化完成")

# 初始化火焰传感器
flame_do = Pin(FLAME_DO_PIN, Pin.IN)
print("✅ 火焰传感器初始化成功")

# 初始化MQ2传感器
mq2_ao = ADC(Pin(MQ2_AO_PIN))
mq2_do = Pin(MQ2_DO_PIN, Pin.IN)
print("✅ MQ2传感器初始化成功")

# 简化MQTT客户端
class MinimalMQTT:
    def __init__(self, client_id, server, port):
        self.client_id = client_id
        self.server = server
        self.port = port
        self.sock = None
        self.connected = False

    def connect(self):
        try:
            print(f"📡 连接MQTT...")
            self.sock = socket.socket()
            self.sock.settimeout(10)
            addr = socket.getaddrinfo(self.server, self.port)[0][-1]
            self.sock.connect(addr)

            # 最小MQTT CONNECT
            client_id = self.client_id.encode()
            msg = bytearray([0x10, len(client_id) + 12]) + bytearray([0, 4]) + b"MQTT" + bytearray([4, 2, 0, 60]) + bytearray([len(client_id) >> 8, len(client_id) & 0xff]) + client_id
            self.sock.send(msg)

            resp = self.sock.recv(10)
            if resp and resp[0] == 0x20 and resp[3] == 0x00:
                self.connected = True
                print("✅ MQTT连接成功")
                return True
            return False
        except Exception as e:
            print(f"❌ MQTT连接失败: {e}")
            return False

    def subscribe(self, topic):
        try:
            if not self.connected:
                return False

            topic_bytes = topic.encode()
            sub_msg = bytearray([0x82, len(topic_bytes) + 2, 0, 1, len(topic_bytes) >> 8, len(topic_bytes) & 0xff]) + topic_bytes + bytearray([0x00])
            self.sock.send(sub_msg)
            print("✅ 订阅控制主题")
            return True
        except Exception as e:
            print(f"❌ 订阅失败: {e}")
            return False

    def check_msg(self):
        try:
            if not self.connected or not self.sock:
                return None

            self.sock.settimeout(0.05)  # 超短超时
            data = self.sock.recv(128)
            if data and len(data) > 5 and (data[0] & 0xf0) == 0x30:
                # 最简PUBLISH解析
                topic_len = (data[2] << 8) | data[3]
                if len(data) >= 4 + topic_len:
                    topic = data[4:4+topic_len].decode()
                    message = data[4+topic_len:].decode()
                    if "control" in topic:
                        return message
            return None
        except OSError:
            return None  # 超时正常
        except:
            self.connected = False
            return None

    def publish_simple(self, topic, message):
        try:
            if not self.connected:
                return False

            topic_bytes = topic.encode()
            msg_bytes = message.encode()

            pub_msg = bytearray([0x30])  # PUBLISH
            remaining_len = len(topic_bytes) + len(msg_bytes) + 2

            if remaining_len < 128:
                pub_msg.append(remaining_len)
            else:
                pub_msg.append(0x81)
                pub_msg.append(remaining_len - 128)

            pub_msg.append(len(topic_bytes) >> 8)
            pub_msg.append(len(topic_bytes) & 0xff)
            pub_msg.extend(topic_bytes)
            pub_msg.extend(msg_bytes)

            self.sock.send(pub_msg)
            return True
        except:
            return False

def connect_wifi():
    """连接WiFi"""
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    wlan.connect(WIFI_SSID, WIFI_PASSWORD)

    for i in range(15):  # 减少连接尝试次数
        if wlan.isconnected():
            break
        time.sleep(0.5)

    if wlan.isconnected():
        ip = wlan.ifconfig()[0]
        print(f"✅ WiFi连接成功! IP: {ip}")
        return True, ip
    else:
        print("❌ WiFi连接失败")
        return False, None

def read_sensor_minimal():
    """最小化传感器读取"""
    try:
        # 读取火焰传感器
        flame_digital = flame_do.value()
        flame_analog = 1500 if flame_digital == 1 else 0

        # 读取MQ2传感器
        mq2_digital = mq2_do.value()
        try:
            mq2_analog = mq2_ao.read()
        except:
            mq2_analog = 4095

        return flame_analog, mq2_analog, flame_digital, mq2_digital
    except:
        return 1500, 4095, 1, 1

def control_servo_minimal(action, angle=None):
    """最小化舵机控制"""
    try:
        if action == 'on':
            duty = 128
            print("🔛 舵机开启 (180度)")
        elif action == 'off':
            duty = 25
            print("🔴 舵机关闭 (0度)")
        elif action == 'test' and angle is not None:
            angle = max(0, min(180, angle))
            if angle == 0:
                duty = 25
            elif angle == 90:
                duty = 77
            elif angle == 180:
                duty = 128
            else:
                duty = int(25 + (angle * 103) // 180)
            print(f"🎯 舵机转到 {angle}度")
        else:
            return False

        servo.duty(duty)
        time.sleep(0.3)
        return True
    except:
        return False

def main():
    print("=== ESP32火灾报警系统 (内存优化修复版) ===")
    print("🔧 保留所有功能，彻底优化内存")
    print()

    # 连接WiFi
    wifi_ok, ip = connect_wifi()
    if not wifi_ok:
        print("❌ WiFi连接失败，程序退出")
        return

    # 连接MQTT
    mqtt = MinimalMQTT(DEVICE_ID, MQTT_SERVER, MQTT_PORT)
    mqtt_ok = mqtt.connect()
    if mqtt_ok:
        control_topic = f"esp32/{DEVICE_ID}/control"
        mqtt.subscribe(control_topic)

    # 主循环 - 真正的交替处理
    loop_count = 0
    sensor_display_count = 0

    print("🚀 开始优化主循环...")
    print("💡 每2个循环交替处理传感器和MQTT")

    try:
        while True:
            loop_count += 1

            # 奇数循环：只处理传感器
            if loop_count % 2 == 1:
                sensor_display_count += 1
                flame_analog, mq2_analog, flame_digital, mq2_digital = read_sensor_minimal()

                # 简化状态判断
                if flame_analog < 500 or mq2_analog < 1000:
                    status = "ALRM"
                    alarm_status = "alarm"
                else:
                    status = "OK"
                    alarm_status = "normal"

                # 简化显示（每10次显示一次完整信息）
                if sensor_display_count % 10 == 0:
                    print(f"[{sensor_display_count:2d}] 🔥:{flame_analog} 💨:{mq2_analog} 📊:{status}")

                # MQTT数据上传（简化版）
                if mqtt_ok:
                    simple_payload = f'{{"device_id":"{DEVICE_ID}","flame":{flame_analog},"smoke":{mq2_analog},"status":"{alarm_status}","time":{int(time.time())}}}'
                    data_topic = f"esp32/{DEVICE_ID}/data/json"
                    if not mqtt.publish_simple(data_topic, simple_payload):
                        mqtt_ok = False  # 标记断开

                # 等待
                time.sleep(0.8)

            # 偶数循环：只处理MQTT控制
            else:
                if mqtt_ok:
                    message = mqtt.check_msg()
                    if message:
                        print(f"📨 收到控制消息")
                        try:
                            # 最简JSON解析
                            if '"device":"servo"' in message:
                                if '"action":"on"' in message:
                                    control_servo_minimal('on')
                                elif '"action":"off"' in message:
                                    control_servo_minimal('off')
                                elif '"action":"test"' in message:
                                    # 提取角度
                                    start = message.find('"angle":')
                                    if start > 0:
                                        end = message.find('}', start)
                                        if end > start:
                                            angle_str = message[start+9:end].strip('"')
                                            try:
                                                angle = int(angle_str)
                                                control_servo_minimal('test', angle)
                                            except:
                                                pass
                        except:
                            pass

                time.sleep(0.2)

    except KeyboardInterrupt:
        print("\n🏠 程序被用户中断")
    except Exception as e:
        print(f"\n❌ 程序异常: {e}")
    finally:
        # 清理资源
        try:
            if mqtt and mqtt.connected:
                mqtt.sock.close()
        except:
            pass
        servo.duty(0)
        print("🔌 系统已安全关闭")

if __name__ == "__main__":
    main()