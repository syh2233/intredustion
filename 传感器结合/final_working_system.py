'''
最终工作版本的传感器系统
无OLED但功能完整，专注于传感器监测和舵机控制
包含MQ2校准功能
'''

from machine import Pin, ADC, PWM
import time
import json
import network
import socket
import dht

# ==================== 常量配置 ====================
DEVICE_ID = "esp32_fire_alarm_01"

# WiFi配置
WIFI_SSID = "syh2031"
WIFI_PASSWORD = "12345678"

# MQTT配置
MQTT_SERVER = "192.168.24.32"
MQTT_PORT = 1883

# GPIO配置（保持你的接线）
DHT11_PIN = 4
FLAME_PIN = 14  # 火焰传感器专用GPIO14
MQ2_AO_PIN = 34
MQ2_DO_PIN = 2
SOUND_AO_PIN = 13
SOUND_DO_PIN = 35
SERVO_PIN = 15

# 舵机角度配置
SERVO_SAFE_ANGLE = 0      # 安全位置（舵机关闭）
SERVO_ALERT_ANGLE = 90    # 警报位置（舵机启动）

# ==================== 硬件初始化 ====================
print("🔧 初始化硬件...")

# 初始化舵机
servo = PWM(Pin(SERVO_PIN), freq=50)
print("✅ 舵机初始化完成")

# 初始化MQ2烟雾传感器
mq2_ao = ADC(Pin(MQ2_AO_PIN))
mq2_do = Pin(MQ2_DO_PIN, Pin.IN)
mq2_ao.atten(ADC.ATTN_11DB)
print("✅ MQ2烟雾传感器初始化完成")

# 全局变量
flame_pin = None
alert_counter = 0  # 连续报警计数器
current_servo_angle = SERVO_SAFE_ANGLE  # 当前舵机角度，避免重复设置
mqtt_client = None  # MQTT客户端
wifi_connected = False  # WiFi连接状态
sound_error_printed = False  # 声音传感器错误标记
dht_error_printed = False  # 温湿度传感器错误标记

# 声音传感器对象（延迟初始化）
sound_ao = None
sound_do = None

# ==================== WiFi和MQTT函数 ====================
def connect_wifi():
    """连接WiFi网络"""
    global wifi_connected
    print("📡 正在连接WiFi...")
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)

    if not wlan.isconnected():
        print(f"连接到: {WIFI_SSID}")
        wlan.connect(WIFI_SSID, WIFI_PASSWORD)

        # 等待连接
        timeout = 0
        while not wlan.isconnected() and timeout < 30:
            time.sleep(1)
            timeout += 1
            print(".", end="")

        print()

        if wlan.isconnected():
            wifi_connected = True
            print("✅ WiFi连接成功!")
            print(f"IP地址: {wlan.ifconfig()[0]}")
            return True
        else:
            print("❌ WiFi连接失败!")
            wifi_connected = False
            return False
    else:
        wifi_connected = True
        print("✅ WiFi已连接")
        print(f"IP地址: {wlan.ifconfig()[0]}")
        return True

class SimpleMQTTClient:
    """简化的MQTT客户端"""
    def __init__(self, client_id, server, port):
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
            self.sock.settimeout(15)  # 增加超时时间
            addr = socket.getaddrinfo(self.server, self.port)[0][-1]
            self.sock.connect(addr)
            print("TCP连接成功")

            # 构建MQTT CONNECT消息
            protocol_name = b"MQTT"
            protocol_level = 4  # MQTT 3.1.1
            flags = 0x02  # Clean session
            keep_alive = 30  # 减少keep alive时间

            # 可变头部
            var_header = bytearray()
            var_header.append(0)  # MSB of protocol name length
            var_header.append(len(protocol_name))  # LSB of protocol name length
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
                if len(response) > 0:
                    print(f"响应: {[hex(b) for b in response]}")
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
            self.connected = False  # 连接断开，标记为未连接
            return False

    def disconnect(self):
        """断开连接"""
        if self.sock and self.connected:
            try:
                self.sock.send(b"\xE0\x00")  # DISCONNECT
                self.sock.close()
            except:
                pass
            finally:
                self.connected = False

def reconnect_mqtt():
    """重新连接MQTT服务器"""
    global mqtt_client
    try:
        if mqtt_client:
            mqtt_client.disconnect()
        mqtt_client = SimpleMQTTClient(DEVICE_ID, MQTT_SERVER, MQTT_PORT)
        if mqtt_client.connect():
            print("📡 MQTT重新连接成功")
            return True
        else:
            print("❌ MQTT重新连接失败")
            return False
    except Exception as e:
        print(f"❌ MQTT重新连接异常: {e}")
        return False

def send_sensor_data_to_mqtt(sensor_data, status, alerts, danger_level):
    """发送传感器数据到MQTT服务器"""
    global mqtt_client

    # 检查连接状态，如果断开尝试重连
    if not mqtt_client or not mqtt_client.connected:
        print("📡 MQTT连接已断开，尝试重新连接...")
        if not reconnect_mqtt():
            return False

    try:
        # 构建MQTT消息
        mqtt_data = {
            "device_id": DEVICE_ID,
            "timestamp": time.time(),
            "sensor_data": sensor_data,
            "system_status": {
                "status": status,
                "danger_level": danger_level,
                "alerts": alerts,
                "alert_counter": alert_counter
            },
            "location": "宿舍火灾报警系统"
        }

        payload = json.dumps(mqtt_data)
        topic = f"esp32/{DEVICE_ID}/data/json"

        if mqtt_client.publish(topic, payload):
            print(f"📡 MQTT数据已发送")
            return True
        else:
            print(f"❌ MQTT发送失败，尝试重新连接...")
            if reconnect_mqtt():
                # 重连成功后重试发送
                return mqtt_client.publish(topic, payload)
            return False

    except Exception as e:
        print(f"❌ MQTT数据打包失败: {e}")
        return False

# ==================== 传感器函数 ====================
def read_flame():
    """读取火焰传感器（GPIO14数字模式）"""
    if flame_pin is None:
        return None
    try:
        # GPIO14只支持数字输入，直接读取数字值
        return flame_pin.value()
    except:
        return None

def read_mq2():
    """读取MQ2烟雾传感器"""
    try:
        analog_value = mq2_ao.read()
        digital_value = mq2_do.value()
        return analog_value, digital_value
    except:
        return None, None

def read_sound():
    """读取声音传感器（仅数字模式）"""
    try:
        if sound_do is None:
            return None, None

        # 读取数字值
        digital_value = sound_do.value()
        return None, digital_value  # 模拟值返回None

    except Exception as e:
        # 只在第一次失败时打印错误信息
        global sound_error_printed
        if not sound_error_printed:
            print(f"⚠️ 声音传感器读取失败: {e}")
            sound_error_printed = True
        return None, None

def read_dht11():
    """读取DHT11温湿度数据（按照dht11_simple.py的逻辑）"""
    try:
        pin = Pin(DHT11_PIN)

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
            return None, None

        bits = []
        for i in range(2, len(changes), 2):
            if i + 1 < len(changes):
                high_duration = changes[i][1]
                bit = 1 if high_duration > 50 else 0
                bits.append(bit)
                if len(bits) >= 40:
                    break

        if len(bits) < 40:
            return None, None

        # 转换为字节数据
        data = bytearray(5)
        for i in range(5):
            for j in range(8):
                data[i] = (data[i] << 1) | bits[i*8 + j]

        # 校验和检查
        checksum = (data[0] + data[1] + data[2] + data[3]) & 0xFF
        if checksum != data[4]:
            return None, None

        # 返回温度和湿度
        temperature = data[2]
        humidity = data[0]

        if 0 <= humidity <= 95 and 0 <= temperature <= 50:
            return temperature, humidity
        else:
            return None, None

    except Exception as e:
        # 只在第一次失败时打印错误信息
        global dht_error_printed
        if not dht_error_printed:
            print(f"⚠️ DHT11温湿度传感器读取失败: {e}")
            dht_error_printed = True
        return None, None

def set_servo_angle(angle):
    """设置舵机角度（只有角度改变时才设置）"""
    global current_servo_angle
    try:
        # 只有当角度改变时才设置舵机
        if angle != current_servo_angle:
            duty = int(angle / 180 * 102 + 26)  # 0-180度映射到26-128
            servo.duty(duty)
            current_servo_angle = angle  # 更新当前角度
            # 只有当舵机角度改变时才打印信息
            if angle == SERVO_ALERT_ANGLE:
                print(f"🔥 舵机启动到警报位置: {angle}°")
            elif angle == SERVO_SAFE_ANGLE:
                print(f"✅ 舵机重置到安全位置: {angle}°")
    except:
        pass

def reset_servo_to_safe():
    """重置舵机到安全位置（只有需要时才重置）"""
    global current_servo_angle
    try:
        if current_servo_angle != SERVO_SAFE_ANGLE:
            duty = int(SERVO_SAFE_ANGLE / 180 * 102 + 26)  # 0度对应26
            servo.duty(duty)
            current_servo_angle = SERVO_SAFE_ANGLE
    except:
        pass

def init_flame_sensor():
    """初始化火焰传感器 - GPIO14只支持数字输入"""
    global flame_pin
    try:
        # GPIO14在ESP32上只支持数字输入，直接使用数字模式
        flame_pin = Pin(FLAME_PIN, Pin.IN)
        test_digital = flame_pin.value()
        print(f"✅ 火焰传感器初始化成功（数字模式），测试读数: {test_digital}")
        print(f"   说明: GPIO{FLAME_PIN}检测到火焰时输出0，正常时输出1")
        return True
    except Exception as e:
        print(f"❌ 火焰传感器初始化失败: {e}")
        flame_pin = None
        return False

def init_sound_sensor():
    """初始化声音传感器 - 仅使用数字模式"""
    global sound_ao, sound_do, sound_error_printed
    try:
        # 仅初始化数字输出（GPIO35）
        sound_do = Pin(SOUND_DO_PIN, Pin.IN)
        test_digital = sound_do.value()
        print(f"✅ 声音传感器初始化成功（数字模式），测试读数: {test_digital}")
        print(f"   说明: GPIO{SOUND_DO_PIN}检测到声音时输出0，安静时输出1")

        # 模拟输出设置为None，表示不可用
        sound_ao = None
        sound_error_printed = False
        return True

    except Exception as e:
        print(f"❌ 声音传感器初始化失败: {e}")
        sound_ao = None
        sound_do = None
        return False

def get_mq2_status(analog_value, digital_value):
    """获取MQ2传感器状态描述"""
    if analog_value is None:
        return "读取错误"

    # 计算烟雾浓度百分比
    concentration = min(100, max(0, (analog_value / 4095) * 100))

    # 根据用户要求调整状态判断：1700以上为正常值
    if analog_value > 2500:
        return f"🚨检测到烟雾! 浓度{concentration:.0f}%"
    elif analog_value > 2200:
        return f"⚠️烟雾浓度偏高 浓度{concentration:.0f}%"
    elif analog_value > 1700:
        return f"✅空气质量正常 浓度{concentration:.0f}%"
    else:
        return f"✅空气清新 浓度{concentration:.0f}%"

# ==================== 主程序 ====================
def main():
    """主函数"""
    print("🚀 最终工作版传感器系统启动（含MQTT上传）")
    print("=" * 70)
    print("特点:")
    print("✅ 无OLED，功能完整")
    print("✅ 包含MQ2校准提示")
    print("✅ 专注于传感器监测")
    print("✅ 舵机控制正常")
    print("✅ MQTT数据上传")
    print("=" * 70)

    # 连接WiFi
    print("\n📡 连接网络...")
    wifi_ok = connect_wifi()

    # 连接MQTT（只有在WiFi连接成功时）
    global mqtt_client
    if wifi_ok:
        try:
            mqtt_client = SimpleMQTTClient(DEVICE_ID, MQTT_SERVER, MQTT_PORT)
            if mqtt_client.connect():
                print("✅ MQTT连接成功")
            else:
                print("❌ MQTT连接失败，继续运行但不上传数据")
                mqtt_client = None
        except Exception as e:
            print(f"❌ MQTT连接异常: {e}")
            mqtt_client = None
    else:
        print("❌ WiFi连接失败，跳过MQTT连接")

    # 初始化火焰传感器
    flame_ok = init_flame_sensor()

    # 初始化声音传感器
    sound_ok = init_sound_sensor()

    # 初始化舵机到安全位置
    set_servo_angle(SERVO_SAFE_ANGLE)
    print("✅ 舵机初始化到安全位置（0度，不启动）")

    print("\n📊 开始监测...")
    print("=" * 70)
    print("格式: [次数] 火焰 | 烟雾(模拟,数字) | 声音(模拟,数字) | 温度 | 湿度 | 系统状态 | 警报信息 | 报警计数")
    print("-" * 70)

    # 主循环
    loop_count = 0

    while True:
        loop_count += 1

        try:
            # 读取所有传感器数据
            sensor_data = {}

            # 火焰传感器
            flame_value = read_flame()
            if flame_value is not None:
                sensor_data['flame'] = flame_value

            # MQ2烟雾传感器
            smoke_analog, smoke_digital = read_mq2()
            if smoke_analog is not None:
                sensor_data['smoke_analog'] = smoke_analog
            if smoke_digital is not None:
                sensor_data['smoke_digital'] = smoke_digital

            # 声音传感器
            sound_analog, sound_digital = read_sound()
            if sound_analog is not None:
                sensor_data['sound_analog'] = sound_analog
            if sound_digital is not None:
                sensor_data['sound_digital'] = sound_digital

            # 温湿度传感器
            temperature, humidity = read_dht11()
            if temperature is not None and humidity is not None:
                sensor_data['temperature'] = temperature
                sensor_data['humidity'] = humidity
            else:
                # 读取失败时使用默认值
                sensor_data['temperature'] = 26  # 默认26度
                sensor_data['humidity'] = 50   # 默认50%

            # 危险检测逻辑
            danger_level = 0
            alerts = []

            # 火焰检测（GPIO14数字模式：0表示检测到火焰，1表示正常）
            if flame_value is not None:
                if flame_value == 0:
                    danger_level += 3
                    alerts.append("火焰检测")

            # 烟雾检测（根据用户要求调整：1700以上为正常值）
            if smoke_analog is not None:
                if smoke_analog > 2500:  # 高于2500才认为是烟雾
                    danger_level += 2
                    alerts.append("烟雾检测")
                elif smoke_analog > 2200:  # 2200-2500之间是警告
                    danger_level += 1
                    alerts.append("烟雾浓度偏高")
                # 1700-2200之间是正常范围，不触发警报

            # 数字检测作为辅助，但当模拟值在正常范围时忽略数字检测
            if smoke_digital == 0 and smoke_analog is not None and smoke_analog <= 1700:  # 只有当模拟值低于1700时才考虑数字检测
                danger_level += 1
                alerts.append("数字检测到烟雾")

            # 声音检测（数字0=有声音）
            if sound_digital == 0:
                danger_level += 1
                alerts.append("异常声音")

            # 确定系统状态
            if danger_level >= 4:
                status = "🚨危险"
                alert_counter += 1  # 增加报警计数器
                if alert_counter >= 3:  # 连续3次报警才启动舵机
                    set_servo_angle(SERVO_ALERT_ANGLE)
                    status = "🚨危险(舵机启动)"  # 更新状态显示
                else:
                    print(f"⚠️ 检测到危险! 报警计数: {alert_counter}/3")
                    set_servo_angle(SERVO_SAFE_ANGLE)  # 确保在等待期间舵机不启动
            elif danger_level >= 2:
                status = "⚠️警告"
                alert_counter = 0  # 重置报警计数器
                set_servo_angle(SERVO_SAFE_ANGLE)  # 确保警告状态舵机不启动
            else:
                status = "✅正常"
                alert_counter = 0  # 重置报警计数器
                set_servo_angle(SERVO_SAFE_ANGLE)  # 确保正常状态舵机不启动

            # 格式化显示
            flame_str = f"{flame_value or 'N/A'}"
            smoke_str = f"{smoke_analog or 'N/A'},{smoke_digital if smoke_digital is not None else 'N/A'}"
            sound_str = f"{sound_analog or 'N/A'},{sound_digital if sound_digital is not None else 'N/A'}"
            temp_str = f"{temperature}°C" if temperature is not None else "26°C"
            hum_str = f"{humidity}%" if humidity is not None else "50%"

            # 获取烟雾状态描述
            if smoke_analog is not None and smoke_digital is not None:
                smoke_status = get_mq2_status(smoke_analog, smoke_digital)
            else:
                smoke_status = "读取错误"

            alert_str = f"警报:{', '.join(alerts)}" if alerts else "警报:无"

            # 输出完整信息
            counter_str = f"计数:{alert_counter}" if alert_counter > 0 else "计数:0"
            print(f"[{loop_count:3d}] {flame_str:^6} | {smoke_str:^8} | {sound_str:^8} | {temp_str:^6} | {hum_str:^5} | {status} | {alert_str} | {counter_str}")

            # 发送数据到MQTT（每次循环都发送）
            if mqtt_client and wifi_connected:
                # 构建传感器数据对象（使用sensor_data，已包含温湿度数据）
                mqtt_sensor_data = sensor_data.copy()

                # 发送到MQTT
                send_sensor_data_to_mqtt(mqtt_sensor_data, status, alerts, danger_level)

            # 每10次循环显示MQ2状态建议
            if loop_count % 10 == 0:
                print(f"💡 MQ2状态: {smoke_status}")
                if smoke_analog > 2200:  # 只有在浓度偏高时才提示
                    print("   🔧 提示: 如需调节灵敏度请运行 mq2_realtime_adjust.py")
                elif smoke_analog > 1700:  # 显示正常范围提示
                    print("   ✅ 当前数值在正常范围内 (1700+)")

        except Exception as e:
            print(f"[{loop_count:3d}] ❌ 读取错误: {e}")

        # 采样间隔
        time.sleep(2)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n🛑 程序停止")
        set_servo_angle(SERVO_SAFE_ANGLE)
        print("✅ 舵机已回到安全位置")
        # 断开MQTT连接
        if mqtt_client:
            mqtt_client.disconnect()
            print("📡 MQTT连接已断开")
        print("👋 感谢使用!")
    except Exception as e:
        print(f"\n❌ 程序错误: {e}")
        set_servo_angle(SERVO_SAFE_ANGLE)
        # 断开MQTT连接
        if mqtt_client:
            mqtt_client.disconnect()
            print("📡 MQTT连接已断开")