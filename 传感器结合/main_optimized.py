'''
ESP32火灾报警系统 - 内存优化版本
传感器监测和MQTT消息处理交替进行，减少内存占用
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
OLED_WIDTH = 128
OLED_HEIGHT = 64

# 硬件初始化
print("🔧 初始化硬件...")

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

# 初始化OLED显示屏
try:
    i2c = SoftI2C(scl=Pin(OLED_SCL), sda=Pin(OLED_SDA), freq=400000)
    oled = ssd1306.SSD1306_I2C(OLED_WIDTH, OLED_HEIGHT, i2c)
    oled.fill(0)
    oled.text("ESP32 Alarm", 0, 0)
    oled.text("Ready...", 0, 16)
    oled.show()
    print("✅ OLED显示屏初始化成功")
except Exception as e:
    print(f"❌ OLED显示屏初始化失败: {e}")
    oled = None

# 简化MQTT客户端
class SimpleMQTT:
    def __init__(self, client_id, server, port):
        self.client_id = client_id
        self.server = server
        self.port = port
        self.sock = None
        self.connected = False

    def connect(self):
        try:
            print(f"📡 连接MQTT: {self.server}:{self.port}")
            self.sock = socket.socket()
            self.sock.settimeout(10)
            addr = socket.getaddrinfo(self.server, self.port)[0][-1]
            self.sock.connect(addr)

            # 简化MQTT CONNECT
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
            print("✅ MQTT订阅成功")
            return True
        except Exception as e:
            print(f"❌ MQTT订阅失败: {e}")
            return False

    def check_msg(self):
        try:
            if not self.connected or not self.sock:
                return None

            self.sock.settimeout(0.1)
            data = self.sock.recv(256)
            if data and len(data) > 5 and (data[0] & 0xf0) == 0x30:
                # 简化PUBLISH解析
                topic_len = (data[2] << 8) | data[3]
                if len(data) >= 4 + topic_len:
                    topic = data[4:4+topic_len].decode()
                    message = data[4+topic_len:].decode()
                    if "control" in topic:
                        return message
            return None
        except OSError:
            return None
        except Exception as e:
            print(f"❌ MQTT检查失败: {e}")
            self.connected = False
            return None

def connect_wifi():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    wlan.connect(WIFI_SSID, WIFI_PASSWORD)

    for i in range(20):
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

def read_sensors():
    """读取传感器数据 - 简化版本"""
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

        return flame_analog, flame_digital, mq2_analog, mq2_digital
    except:
        return 1500, 1, 4095, 1

def control_servo(action, angle=None):
    """控制舵机 - 简化版本"""
    try:
        if action == 'on':
            duty = 128  # 180度
            print("🔛 舵机开启 (180度)")
        elif action == 'off':
            duty = 25   # 0度
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
        time.sleep(0.5)
        return True
    except Exception as e:
        print(f"❌ 舵机控制失败: {e}")
        return False

def update_oled_simple(flame, mq2, status, servo_status):
    """简化OLED显示"""
    if oled is None:
        return

    try:
        oled.fill(0)
        oled.text("ALARM", 0, 0)
        oled.text(f"F:{flame}", 0, 16)
        oled.text(f"M:{mq2}", 64, 16)
        oled.text(f"ST:{status[:4]}", 0, 32)
        oled.text(f"SV:{servo_status[:3]}", 64, 32)
        oled.show()
    except:
        pass

def main():
    print("=== ESP32火灾报警系统 (内存优化版) ===")
    print("🔄 传感器监测和MQTT处理交替进行")
    print()

    # 连接WiFi
    wifi_ok, ip = connect_wifi()
    if not wifi_ok:
        print("❌ WiFi连接失败，程序退出")
        return

    # 连接MQTT
    mqtt = SimpleMQTT(DEVICE_ID, MQTT_SERVER, MQTT_PORT)
    mqtt_ok = mqtt.connect()
    if mqtt_ok:
        control_topic = f"esp32/{DEVICE_ID}/control"
        mqtt.subscribe(control_topic)

    # 主循环 - 交替处理
    loop_count = 0
    sensor_count = 0
    mqtt_count = 0

    print("🚀 开始主循环...")
    print("💡 奇数循环: 传感器监测，偶数循环: MQTT检查")

    try:
        while True:
            loop_count += 1

            # 奇数循环：处理传感器数据
            if loop_count % 2 == 1:
                sensor_count += 1
                flame_analog, flame_digital, mq2_analog, mq2_digital = read_sensors()

                # 简化状态判断
                if flame_analog < 500 or mq2_analog < 1000:
                    status = "ALARM"
                    system_status = "警报"
                else:
                    status = "OK"
                    system_status = "正常"

                # 简化OLED显示
                servo_status = "ON" if servo.duty() > 50 else "OFF"
                update_oled_simple(flame_analog, mq2_analog, status, servo_status)

                # 每10次传感器检查显示一次数据
                if sensor_count % 10 == 0:
                    print(f"[{sensor_count:2d}] 🔥火焰:{flame_analog} 💨烟雾:{mq2_analog} 📊状态:{system_status} 🎯舵机:{servo_status}")

                time.sleep(0.8)  # 传感器处理时间

            # 偶数循环：处理MQTT消息
            else:
                mqtt_count += 1
                if mqtt_ok:
                    message = mqtt.check_msg()
                    if message:
                        print(f"📨 收到MQTT控制消息")
                        try:
                            import ujson
                            cmd = ujson.loads(message)
                            device = cmd.get('device', '')
                            action = cmd.get('action', '')

                            if device == 'servo':
                                angle = cmd.get('angle', None)
                                if control_servo(action, angle):
                                    print(f"✅ 舵机命令执行成功: {action}" + (f" -> {angle}度" if angle else ""))
                                else:
                                    print(f"❌ 舵机命令执行失败: {action}")
                            else:
                                print(f"⚠️ 非舵机命令: {device}")

                        except Exception as e:
                            print(f"❌ MQTT消息处理失败: {e}")

                time.sleep(0.2)  # MQTT检查时间（较短）

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