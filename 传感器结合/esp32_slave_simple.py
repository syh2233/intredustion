'''
ESP32火灾报警系统 - 从机版本 (简化版)
通过WiFi UDP通信将火焰和烟雾传感器数据传输到ESP32主机
硬件配置：
- 火焰传感器: GPIO14 (模拟输入)
- MQ2烟雾传感器: GPIO34 (模拟输入), GPIO2 (数字输入)
- LED指示灯: GPIO5 (状态指示)
'''

from machine import Pin, ADC, SoftI2C
import time
import network
import socket
import json
import machine
import ssd1306

# ==================== 常量配置 ====================
# 从机设备信息
SLAVE_ID = "esp32_slave_01"
SLAVE_NAME = "从机-01"

# WiFi配置 (与主机相同网络)
WIFI_SSID = "syh2031"
WIFI_PASSWORD = "12345678"

# 主机配置 (UDP通信) - 现在使用自动发现
HOST_PORT = 8888          # UDP通信端口

# GPIO配置
FLAME_PIN = 14        # 火焰传感器数字输入（0=有火，1=无火）
MQ2_AO_PIN = 34       # MQ2烟雾传感器模拟输入
MQ2_DO_PIN = 2        # MQ2烟雾传感器数字输入
LED_PIN = 5           # 状态指示灯
OLED_SDA = 26         # OLED SDA引脚
OLED_SCL = 25         # OLED SCL引脚

# 传感器阈值配置
FLAME_ALARM_THRESHOLD = 500      # 火焰警报阈值
FLAME_WARNING_THRESHOLD = 1000   # 火焰警告阈值
MQ2_ALARM_THRESHOLD = 1000       # 烟雾警报阈值
MQ2_WARNING_THRESHOLD = 1300     # 烟雾警告阈值

# 通信配置
SEND_INTERVAL = 2.0      # 数据发送间隔(秒)
MAX_RETRIES = 3         # 最大重试次数
TIMEOUT = 5.0           # 通信超时时间

# ==================== 硬件初始化 ====================
print("🔧 初始化从机硬件...")

# 初始化LED状态指示灯
led = Pin(LED_PIN, Pin.OUT)
led.value(0)  # 初始关闭

# 初始化火焰传感器 (数字模式)
print(f"初始化火焰传感器 - GPIO{FLAME_PIN} (数字模式)")
flame_digital = Pin(FLAME_PIN, Pin.IN)

# 初始化MQ2烟雾传感器
print(f"初始化MQ2烟雾传感器 - 模拟:GPIO{MQ2_AO_PIN}, 数字:GPIO{MQ2_DO_PIN}")
mq2_adc = ADC(Pin(MQ2_AO_PIN))
mq2_adc.width(ADC.WIDTH_12BIT)  # 设置12位分辨率 (0-4095)
mq2_adc.atten(ADC.ATTN_11DB)    # 设置11dB衰减，0-3.3V范围
mq2_do = Pin(MQ2_DO_PIN, Pin.IN)

# 初始化OLED显示屏
print(f"初始化OLED显示屏 - SDA:GPIO{OLED_SDA}, SCL:GPIO{OLED_SCL}")
try:
    i2c = SoftI2C(scl=Pin(OLED_SCL), sda=Pin(OLED_SDA))
    oled_width = 128
    oled_height = 64
    oled = ssd1306.SSD1306_I2C(oled_width, oled_height, i2c)
    oled.fill(0)
    oled.text("ESP32从机", 0, 0)
    oled.text("初始化中...", 0, 16)
    oled.show()
    print("✅ OLED显示屏初始化成功")
except Exception as e:
    print(f"❌ OLED显示屏初始化失败: {e}")
    oled = None

print("✅ 硬件初始化完成")

# ==================== WiFi连接 ====================
def connect_wifi():
    """连接WiFi网络"""
    print(f"📡 连接WiFi: {WIFI_SSID}")

    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)

    if wlan.isconnected():
        print(f"✅ WiFi已连接，IP: {wlan.ifconfig()[0]}")
        return wlan

    print("正在连接...")
    wlan.connect(WIFI_SSID, WIFI_PASSWORD)

    # 等待连接
    for i in range(30):
        if wlan.isconnected():
            ip_info = wlan.ifconfig()
            print(f"✅ WiFi连接成功!")
            print(f"   IP地址: {ip_info[0]}")
            print(f"   子网掩码: {ip_info[1]}")
            print(f"   网关: {ip_info[2]}")
            return wlan
        led.value(not led.value())  # LED闪烁表示正在连接
        time.sleep(0.5)

    print("❌ WiFi连接失败")
    return None

# ==================== 主机发现模块 ====================
class HostDiscovery:
    def __init__(self):
        self.broadcast_socket = None
        self.discovery_socket = None
        self.discovery_port = 8887  # 发现请求端口
        self.host_port = 8888       # 主机UDP端口

    def start_discovery(self):
        """启动主机发现"""
        try:
            # 创建发现请求socket
            self.discovery_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.discovery_socket.settimeout(8.0)  # 8秒超时
            self.discovery_socket.bind(('0.0.0.0', self.discovery_port))
            print(f"✅ 主机发现服务启动，监听端口: {self.discovery_port}")
            return True
        except Exception as e:
            print(f"❌ 主机发现服务启动失败: {e}")
            return False

    def send_discovery_request(self):
        """发送主机发现请求"""
        try:
            if not self.discovery_socket:
                print("❌ 发现socket未初始化")
                return False

            # 构建发现请求数据
            discovery_request = {
                "type": "discover",
                "slave_id": SLAVE_ID,
                "slave_name": SLAVE_NAME,
                "timestamp": time.time(),
                "message": "寻找主机"
            }

            # 发送广播发现请求
            json_data = json.dumps(discovery_request)
            sent_to_any = False

            # 方法1: 尝试广播
            try:
                self.discovery_socket.sendto(json_data.encode(), ('255.255.255.255', self.host_port))
                print("🔍 发送主机发现广播到 255.255.255.255...")
                sent_to_any = True
            except:
                print("⚠️ 全网广播失败")

            # 方法2: 尝试网关广播
            try:
                import network
                wlan = network.WLAN(network.STA_IF)
                if wlan.isconnected():
                    ip_info = wlan.ifconfig()
                    gateway_ip = ip_info[2]
                    # 构造广播地址 (例如: 192.168.24.255)
                    broadcast_ip = '.'.join(gateway_ip.split('.')[:3]) + '.255'
                    self.discovery_socket.sendto(json_data.encode(), (broadcast_ip, self.host_port))
                    print(f"🔍 发送主机发现广播到 {broadcast_ip}...")
                    sent_to_any = True
            except Exception as e:
                print(f"⚠️ 网关广播失败: {e}")

            # 方法3: 尝试常见的主机IP地址
            common_ips = ['192.168.24.23', '192.168.24.100', '192.168.24.1']
            for ip in common_ips:
                try:
                    self.discovery_socket.sendto(json_data.encode(), (ip, self.host_port))
                    print(f"🔍 尝试发送到 {ip}...")
                    sent_to_any = True
                except:
                    pass

            if not sent_to_any:
                print("❌ 所有发送方法都失败")

            return True

        except Exception as e:
            print(f"❌ 发送发现请求失败: {e}")
            return False

    def wait_for_host_response(self):
        """等待主机响应"""
        if not self.discovery_socket:
            return None

        try:
            # 等待主机响应
            data, addr = self.discovery_socket.recvfrom(512)
            host_ip = addr[0]
            host_port = addr[1]

            # 解析响应数据
            try:
                response_data = json.loads(data.decode('utf-8'))
                print(f"📨 收到主机响应: {host_ip}")

                # 验证响应数据
                if response_data.get('type') == 'discover_response':
                    return response_data, host_ip, host_port
                else:
                    print(f"⚠️  收到无效响应类型: {response_data.get('type')}")
                    return None

            except json.JSONDecodeError:
                print(f"❌ 响应JSON解析失败 - 来自 {host_ip}")
                return None

        except Exception as e:
            # MicroPython socket超时或其他异常
            if "timeout" in str(e).lower():
                print("⏰ 主机发现超时")
            else:
                print(f"❌ 接收主机响应错误: {e}")
            return None

    def discover_host(self, max_attempts=3):
        """发现主机"""
        print(f"🔍 开始主机发现 (最多尝试{max_attempts}次)...")

        for attempt in range(max_attempts):
            print(f"\n--- 发现尝试 {attempt + 1}/{max_attempts} ---")

            # 发送发现请求
            if not self.send_discovery_request():
                print("❌ 发现请求发送失败")
                continue

            # 等待响应
            response = self.wait_for_host_response()
            if response:
                response_data, host_ip, host_port = response
                print(f"✅ 主机发现成功!")
                print(f"   主机IP: {host_ip}")
                print(f"   主机端口: {host_port}")
                print(f"   主机名称: {response_data.get('host_name', 'Unknown')}")
                return host_ip, host_port

            print(f"❌ 第{attempt + 1}次尝试失败")

            if attempt < max_attempts - 1:
                print("等待2秒后重试...")
                time.sleep(2)

        print("❌ 主机发现失败，请检查:")
        print("   1. 主机是否正在运行")
        print("   2. 主机和从机是否在同一WiFi网络")
        print("   3. 网络连接是否正常")
        return None, None

    def stop(self):
        """停止发现服务"""
        if self.discovery_socket:
            self.discovery_socket.close()
        print("主机发现服务已停止")

# ==================== UDP通信模块 ====================
class UDPSlaveClient:
    def __init__(self, host_ip, host_port):
        self.host_ip = host_ip
        self.host_port = host_port
        self.socket = None
        self.connected = False
        self.receive_socket = None
        self.receive_port = 8889  # 从机接收端口（与发送端口不同）

    def connect(self):
        """建立UDP socket"""
        try:
            # 发送socket
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.socket.settimeout(TIMEOUT)

            # 接收socket
            self.receive_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.receive_socket.bind(('0.0.0.0', self.receive_port))
            self.receive_socket.settimeout(0.1)  # 非阻塞模式

            self.connected = True
            print(f"✅ UDP客户端创建成功，目标: {self.host_ip}:{self.host_port}")
            print(f"✅ 接收端口: {self.receive_port}")
            return True
        except Exception as e:
            print(f"❌ UDP客户端创建失败: {e}")
            return False

    def send_data(self, data):
        """发送数据到主机"""
        if not self.connected or not self.socket:
            return False

        try:
            # 将数据转换为JSON字符串
            json_data = json.dumps(data)

            # 发送数据
            self.socket.sendto(json_data.encode(), (self.host_ip, self.host_port))
            print(f"📤 数据已发送到 {self.host_ip}:{self.host_port}")
            return True

        except Exception as e:
            print(f"❌ 数据发送失败: {e}")
            return False

    def receive_data(self):
        """接收来自主机的数据"""
        if not self.connected or not self.receive_socket:
            return None

        try:
            data, addr = self.receive_socket.recvfrom(512)
            sender_ip = addr[0]
            sender_port = addr[1]

            # 解析JSON数据
            try:
                json_data = json.loads(data.decode('utf-8'))
                return json_data, sender_ip, sender_port
            except json.JSONDecodeError:
                print(f"❌ JSON解析失败 - 来自 {sender_ip}:{sender_port}")
                return None

        except Exception as e:
            # MicroPython socket超时或其他异常
            return None

    def test_host_connection(self):
        """测试与主机的连接"""
        if not self.connected:
            return False

        try:
            # 发送测试消息
            test_data = {
                "type": "test",
                "slave_id": SLAVE_ID,
                "message": "connection_test",
                "timestamp": time.time()
            }
            return self.send_data(test_data)
        except:
            return False

    def close(self):
        """关闭连接"""
        if self.socket:
            self.socket.close()
        if self.receive_socket:
            self.receive_socket.close()
        self.connected = False
        print("UDP连接已关闭")

# ==================== 传感器读取函数 ====================
def read_flame_sensor():
    """读取火焰传感器 - 数字模式"""
    try:
        # 读取数字值：0=检测到火焰，1=正常
        digital_value = flame_digital.value()

        if digital_value == 0:  # 检测到火焰
            status = "alarm"
            analog_value = 0  # 用于显示
        else:  # 正常状态
            status = "normal"
            analog_value = 1500  # 用于显示，设置为高值避免误报警

        return analog_value, digital_value, status

    except Exception as e:
        print(f"❌ 火焰传感器读取错误: {e}")
        return 1, 1, "error"

def read_mq2_sensor():
    """读取MQ2烟雾传感器"""
    global mq2_adc  # 声明使用全局变量
    try:
        # 不再每次重新初始化ADC，使用全局初始化的ADC
        analog_value = mq2_adc.read()
        digital_value = mq2_do.value()

        print(f"🔍 MQ2原始读数 - 模拟: {analog_value}, 数字: {digital_value}")

        # 根据模拟值判断状态 (注意：MQ2传感器值越低表示烟雾浓度越高)
        if analog_value < MQ2_ALARM_THRESHOLD:
            status = "alarm"
        elif analog_value < MQ2_WARNING_THRESHOLD:
            status = "warning"
        else:
            status = "normal"

        return analog_value, digital_value, status

    except Exception as e:
        print(f"❌ MQ2传感器读取错误: {e}")
        # 如果读取失败，尝试重新初始化ADC
        try:
            mq2_adc = ADC(Pin(MQ2_AO_PIN))
            mq2_adc.width(ADC.WIDTH_12BIT)
            mq2_adc.atten(ADC.ATTN_11DB)  # 0-4095范围
            time.sleep(0.1)
            analog_value = mq2_adc.read()
            digital_value = mq2_do.value()
            print(f"🔄 MQ2重新初始化后读数 - 模拟: {analog_value}, 数字: {digital_value}")
            return analog_value, digital_value, "normal"
        except Exception as e2:
            print(f"❌ MQ2重新初始化也失败: {e2}")
            return 1500, 1, "normal"  # 返回正常值而不是错误值

def check_overall_status(flame_status, mq2_status):
    """检查整体状态"""
    if flame_status == "alarm" or mq2_status == "alarm":
        return "alarm"
    elif flame_status == "warning" or mq2_status == "warning":
        return "warning"
    else:
        return "normal"

# ==================== 状态指示函数 ====================
def update_led_status(status):
    """根据状态更新LED指示灯"""
    if status == "alarm":
        # 警报状态 - 快速闪烁
        for _ in range(3):
            led.value(1)
            time.sleep(0.1)
            led.value(0)
            time.sleep(0.1)
    elif status == "warning":
        # 警告状态 - 慢速闪烁
        led.value(1)
        time.sleep(0.5)
        led.value(0)
    else:
        # 正常状态 - 关闭
        led.value(0)

def update_oled_display(flame_analog, flame_status, mq2_analog, mq2_status, overall_status, count, host_ip, master_data=None):
    """更新OLED显示屏 - 包含主机和从机数据"""
    if not oled:
        return

    try:
        oled.fill(0)

        # 标题
        oled.text(f"{SLAVE_NAME}", 0, 0)

        # 从机传感器数据 - 火焰用图标显示
        flame_icon = "FIRE" if flame_analog == 0 else "OK"
        oled.text(f"{flame_icon}S:{mq2_analog}", 0, 16)

        # 显示主机数据
        if master_data:
            # 显示主机温度和湿度
            master_temp = master_data.get('temperature', 'N/A')
            master_humi = master_data.get('humidity', 'N/A')
            master_flame = master_data.get('flame_analog', 1)
            master_mq2 = master_data.get('mq2_analog', 'N/A')

            # 主机火焰用图标显示
            master_flame_icon = "FIRE" if master_flame == 0 else "OK"
            oled.text(f"{master_flame_icon}M:{master_mq2}", 0, 32)
            oled.text(f"T:{master_temp}C H:{master_humi}%", 0, 48)
        else:
            # 没有主机数据时显示从机状态
            status_text = "正常"
            if overall_status == "alarm":
                status_text = "警报"
            elif overall_status == "warning":
                status_text = "警告"

            oled.text(f"状态:{status_text}", 0, 32)

        # 序号
        oled.text(f"#{count}", 70, 48)

        # 主机IP (如果空间允许)
        if host_ip:
            ip_short = host_ip.split('.')[-2:]  # 只显示后两段
            ip_text = f"IP:{'.'.join(ip_short)}"
            oled.text(ip_text, 70, 0)

        oled.show()
    except Exception as e:
        print(f"❌ OLED显示更新失败: {e}")

def oled_show_message(title, message1="", message2=""):
    """在OLED上显示消息"""
    if not oled:
        return

    try:
        oled.fill(0)
        oled.text(title, 0, 0)
        if message1:
            oled.text(message1, 0, 16)
        if message2:
            oled.text(message2, 0, 32)
        oled.show()
    except Exception as e:
        print(f"❌ OLED消息显示失败: {e}")

# ==================== 主程序 ====================
def main():
    print("🚀 ESP32火灾报警系统从机启动")
    print("=" * 60)
    print(f"从机ID: {SLAVE_ID}")

    # 连接WiFi
    oled_show_message("WiFi连接中...")
    wlan = connect_wifi()
    if not wlan:
        print("❌ WiFi连接失败，程序退出")
        oled_show_message("WiFi失败", "程序退出")
        return

    # 获取本机IP地址
    slave_ip = wlan.ifconfig()[0]
    print(f"从机IP: {slave_ip}")
    oled_show_message("WiFi已连接", slave_ip[:12])

    # 初始化主机发现
    host_discovery = HostDiscovery()
    if not host_discovery.start_discovery():
        print("❌ 主机发现服务启动失败")
        oled_show_message("发现服务", "启动失败")
        return

    # 发现主机
    print("\n🔍 开始自动发现主机...")
    oled_show_message("寻找主机...")
    discovered_host_ip, discovered_host_port = host_discovery.discover_host()

    if not discovered_host_ip:
        print("❌ 无法发现主机，程序退出")
        oled_show_message("未找到主机", "程序退出")
        host_discovery.stop()
        return

    print(f"✅ 主机发现成功: {discovered_host_ip}:{discovered_host_port}")
    oled_show_message("主机已连接", discovered_host_ip[:12])

    # 创建UDP客户端
    udp_client = UDPSlaveClient(discovered_host_ip, discovered_host_port)
    if not udp_client.connect():
        print("❌ UDP客户端创建失败，程序退出")
        oled_show_message("UDP连接", "创建失败")
        return

    # 发送启动消息
    startup_msg = {
        "type": "startup",
        "slave_id": SLAVE_ID,
        "slave_name": SLAVE_NAME,
        "ip": slave_ip,
        "sensors": ["flame", "mq2_smoke"],
        "timestamp": time.time()
    }
    udp_client.send_data(startup_msg)

    print("📊 开始监测...")
    print("=" * 80)

    count = 0
    consecutive_errors = 0
    master_data = None  # 存储主机数据

    while True:
        count += 1

        try:
            # 读取传感器数据
            flame_analog, flame_digital, flame_status = read_flame_sensor()
            mq2_analog, mq2_digital, mq2_status = read_mq2_sensor()

            # 判断整体状态
            overall_status = check_overall_status(flame_status, mq2_status)

            # 更新LED状态指示
            update_led_status(overall_status)

            # 接收主机数据
            host_message = udp_client.receive_data()
            if host_message:
                host_data, sender_ip, sender_port = host_message
                if host_data.get('type') == 'master_data':
                    master_data = host_data.get('data', {})
                    print(f"📥 收到主机数据: 温度{master_data.get('temperature', 'N/A')}°C, 湿度{master_data.get('humidity', 'N/A')}%")

            # 更新OLED显示
            update_oled_display(flame_analog, flame_status, mq2_analog, mq2_status, overall_status, count, discovered_host_ip, master_data)

            # 构建发送数据
            sensor_data = {
                "type": "sensor_data",
                "slave_id": SLAVE_ID,
                "timestamp": time.time(),
                "sensors": {
                    "flame": {
                        "analog": flame_analog,
                        "digital": flame_digital,
                        "status": flame_status
                    },
                    "mq2_smoke": {
                        "analog": mq2_analog,
                        "digital": mq2_digital,
                        "status": mq2_status
                    }
                },
                "overall_status": overall_status,
                "sequence": count
            }

            # 发送数据
            success = udp_client.send_data(sensor_data)

            if success:
                consecutive_errors = 0
                print(f"[{count:3d}] 火焰:{flame_analog}({flame_status}) | 烟雾:{mq2_analog}({mq2_status}) | 整体:{overall_status} | ✅")
            else:
                consecutive_errors += 1
                print(f"[{count:3d}] 数据发送失败 | 重试次数: {consecutive_errors}")
                oled_show_message("发送失败", f"重试:{consecutive_errors}")

                # 如果连续失败次数过多，尝试重新连接
                if consecutive_errors >= MAX_RETRIES:
                    print("🔄 尝试重新连接...")
                    oled_show_message("重新连接中...")
                    udp_client.close()
                    time.sleep(1)
                    if udp_client.connect():
                        consecutive_errors = 0
                        print("✅ 重新连接成功")
                        oled_show_message("重连成功")
                    else:
                        print("❌ 重新连接失败")
                        oled_show_message("重连失败")

            # 检查WiFi连接状态
            if not wlan.isconnected():
                print("📡 WiFi连接断开，尝试重新连接...")
                oled_show_message("WiFi断开", "重新连接...")
                wlan = connect_wifi()
                if wlan:
                    # 重新发送启动消息
                    slave_ip = wlan.ifconfig()[0]
                    startup_msg["ip"] = slave_ip
                    startup_msg["timestamp"] = time.time()
                    udp_client.send_data(startup_msg)
                    oled_show_message("WiFi重连成功")
                else:
                    print("❌ WiFi重连失败")
                    oled_show_message("WiFi重连失败")
                    led.value(0)  # 关闭LED

        except Exception as e:
            print(f"❌ 主循环错误: {e}")
            consecutive_errors += 1
            led.value(0)  # 出错时关闭LED
            oled_show_message("系统错误", "请联系管理员")

        # 等待下次发送
        time.sleep(SEND_INTERVAL)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n程序被中断")
        # 清理资源
        led.value(0)
        if 'udp_client' in globals():
            udp_client.close()
        print("从机系统已安全关闭")
    except Exception as e:
        print(f"❌ 程序异常退出: {e}")
        # 重启系统
        print("🔄 系统将在5秒后重启...")
        time.sleep(5)
        machine.reset()