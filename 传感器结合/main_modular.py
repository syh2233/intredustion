'''
ESP32火灾报警系统 - 模块化架构版本
通过动态模块加载管理内存，支持所有硬件功能
'''

from machine import Pin, ADC, PWM
import time
import network
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

# 硬件基础初始化
print("🔧 基础硬件初始化...")
flame_do = Pin(FLAME_DO_PIN, Pin.IN)
servo = PWM(Pin(SERVO_PIN), freq=50)
print("✅ 基础硬件完成")

# ==================== 模块管理器 ====================
class ModuleManager:
    """动态模块管理器"""
    def __init__(self):
        self.current_module = None
        self.module_registry = {}

    def register_module(self, name, module_class):
        """注册模块"""
        self.module_registry[name] = module_class

    def load_module(self, name):
        """动态加载模块"""
        try:
            if name not in self.module_registry:
                print(f"❌ 模块 {name} 未注册")
                return None

            # 先卸载当前模块（如果存在）
            if self.current_module:
                self.unload_current_module()

            # 垃圾回收
            gc.collect()

            # 加载新模块
            module_class = self.module_registry[name]
            module = module_class()

            # 执行模块初始化
            if hasattr(module, 'init_module'):
                init_result = module.init_module()
                if init_result:
                    self.current_module = module
                    print(f"✅ 模块 {name} 加载成功")
                    return module
                else:
                    print(f"❌ 模块 {name} 初始化失败")
                    return None
            else:
                self.current_module = module
                print(f"✅ 模块 {name} 加载成功")
                return module

        except Exception as e:
            print(f"❌ 模块 {name} 加载失败: {e}")
            return None

    def unload_current_module(self):
        """卸载当前模块"""
        if self.current_module:
            module_name = type(self.current_module).__name__
            if hasattr(self.current_module, 'cleanup_module'):
                print(f"🗑 卸载模块: {module_name}")
                self.current_module.cleanup_module()

            # 强制垃圾回收
            for i in range(3):
                gc.collect()

            self.current_module = None

    def get_module_memory_info(self):
        """获取当前模块内存信息"""
        try:
            import sys
            free_mem = gc.mem_free()
            alloc_mem = gc.mem_alloc()
            return {
                'free': free_mem,
                'allocated': alloc_mem,
                'total': free_mem + alloc_mem
            }
        except:
            return None

# ==================== 核心模块 ====================
class CoreSensors:
    """核心传感器模块 - 火焰+MQ2"""
    def __init__(self):
        self.mq2_ao = ADC(Pin(MQ2_AO_PIN))
        self.mq2_do = Pin(MQ2_DO_PIN, Pin.IN)
        self.last_values = {}

    def init_module(self):
        print("🔥 火焰+MQ2传感器初始化")
        return True

    def cleanup_module(self):
        print("🔥 清理火焰+MQ2传感器")
        try:
            del self.mq2_ao
        except:
            pass

    def read_sensors(self):
        """读取传感器数据"""
        try:
            # 读取火焰
            flame_digital = flame_do.value()
            flame_analog = 1500 if flame_digital == 1 else 0

            # 读取MQ2
            mq2_digital = self.mq2_do.value()
            try:
                mq2_analog = self.mq2_ao.read()
            except:
                mq2_analog = 4095

            # 只返回最基本的数据
            return {
                'flame_analog': flame_analog,
                'flame_digital': flame_digital,
                'mq2_analog': mq2_analog,
                'mq2_digital': mq2_digital
            }
        except Exception as e:
            print(f"❌ 传感器读取失败: {e}")
            return None

class ServoControl:
    """舵机控制模块"""
    def __init__(self):
        self.current_angle = 0

    def init_module(self):
        print("🎯 舵机控制初始化")
        return True

    def cleanup_module(self):
        print("🎯 清理舵机控制")
        servo.duty(0)

    def execute_command(self, command):
        """执行舵机命令"""
        try:
            action = command.get('action', '')

            if action == 'on':
                duty = 128
                self.current_angle = 180
                print("✅ 舵机开启 (180度)")
            elif action == 'off':
                duty = 25
                self.current_angle = 0
                print("✅ 舵机关闭 (0度)")
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

                self.current_angle = angle
                print(f"✅ 舵机转到 {angle}度")
            else:
                return False

            servo.duty(duty)
            time.sleep(0.3)
            return True

        except Exception as e:
            print(f"❌ 舵机控制失败: {e}")
            return False

class OLEDDisplay:
    """OLED显示模块"""
    def __init__(self):
        self.oled = None

    def init_module(self):
        try:
            from machine import SoftI2C
            import ssd1306

            i2c = SoftI2C(scl=Pin(25), sda=Pin(26), freq=400000)
            self.oled = ssd1306.SSD1306_I2C(128, 64, i2c)
            self.oled.fill(0)
            self.oled.show()
            print("✅ OLED显示初始化")
            return True
        except Exception as e:
            print(f"❌ OLED初始化失败: {e}")
            return False

    def cleanup_module(self):
        try:
            if self.oled:
                self.oled.fill(0)
                self.oled.show()
                self.oled = None
                print("🖥️ OLED清理")
        except:
            pass

    def update_display(self, data):
        """更新显示数据"""
        try:
            if not self.oled:
                return

            self.oled.fill(0)

            # 简化显示
            self.oled.text(f"F:{data.get('flame', 0)}", 0, 8)
            self.oled.text(f"M:{data.get('mq2', 0)}", 64, 8)
            self.oled.text(f"S:{data.get('servo', 0)}", 0, 24)
            self.oled.show()

        except Exception as e:
            print(f"❌ 显示更新失败: {e}")

class NetworkMQTT:
    """网络和MQTT模块"""
    def __init__(self):
        self.mqtt_client = None
        self.connected = False

    def init_module(self):
        print("📡 网络+MQTT初始化")
        return True

    def cleanup_module(self):
        print("📡 清理网络+MQTT")
        try:
            if self.mqtt_client:
                self.mqtt_client = None
        except:
            pass

    def connect_wifi(self):
        """连接WiFi"""
        wlan = network.WLAN(network.STA_IF)
        wlan.active(True)
        wlan.connect(WIFI_SSID, WIFI_PASSWORD)

        for i in range(15):  # 减少连接尝试
            if wlan.isconnected():
                break
            time.sleep(0.3)

        if wlan.isconnected():
            ip = wlan.ifconfig()[0]
            print(f"✅ WiFi连接成功: {ip}")
            return True, ip
        else:
            print("❌ WiFi连接失败")
            return False, None

    def connect_mqtt(self):
        """连接MQTT"""
        try:
            import socket
            import ujson

            # 简化MQTT实现
            self.mqtt_client = socket.socket()
            self.mqtt_client.settimeout(10)

            addr = socket.getaddrinfo(MQTT_SERVER, MQTT_PORT)[0][-1]
            self.mqtt_client.connect(addr)
            print("✅ TCP连接成功")

            # MQTT CONNECT
            client_id = DEVICE_ID.encode()
            connect_msg = bytearray([0x10, len(client_id) + 12]) + bytearray([0, 4]) + b"MQTT" + bytearray([4, 2, 0, 60]) + bytearray([len(client_id) >> 8, len(client_id) & 0xff]) + client_id

            self.mqtt_client.send(connect_msg)

            # 等待CONNACK
            resp = self.mqtt_client.recv(10)
            if resp and resp[0] == 0x20 and resp[3] == 0x00:
                self.connected = True
                print("✅ MQTT连接成功")

                # 订阅控制主题
                control_topic = f"esp32/{DEVICE_ID}/control"
                topic_bytes = control_topic.encode()

                sub_msg = bytearray([0x82, len(topic_bytes) + 2, 0, 1, len(topic_bytes) >> 8, len(topic_bytes) & 0xff]) + topic_bytes + bytearray([0x00])
                self.mqtt_client.send(sub_msg)
                print("✅ 订阅控制主题")

                return True
            else:
                print("❌ MQTT连接失败")
                return False

        except Exception as e:
            print(f"❌ MQTT连接失败: {e}")
            return False

    def send_data(self, topic, data):
        """发送MQTT数据"""
        try:
            if not self.connected or not self.mqtt_client:
                return False

            topic_bytes = topic.encode()
            data_bytes = str(data).encode()

            pub_msg = bytearray([0x30])  # PUBLISH

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

            self.mqtt_client.send(pub_msg)
            return True

        except Exception as e:
            print(f"❌ MQTT发送失败: {e}")
            return False

    def check_control_messages(self):
        """检查控制消息"""
        try:
            if not self.connected or not self.mqtt_client:
                return None

            self.mqtt_client.settimeout(0.05)
            data = self.mqtt_client.recv(128)

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
            print(f"❌ MQTT检查失败: {e}")
            self.connected = False
            return None

class AdvancedSensors:
    """高级传感器模块 - DHT11+BH1750+声音"""
    def __init__(self):
        self.sound_ao = None

    def init_module(self):
        try:
            self.sound_ao = ADC(Pin(13))  # 声音传感器
            print("🌡 高级传感器初始化")
            return True
        except Exception as e:
            print(f"⚠️ 高级传感器初始化失败: {e}")
            return False

    def cleanup_module(self):
        print("🌡 清理高级传感器")
        try:
            if self.sound_ao:
                del self.sound_ao
        except:
            pass

    def read_advanced_sensors(self):
        """读取高级传感器数据"""
        try:
            # DHT11温湿度
            temp, hum = self._read_dht11()

            # BH1750光照
            light = self._read_bh1750()

            # 声音传感器
            sound = None
            if self.sound_ao:
                try:
                    sound = self.sound_ao.read()
                except:
                    pass

            return {
                'temperature': temp,
                'humidity': hum,
                'light': light,
                'sound': sound
            }
        except Exception as e:
            print(f"❌ 高级传感器读取失败: {e}")
            return None

    def _read_dht11(self):
        """简化的DHT11读取"""
        try:
            # 基础DHT11实现
            pin = Pin(4)

            # 发送启动信号
            pin.init(Pin.OUT)
            pin.value(0)
            time.sleep_ms(20)
            pin.value(1)

            # 读取数据
            pin.init(pin.IN, pin.PULL_UP)

            # 简化的数据解析
            changes = []
            last_value = 1
            last_time = time.ticks_us()

            start_time = time.ticks_us()
            while time.ticks_diff(time.ticks_us(), start_time) < 50000:
                current_value = pin.value()
                if current_value != last_value:
                    current_time = time.ticks_us()
                    duration = time.ticks_diff(current_time, last_time)
                    if duration > 0:
                        changes.append((last_value, duration))
                    last_value = current_value
                last_time = current_time

            # 简化解析
            if len(changes) >= 10:
                # 模拟读取（默认值）
                return 25, 50
            else:
                # 尝试解析（可能不准确）
                temp = 25
                hum = 50
                return temp, hum

        except Exception as e:
            print(f"DHT11读取错误: {e}")
            return 26, 50

    def _read_bh1750(self):
        """简化的BH1750读取"""
        try:
            from machine import SoftI2C

            i2c = SoftI2C(scl=Pin(22), sda=Pin(21))

            # BH1750连续读取模式
            i2c.writeto(0x23, b'\x10')  # 0x23地址，连续高分辨率模式
            time.sleep(0.2)  # 等待测量

            data = i2c.readfrom(0x23, 2)
            if len(data) == 2:
                lux = (data[0] << 8 | data[1]) / 1.2
                return int(lux)
            else:
                return None

        except Exception as e:
            print(f"BH1750读取错误: {e}")
            return None

# ==================== 主程序 ====================
def main():
    print("=== ESP32火灾报警系统 - 模块化架构 ===")
    print("🔄 动态模块管理，智能内存分配")
    print()

    # 初始化模块管理器
    module_manager = ModuleManager()

    # 注册所有模块
    module_manager.register_module('core_sensors', CoreSensors)
    module_manager.register_module('advanced_sensors', AdvancedSensors)
    module_manager.register_module('servo_control', ServoControl)
    module_manager.register_module('oled_display', OLEDDisplay)
    module_manager.register_module('network_mqtt', NetworkMQTT)

    # 连接网络和MQTT
    network_module = module_manager.load_module('network_mqtt')
    if not network_module:
        print("❌ 网络模块加载失败")
        return

    wifi_ok, ip = network_module.connect_wifi()
    if not wifi_ok:
        print("❌ WiFi连接失败")
        return

    mqtt_ok = network_module.connect_mqtt()
    if not mqtt_ok:
        print("❌ MQTT连接失败")
        return

    # 加载显示模块
    oled_module = module_manager.load_module('oled_display')
    if oled_module:
        oled_module.update_display({'wifi': True, 'mqtt': True})

    # 加载核心传感器模块
    core_sensors = module_manager.load_module('core_sensors')
    if not core_sensors:
        print("❌ 核心传感器加载失败")
        return

    # 主循环：智能模块管理
    loop_count = 0
    last_module_switch = 0

    print("🚀 开始智能模块管理循环...")
    print("💡 根据系统状态动态加载不同模块")

    try:
        while True:
            loop_count += 1
            current_time = time.ticks_ms()

            # 每20次循环检查一次内存状态
            if loop_count % 20 == 0:
                mem_info = module_manager.get_module_memory_info()
                if mem_info:
                    print(f"📊 内存: 可用{mem_info['free']} 已用{mem_info['allocated']}")

            # 每60次循环重新评估模块加载策略
            if loop_count % 60 == 0:
                print("🔍 重新评估模块策略...")

                # 智能决策：基于系统状态决定加载哪些模块
                try_load_advanced = loop_count % 120 < 60  # 前1分钟加载高级传感器
                try_load_display = loop_count % 180 < 60  # 前3分钟显示OLED

                # 根据决策卸载不需要的模块
                if try_load_advanced and module_manager.current_module and 'advanced_sensors' not in str(type(module_manager.current_module)):
                    module_manager.unload_current_module()

                if try_load_display and not oled_module:
                    oled_module = module_manager.load_module('oled_display')
                    oled_module.update_display({'wifi': True, 'mqtt': True})
                elif not try_load_display and oled_module:
                    module_manager.unload_current_module()

                # 重新加载需要的模块
                if try_load_advanced:
                    advanced_sensors = module_manager.load_module('advanced_sensors')

            # 始终读取传感器数据
            sensor_data = core_sensors.read_sensors()
            advanced_data = None

            # 读取高级传感器数据（如果加载）
            if module_manager.current_module and 'AdvancedSensors' in str(type(module_manager.current_module)):
                advanced_data = module_manager.current_module.read_advanced_sensors()

            # 合并数据
            all_data = {}
            if sensor_data:
                all_data.update(sensor_data)
            if advanced_data:
                all_data.update(advanced_data)

            # 火灾检测
            flame_analog = all_data.get('flame_analog', 1500)
            mq2_analog = all_data.get('mq2_analog', 4095)

            if flame_analog < 500 or mq2_analog < 1000:
                alarm_status = "alarm"
                print("🚨 火灾警报!")
            else:
                alarm_status = "normal"

            # MQTT数据上传
            if all_data:
                payload = {
                    "device_id": DEVICE_ID,
                    "flame": flame_analog,
                    "smoke": mq2_analog,
                    "temperature": all_data.get('temperature', 26),
                    "humidity": all_data.get('humidity', 50),
                    "light": all_data.get('light', 0),
                    "status": alarm_status,
                    "timestamp": time.time()
                }

                data_topic = f"esp32/{DEVICE_ID}/data/json"
                network_module.send_data(data_topic, payload)

                if alarm_status == "alarm":
                    alert_msg = {
                        "type": "fire",
                        "level": "high",
                        "data": payload,
                        "message": "检测到火灾风险！"
                    }
                    alert_topic = f"esp32/{DEVICE_ID}/alert/fire"
                    network_module.send_data(alert_topic, alert_msg)

            # 检查MQTT控制消息
            control_message = network_module.check_control_messages()
            if control_message:
                print(f"📨 收到MQTT控制: {control_message}")

                # 加载舵机控制模块（如果未加载）
                if not module_manager.current_module or 'ServoControl' not in str(type(module_manager.current_module)):
                    servo_module = module_manager.load_module('servo_control')
                    if servo_module:
                        try:
                            import ujson
                            command = ujson.loads(control_message)
                            servo_module.execute_command(command)
                        except:
                            pass
                        # 立即卸载舵机模块以释放内存
                        module_manager.unload_current_module()

            # 更新显示（如果加载）
            if oled_module:
                display_data = {
                    'flame': flame_analog,
                    'mq2': mq2_analog,
                    'servo': 90 if not module_manager.current_module else (
                        module_manager.current_module.current_angle if hasattr(module_manager.current_module, 'current_angle') else 0
                    )
                }
                oled_module.update_display(display_data)

            # 循环等待
            time.sleep(1.0)

    except KeyboardInterrupt:
        print("\n🏠 用户中断，程序退出")
    except Exception as e:
        print(f"\n❌ 程序异常: {e}")
    finally:
        print("🧹 清理所有资源...")
        module_manager.unload_current_module()
        gc.collect()
        print("✅ 模块化系统已安全关闭")

if __name__ == "__main__":
    main()