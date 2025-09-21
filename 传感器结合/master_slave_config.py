'''
ESP32主机-从机配置文件
用于配置主机和从机的通信参数
'''

# ==================== WiFi配置 (主机和从机相同) ====================
WIFI_SSID = "syh2031"                # WiFi网络名称
WIFI_PASSWORD = "12345678"          # WiFi密码

# ==================== 主机配置 ====================
HOST_DEVICE_ID = "esp32_fire_alarm_01"  # 主机设备ID
HOST_NAME = "主机-01"                  # 主机显示名称
HOST_LOCATION = "宿舍监控中心"       # 主机安装位置

# ==================== 从机配置 ====================
# 从机1配置
SLAVE1_ID = "esp32_slave_01"          # 从机1设备ID
SLAVE1_NAME = "从机-01"               # 从机1显示名称
SLAVE1_LOCATION = "宿舍A栋101"        # 从机1安装位置

# 从机2配置 (可复制添加更多从机)
SLAVE2_ID = "esp32_slave_02"          # 从机2设备ID
SLAVE2_NAME = "从机-02"               # 从机2显示名称
SLAVE2_LOCATION = "宿舍A栋102"        # 从机2安装位置

# ==================== 通信配置 ====================
UDP_PORT = 8888                       # UDP通信端口
DISCOVERY_PORT = 8887                 # 主机发现端口
SEND_INTERVAL = 2.0                   # 数据发送间隔(秒)
MAX_RETRIES = 3                       # 最大重试次数
TIMEOUT = 5.0                         # 通信超时时间
DISCOVERY_TIMEOUT = 5.0               # 主机发现超时时间
DISCOVERY_ATTEMPTS = 3                # 主机发现尝试次数

# ==================== 传感器阈值配置 ====================
# 火焰传感器阈值 (值越低表示火焰越强)
FLAME_ALARM_THRESHOLD = 500           # 火焰警报阈值
FLAME_WARNING_THRESHOLD = 1000         # 火焰警告阈值

# MQ2烟雾传感器阈值 (值越低表示烟雾越浓)
MQ2_ALARM_THRESHOLD = 1000            # 烟雾警报阈值
MQ2_WARNING_THRESHOLD = 1500          # 烟雾警告阈值

# ==================== 硬件引脚配置 ====================
# 主机引脚配置 (保持原有main.py配置)
# 从机引脚配置
FLAME_PIN = 14                        # 火焰传感器模拟输入
MQ2_AO_PIN = 34                       # MQ2烟雾传感器模拟输入
MQ2_DO_PIN = 2                        # MQ2烟雾传感器数字输入
LED_PIN = 5                           # 状态指示灯
OLED_SDA = 26                         # OLED SDA引脚
OLED_SCL = 25                         # OLED SCL引脚

# ==================== 调试配置 ====================
DEBUG_MODE = True                     # 调试模式
SHOW_SLAVE_DATA = True                 # 显示从机数据
UDP_TIMEOUT = 0.1                      # UDP接收超时时间
SLAVE_TIMEOUT = 60                     # 从机超时时间(秒)

# ==================== 使用说明 ====================
'''
使用方法：
1. 主机程序：在main.py中import此配置文件
2. 从机程序：在esp32_slave_simple.py中import此配置文件
3. 根据实际网络环境修改WIFI_SSID和WIFI_PASSWORD
4. 根据需要修改从机配置和阈值设置
5. 确保主机和从机在同一WiFi网络下
6. 系统支持从机自动发现主机，无需手动配置主机IP

自动发现功能：
- 从机启动后会自动发送UDP广播寻找主机
- 主机收到请求后会响应自己的IP地址
- 发现成功后从机会自动建立连接
- 如果发现失败，从机会显示错误信息并退出
'''