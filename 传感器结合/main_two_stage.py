'''
ESP32火灾报警系统 - 两阶段处理版本
阶段1: 传感器读取+OLED显示+MQTT数据发送
阶段2: MQTT控制消息接收+舵机控制
减少同时运行的内存占用
'''

from machine import Pin, ADC, PWM
import time
import json
import network
import socket
from machine import SoftI2C
import ssd1306
import gc  # 垃圾回收

# 配置
DEVICE_ID = "esp32_fire_alarm_01"
WIFI_SSID = "syh2031"
WIFI_PASSWORD = "12345678"
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
print("🔧 阶段1: 基础硬件初始化...")

# 初始化火焰传感器
flame_do = Pin(FLAME_DO_PIN, Pin.IN)
print("✅ 火焰传感器初始化成功")

# 初始化MQ2传感器
mq2_ao = ADC(Pin(MQ2_AO_PIN))
mq2_do = Pin(MQ2_DO_PIN, Pin.IN)
print("✅ MQ2传感器初始化成功")

# 初始化舵机
servo = PWM(Pin(SERVO_PIN), freq=50)
servo.duty(0)
print("✅ 舵机初始化完成")

# 初始化OLED显示屏
try:
    i2c = SoftI2C(scl=Pin(OLED_SCL), sda=Pin(OLED_SDA), freq=400000)
    oled = ssd1306.SSD1306_I2C(OLED_WIDTH, OLED_HEIGHT, i2c)
    oled.fill(0)
    oled.text("Phase 1", 0, 16)
    oled.show()
    print("✅ OLED显示屏初始化成功")
    oled_available = True
except Exception as e:
    print(f"❌ OLED显示屏初始化失败: {e}")
    oled_available = False

# ==================== 阶段1: 传感器+OLED+MQTT ====================
class Phase1Processor:
    """阶段1处理器"""
    def __init__(self):
        self.phase1_active = True
        self.phase2_active = False

    def read_sensors(self):
        """读取传感器数据"""
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

            # DHT11模拟读取（简化版）
            temp = 25  # 默认25度
            hum = 60  # 默认60%

            # BH1750模拟读取（简化版）
            light = 100  # 默认100lux

            # 构建传感器数据
            sensor_data = {
                'flame_analog': flame_analog,
                'flame_digital': flame_digital,
                'mq2_analog': mq2_analog,
                'mq2_digital': mq2_digital,
                'temperature': temp,
                'humidity': hum,
                'light': light
            }

            # 打印传感器数据到日志
            print(f"🔥 阶段1传感器数据: 火焰={flame_analog}(数字:{flame_digital}) MQ2={mq2_analog}(数字:{mq2_digital}) 温度={temp}°C 湿度={hum}% 光照={light}lux")

            return sensor_data

        except Exception as e:
            print(f"❌ 传感器读取失败: {e}")
            return None

    def update_oled_display(self, sensor_data):
        """更新OLED显示 - 保持与main.py相同的格式"""
        if not oled_available:
            return

        try:
            oled.fill(0)

            # 第1行：标题
            oled.text("ALARM-P1", 0, 0)

            # 第2行：火焰和烟雾
            flame_val = min(sensor_data.get('flame_analog', 0), 999)
            mq2_val = min(sensor_data.get('mq2_analog', 0), 999)
            oled.text(f"F:{flame_val}", 0, 8)
            oled.text(f"M:{mq2_val}", 64, 8)

            # 第3行：温度和湿度
            temperature = sensor_data.get('temperature', 25)
            humidity = sensor_data.get('humidity', 60)
            oled.text(f"T:{temperature}", 0, 16)
            oled.text(f"H:{humidity}", 64, 16)

            # 第4行：光照
            light = sensor_data.get('light', 0)
            if light is not None:
                light_val = min(int(light), 999)
                oled.text(f"L:{light_val}", 0, 24)
            else:
                oled.text("L:---", 0, 24)

            # 第5行：系统状态
            flame_analog = sensor_data.get('flame_analog', 1500)
            mq2_analog = sensor_data.get('mq2_analog', 4095)
            if flame_analog < 500 or mq2_analog < 1000:
                status_text = "ALRM"
            else:
                status_text = "OK"
            oled.text(f"ST:{status_text}", 64, 24)

            # 第6行：循环计数
            oled.text(f"LP:{self.loop_count if hasattr(self, 'loop_count') else 0}", 0, 32)

            # 第7行：运行时间
            oled.text(f"PH:1", 64, 32)

            oled.show()
        except Exception as e:
            print(f"❌ OLED显示失败: {e}")

    def send_mqtt_data(self, sensor_data, alarm_status):
        """发送MQTT数据"""
        try:
            import ujson

            payload = {
                "device_id": DEVICE_ID,
                "flame": sensor_data.get('flame_analog', 0),
                "smoke": sensor_data.get('mq2_analog', 0),
                "temperature": sensor_data.get('temperature', 25),
                "humidity": sensor_data.get('humidity', 60),
                "light": sensor_data.get('light', 0),
                "status": alarm_status,
                "phase": 1,
                "timestamp": time.time()
            }

            topic = f"esp32/{DEVICE_ID}/data/json"
            message = ujson.dumps(payload)

            # 殀化的MQTT发送
            sock = socket.socket()
            sock.settimeout(5)
            addr = socket.getaddrinfo(MQTT_SERVER, MQTT_PORT)[0][-1]
            sock.connect(addr)

            # MQTT CONNECT
            client_id = DEVICE_ID.encode()
            connect_msg = bytearray([0x10, len(client_id) + 12]) + bytearray([0, 4]) + b"MQTT" + bytearray([4, 2, 0, 60]) + bytearray([len(client_id) >> 8, len(client_id) & 0xff]) + client_id
            sock.send(connect_msg)

            # 等待CONNACK
            resp = sock.recv(10)
            if resp and resp[0] == 0x20 and resp[3] == 0x00:
                print("✅ 阶段1 MQTT连接成功")

                # 发送数据
                topic_bytes = topic.encode()
                data_bytes = message.encode()

                pub_msg = bytearray([0x30])
                remaining_len = len(topic_bytes) + len(data_bytes) + 2

                if remaining_len < 128:
                    pub_msg.append(remaining_len)
                else:
                    pub_msg.append(0x81)
                    pub_msg.append(remaining_len - 128)

                pub_msg.append(len(topic_bytes) >> 8)
                pub_msg.append(len(topic_bytes) & 0xff)
                pub_msg.extend(topic_bytes)
                pub_msg.extend(data_bytes)

                sock.send(pub_msg)
                print("✅ 阶段1 MQTT数据发送")

                # 发送警报（如果需要）
                if alarm_status == "alarm":
                    alert_topic = f"esp32/{DEVICE_ID}/alert"
                    alert_msg = ujson.dumps({
                        "type": "fire",
                        "level": "high",
                        "message": "火灾警报-阶段1",
                        "data": payload
                    })
                    alert_bytes = bytearray([0x30, len(alert_topic.encode()) + len(alert_msg.encode()) + 2])

                    if len(alert_bytes) < 128:
                        alert_bytes.append(len(alert_bytes))
                    else:
                        alert_bytes.append(0x81)
                        alert_bytes.append(len(alert_bytes) - 128)

                    alert_bytes.append(len(alert_topic) >> 8)
                    alert_bytes.append(len(alert_topic) & 0xff)
                    alert_bytes.extend(alert_topic.encode())
                    alert_bytes.extend(alert_msg.encode())

                    sock.send(alert_bytes)

                sock.close()
            else:
                print("❌ 阶段1 MQTT连接失败")
            sock.close()

        except Exception as e:
            print(f"❌ 阶段1 MQTT发送失败: {e}")

    def cleanup(self):
        """清理资源"""
        print("🔥 阶段1清理")
        self.phase1_active = False

# ==================== 阶段2: MQTT控制+舵机 ====================
class Phase2Processor:
    """阶段2处理器"""
    def __init__(self):
        self.phase2_active = False

    def connect_mqtt(self):
        """连接MQTT服务"""
        try:
            import ujson

            print("🔗 阶段2: 连接MQTT控制服务")
            sock = socket.socket()
            sock.settimeout(10)
            addr = socket.getaddrinfo(MQTT_SERVER, MQTT_PORT)[0][-1]
            sock.connect(addr)
            print("✅ TCP连接成功")

            # MQTT CONNECT
            client_id = DEVICE_ID.encode()
            connect_msg = bytearray([0x10, len(client_id) + 12]) + bytearray([0, 4]) + b"MQTT" + bytearray([4, 2, 0, 60]) + bytearray([len(client_id) >> 8, len(client_id) & 0xff]) + client_id
            sock.send(connect_msg)

            # 等待CONNACK
            resp = sock.recv(10)
            if resp and resp[0] == 0x20 and resp[3] == 0x00:
                print("✅ 阶段2 MQTT连接成功")

                # 订阅控制主题
                control_topic = f"esp32/{DEVICE_ID}/control"
                topic_bytes = control_topic.encode()

                sub_msg = bytearray([0x82, len(topic_bytes) + 2, 0, 1, len(topic_bytes) >> 8, len(topic_bytes) & 0xff]) + topic_bytes + bytearray([0x00])

                sock.send(sub_msg)
                print("✅ 阶段2 订阅控制主题")

                self.connected = True
                self.mqtt_sock = sock
                return True
            else:
                print("❌ 阶段2 MQTT连接失败")
                sock.close()
                return False

        except Exception as e:
            print(f"❌ 阶段2 MQTT连接失败: {e}")
            return False

    def check_mqtt_messages(self):
        """检查MQTT控制消息"""
        if not self.connected or not self.mqtt_sock:
            return None

        try:
            self.mqtt_sock.settimeout(0.1)
            data = self.mqtt_sock.recv(256)

            if data and len(data) > 5 and (data[0] & 0xf0) == 0x30:
                # PUBLISH消息
                topic_len = (data[2] << 8) | data[3]
                if len(data) >= 4 + topic_len:
                    topic = data[4:4+topic_len].decode()
                    if "control" in topic:
                        message = data[4+topic_len:].decode()
                        return message

            return None

        except OSError:
            return None  # 超时正常
        except Exception as e:
            print(f"❌ 阶段2 MQTT检查失败: {e}")
            self.connected = False
            return None

    def process_servo_command(self, command):
        """处理舵机命令"""
        try:
            action = command.get('action', '')

            if action == 'on':
                duty = 128
                servo.duty(duty)
                print("🔛 舵机开启 (180度)")
                return True
            elif action == 'off':
                duty = 25
                servo.duty(duty)
                print("🔴 舵机关闭 (0度)")
                return True
            elif action == 'test':
                angle = command.get('angle', 90)
                angle = max(0, min(180, angle))

                if angle == 0:
                    duty = 25
                elif angle == 90:
                    duty = 77
                elif angle == 180:
                    duty = 128
                else:
                    duty = int(25 + (angle * 103) // 180)

                servo.duty(duty)
                print(f"🎯 舵机转到 {angle}度")
                return True
            else:
                print(f"⚠️ 未知舵机动作: {action}")
                return False

        except Exception as e:
            print(f"❌ 舵机控制失败: {e}")
            return False

    def update_oled_display_phase2(self):
        """更新阶段2的OLED显示"""
        if not oled_available:
            return

        try:
            oled.fill(0)

            # 第1行：标题
            oled.text("ALARM-P2", 0, 0)

            # 第2行：状态
            oled.text(f"MQTT:{'OK' if self.connected else 'NC'}", 0, 8)

            # 第3行：舵机状态
            oled.text("SERVO:READY", 0, 16)

            # 第4行：等待状态
            oled.text("WAIT CMD", 0, 24)

            # 第5行：循环计数
            oled.text(f"LP:{self.loop_count if hasattr(self, 'loop_count') else 0}", 0, 32)

            # 第6行：阶段标识
            oled.text("PH:2", 64, 32)

            oled.show()
        except Exception as e:
            print(f"❌ 阶段2 OLED显示失败: {e}")

    def cleanup(self):
        """清理资源"""
        print("🔥 阶段2清理")
        try:
            if self.mqtt_sock:
                self.mqtt_sock.close()
        except:
            pass
        servo.duty(0)
        self.connected = False
        self.phase2_active = False

# ==================== 两阶段控制器 ====================
class TwoPhaseController:
    """两阶段控制器"""
    def __init__(self):
        self.phase1 = Phase1Processor()
        self.phase2 = Phase2Processor()
        self.current_phase = 1
        self.switch_count = 0
        self.auto_switch_interval = 60  # 每60秒切换一次

    def switch_to_phase1(self):
        """切换到阶段1"""
        try:
            print("🔄 切换到阶段1: 传感器+显示+数据上传")

            # 关闭阶段2
            if self.phase2_active:
                self.phase2.cleanup()
                self.phase2_active = False

            # 启动阶段1
            self.phase1_active = True
            self.current_phase = 1

        except Exception as e:
            print(f"❌ 切换到阶段1失败: {e}")

    def switch_to_phase2(self):
        """切换到阶段2"""
        try:
            print("🔄 切换到阶段2: MQTT控制+舵机执行")

            # 关闭阶段1
            if self.phase1_active:
                self.phase1.cleanup()
                self.phase1_active = False

            # 启动阶段2
            if not self.phase2.connect_mqtt():
                print("❌ 阶段2启动失败")
                return False

            self.phase2_active = True
            self.current_phase = 2

        except Exception as e:
            print(f"❌ 切换到阶段2失败: {e}")

    def process_auto_switch(self):
        """自动切换控制"""
        self.switch_count += 1

        if self.switch_count >= self.auto_switch_interval:
            print(f"🔄 自动切换检查 (计数: {self.switch_count})")

            # 垃圾回收
            gc.collect()

            # 检查是否需要切换
            # 简单策略：根据时间切换
            if self.current_phase == 2:  # 阶段2运行时间长了，切回阶段1
                if self.switch_count >= 2:  # 已经在阶段2运行了2个周期
                    self.switch_to_phase1()

            # 每3次循环检查阶段1中的异常情况
            if self.current_phase == 1:
                loop_count = 0
                exception_count = 0

                for i in range(3):  # 检查3次循环
                    try:
                        sensor_data = self.phase1.read_sensors()
                        if not sensor_data:
                            loop_count += 1
                            exception_count += 1

                    except Exception as e:
                        loop_count += 1
                        exception_count += 1
                        print(f"❌ 阶段1传感器异常: {e}")

                # 如果3次循环中有异常，立即切换到阶段2
                if exception_count >= 2:
                    print("⚠️ 阶段1异常较多，切换到阶段2")
                    self.switch_to_phase2()

    def run_phase1(self):
        """运行阶段1"""
        print("🚀 开始运行阶段1...")
        loop_count = 0

        try:
            while self.phase1_active:
                loop_count += 1

                # 更新循环计数到phase1对象
                self.phase1.loop_count = loop_count

                # 读取传感器数据
                sensor_data = self.phase1.read_sensors()

                if sensor_data:
                    # 火灾检测
                    flame_analog = sensor_data.get('flame_analog', 1500)
                    mq2_analog = sensor_data.get('mq2_analog', 1500)
                    if flame_analog < 500 or mq2_analog < 1000:
                        alarm_status = "alarm"
                        print("🚨 火灾警报!")
                    else:
                        alarm_status = "normal"

                    # 更新OLED显示
                    self.phase1.update_oled_display(sensor_data)

                    # 发送MQTT数据
                    self.phase1.send_mqtt_data(sensor_data, alarm_status)

                    # 内存管理
                    if loop_count % 20 == 0:
                        gc.collect()
                        print("🧹 垃圾回收完成")

                    # 短暂等待
                    time.sleep(1.0)

        except KeyboardInterrupt:
            print("\n🏠 用户中断阶段1")
        except Exception as e:
            print(f"\n❌ 阶段1异常: {e}")
        finally:
            self.phase1.cleanup()

    def run_phase2(self):
        """运行阶段2"""
        print("🚀 开始运行阶段2...")
        loop_count = 0

        try:
            while self.phase2_active:
                loop_count += 1

                # 更新循环计数到phase2对象
                self.phase2.loop_count = loop_count

                # 更新OLED显示
                self.phase2.update_oled_display_phase2()

                # 检查MQTT控制消息
                control_message = self.phase2.check_mqtt_messages()

                if control_message:
                    print(f"📨 阶段2收到控制消息: {control_message}")

                    try:
                        import ujson
                        command = ujson.loads(control_message)

                        # 处理舵机命令
                        success = self.phase2.process_servo_command(command)

                        # 发送执行结果反馈
                        result_msg = ujson.dumps({
                            "device_id": DEVICE_ID,
                            "result": success,
                            "action": command.get('action'),
                            "timestamp": time.time(),
                            "phase": 2
                        })

                        feedback_topic = f"esp32/{DEVICE_ID}/control/result"
                        feedback_bytes = bytearray([0x30])

                        # 构建反馈消息
                        topic_bytes = feedback_topic.encode()
                        result_bytes = result_msg.encode()
                        remaining_len = len(topic_bytes) + len(result_bytes) + 2

                        if remaining_len < 128:
                            feedback_bytes.append(remaining_len)
                        else:
                            feedback_bytes.append(0x81)
                            feedback_bytes.append(remaining_len - 128)

                        feedback_bytes.append(len(topic_bytes) >> 8)
                        feedback_bytes.append(len(topic_bytes) & 0xff)
                        feedback_bytes.extend(topic_bytes)
                        feedback_bytes.extend(result_bytes)

                        self.phase2.mqtt_sock.send(feedback_bytes)
                        print(f"✅ 阶段2控制结果已反馈")

                    except Exception as e:
                        print(f"❌ 阶段2控制处理失败: {e}")

                # 内存管理
                if loop_count % 10 == 0:
                    gc.collect()
                    print("🧹 阶段2垃圾回收完成")

                # 短暂等待
                time.sleep(0.5)

        except KeyboardInterrupt:
            print("\n🏠 用户中断阶段2")
        except Exception as e:
            print(f"\n❌ 阶段2异常: {e}")
        finally:
            self.phase2.cleanup()

    def start(self):
        """启动两阶段系统"""
        print("🎯 启动两阶段ESP32火灾报警系统")
        print("📊 阶段1: 传感器监测 + OLED显示 + MQTT数据上传")
        print("🔗 阶段2: MQTT控制 + 舵机执行")

        # 启动阶段1
        self.phase1_active = True

        try:
            while True:
                # 运行阶段1
                self.run_phase1()

                # 自动切换检查
                self.process_auto_switch()

                time.sleep(1.0)

        except KeyboardInterrupt:
            print("\n🏠 用户中断，系统关闭")
        except Exception as e:
            print(f"\n❌ 系统异常: {e}")
        finally:
            print("🔌 系统已安全关闭")

if __name__ == "__main__":
    controller = TwoPhaseController()
    controller.start()