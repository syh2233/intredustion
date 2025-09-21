'''
ESP32火灾报警系统 - 从机版本
通过WiFi UDP通信将火焰和烟雾传感器数据传输到主机
硬件配置：
- 火焰传感器: GPIO14 (模拟输入)
- MQ2烟雾传感器: GPIO34 (模拟输入), GPIO2 (数字输入)
- LED指示灯: GPIO5 (状态指示)
'''

from machine import Pin, ADC
import time
import network
import socket
import json
import ubinascii
import machine

# ==================== 常量配置 ====================
# 从机设备信息
SLAVE_ID = "esp32_slave_01"
SLAVE_NAME = "从机-01"

# WiFi配置 (与主机相同网络)
WIFI_SSID = "syh2031"
WIFI_PASSWORD = "12345678"

# 主机配置 (UDP通信)
HOST_IP = "192.168.1.100"  # 需要根据主机实际IP修改
HOST_PORT = 8888          # UDP通信端口

# GPIO配置
FLAME_PIN = 14        # 火焰传感器模拟输入
MQ2_AO_PIN = 34       # MQ2烟雾传感器模拟输入
MQ2_DO_PIN = 2        # MQ2烟雾传感器数字输入
LED_PIN = 5           # 状态指示灯

# 传感器阈值配置
FLAME_ALARM_THRESHOLD = 500      # 火焰警报阈值
FLAME_WARNING_THRESHOLD = 1000   # 火焰警告阈值
MQ2_ALARM_THRESHOLD = 1000       # 烟雾警报阈值
MQ2_WARNING_THRESHOLD = 1500     # 烟雾警告阈值

# 通信配置
SEND_INTERVAL = 2.0      # 数据发送间隔(秒)
MAX_RETRIES = 3         # 最大重试次数
TIMEOUT = 5.0           # 通信超时时间

# ==================== 硬件初始化 ====================
print("🔧 初始化从机硬件...")

# 初始化LED状态指示灯
led = Pin(LED_PIN, Pin.OUT)
led.value(0)  # 初始关闭

# 初始化火焰传感器 (模拟模式)
print(f"初始化火焰传感器 - GPIO{FLAME_PIN}")
flame_adc = ADC(Pin(FLAME_PIN))
flame_adc.atten(flame_adc.ATTN_11DB)  # 0-3.3V范围

# 初始化MQ2烟雾传感器
print(f"初始化MQ2烟雾传感器 - 模拟:GPIO{MQ2_AO_PIN}, 数字:GPIO{MQ2_DO_PIN}")
mq2_adc = ADC(Pin(MQ2_AO_PIN))
# 不设置MQ2的衰减，避免GPIO34的问题
mq2_do = Pin(MQ2_DO_PIN, Pin.IN)

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

# ==================== UDP通信模块 ====================
class UDPSlaveClient:
    def __init__(self, host_ip, host_port):
        self.host_ip = host_ip
        self.host_port = host_port
        self.socket = None
        self.connected = False

    def connect(self):
        """建立UDP socket"""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.socket.settimeout(TIMEOUT)
            self.connected = True
            print(f"✅ UDP客户端创建成功，目标: {self.host_ip}:{self.host_port}")
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
            self.connected = False
            print("UDP连接已关闭")

# ==================== 传感器读取函数 ====================
def read_flame_sensor():
    """读取火焰传感器"""
    try:
        analog_value = flame_adc.read()

        # 根据模拟值判断状态
        if analog_value < FLAME_ALARM_THRESHOLD:
            status = "alarm"
            digital = 0
        elif analog_value < FLAME_WARNING_THRESHOLD:
            status = "warning"
            digital = 0
        else:
            status = "normal"
            digital = 1

        return analog_value, digital, status

    except Exception as e:
        print(f"❌ 火焰传感器读取错误: {e}")
        return 4095, 1, "error"

def read_mq2_sensor():
    """读取MQ2烟雾传感器"""
    try:
        # 重新初始化ADC以避免GPIO34的问题
        global mq2_adc
        mq2_adc = ADC(Pin(MQ2_AO_PIN))
        time.sleep(0.05)  # 短暂延时

        analog_value = mq2_adc.read()
        digital_value = mq2_do.value()

        # 根据模拟值判断状态
        if analog_value < MQ2_ALARM_THRESHOLD:
            status = "alarm"
        elif analog_value < MQ2_WARNING_THRESHOLD:
            status = "warning"
        else:
            status = "normal"

        return analog_value, digital_value, status

    except Exception as e:
        print(f"❌ MQ2传感器读取错误: {e}")
        return 4095, 1, "error"

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

# ==================== 主程序 ====================
def main():
    print("🚀 ESP32火灾报警系统从机启动")
    print("=" * 60)
    print(f"从机ID: {SLAVE_ID}")
    print(f"主机地址: {HOST_IP}:{HOST_PORT}")

    # 连接WiFi
    wlan = connect_wifi()
    if not wlan:
        print("❌ WiFi连接失败，程序退出")
        return

    # 创建UDP客户端
    udp_client = UDPSlaveClient(HOST_IP, HOST_PORT)
    if not udp_client.connect():
        print("❌ UDP客户端创建失败，程序退出")
        return

    # 发送启动消息
    startup_msg = {
        "type": "startup",
        "slave_id": SLAVE_ID,
        "slave_name": SLAVE_NAME,
        "ip": wlan.ifconfig()[0],
        "sensors": ["flame", "mq2_smoke"],
        "timestamp": time.time()
    }
    udp_client.send_data(startup_msg)

    print("📊 开始监测...")
    print("=" * 80)

    count = 0
    consecutive_errors = 0

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

                # 如果连续失败次数过多，尝试重新连接
                if consecutive_errors >= MAX_RETRIES:
                    print("🔄 尝试重新连接...")
                    udp_client.close()
                    time.sleep(1)
                    if udp_client.connect():
                        consecutive_errors = 0
                        print("✅ 重新连接成功")
                    else:
                        print("❌ 重新连接失败")

            # 检查WiFi连接状态
            if not wlan.isconnected():
                print("📡 WiFi连接断开，尝试重新连接...")
                wlan = connect_wifi()
                if wlan:
                    # 重新发送启动消息
                    startup_msg["timestamp"] = time.time()
                    udp_client.send_data(startup_msg)
                else:
                    print("❌ WiFi重连失败")
                    led.value(0)  # 关闭LED

        except Exception as e:
            print(f"❌ 主循环错误: {e}")
            consecutive_errors += 1
            led.value(0)  # 出错时关闭LED

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