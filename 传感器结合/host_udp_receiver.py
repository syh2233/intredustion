'''
ESP32火灾报警系统 - 主机UDP接收程序
接收从机发送的传感器数据并处理
'''

import socket
import json
import time
import threading
from datetime import datetime
import sqlite3

# ==================== 配置常量 ====================
# UDP服务器配置
UDP_HOST = '0.0.0.0'  # 监听所有网络接口
UDP_PORT = 8888       # UDP监听端口

# 数据库配置
DB_NAME = 'slave_sensor_data.db'

# 日志配置
LOG_FILE = 'udp_receiver.log'

# ==================== 数据库初始化 ====================
def init_database():
    """初始化数据库"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    # 创建从机数据表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS slave_sensor_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            slave_id TEXT NOT NULL,
            timestamp REAL NOT NULL,
            flame_analog INTEGER NOT NULL,
            flame_digital INTEGER NOT NULL,
            flame_status TEXT NOT NULL,
            mq2_analog INTEGER NOT NULL,
            mq2_digital INTEGER NOT NULL,
            mq2_status TEXT NOT NULL,
            overall_status TEXT NOT NULL,
            sequence INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # 创建从机信息表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS slave_info (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            slave_id TEXT UNIQUE NOT NULL,
            slave_name TEXT,
            ip_address TEXT,
            last_seen TIMESTAMP,
            status TEXT DEFAULT 'online',
            sensors TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # 创建警报历史表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS slave_alert_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            slave_id TEXT NOT NULL,
            alert_type TEXT NOT NULL,
            severity TEXT NOT NULL,
            flame_value INTEGER,
            mq2_value INTEGER,
            message TEXT,
            resolved BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    conn.commit()
    conn.close()
    print("✅ 数据库初始化完成")

# ==================== 日志功能 ====================
def log_message(message):
    """记录日志消息"""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    log_entry = f"[{timestamp}] {message}"
    print(log_entry)

    # 写入日志文件
    try:
        with open(LOG_FILE, 'a', encoding='utf-8') as f:
            f.write(log_entry + '\n')
    except Exception as e:
        print(f"日志写入失败: {e}")

# ==================== 数据处理函数 ====================
def process_sensor_data(data):
    """处理传感器数据"""
    try:
        # 验证数据格式
        required_fields = ['slave_id', 'timestamp', 'sensors', 'overall_status', 'sequence']
        for field in required_fields:
            if field not in data:
                log_message(f"❌ 数据缺少必需字段: {field}")
                return False

        slave_id = data['slave_id']
        timestamp = data['timestamp']
        sequence = data['sequence']
        overall_status = data['overall_status']

        # 提取传感器数据
        flame_data = data['sensors'].get('flame', {})
        mq2_data = data['sensors'].get('mq2_smoke', {})

        flame_analog = flame_data.get('analog', 0)
        flame_digital = flame_data.get('digital', 1)
        flame_status = flame_data.get('status', 'normal')

        mq2_analog = mq2_data.get('analog', 0)
        mq2_digital = mq2_data.get('digital', 1)
        mq2_status = mq2_data.get('status', 'normal')

        # 保存到数据库
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()

        # 插入传感器数据
        cursor.execute('''
            INSERT INTO slave_sensor_data
            (slave_id, timestamp, flame_analog, flame_digital, flame_status,
             mq2_analog, mq2_digital, mq2_status, overall_status, sequence)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (slave_id, timestamp, flame_analog, flame_digital, flame_status,
              mq2_analog, mq2_digital, mq2_status, overall_status, sequence))

        # 更新从机信息
        cursor.execute('''
            INSERT OR REPLACE INTO slave_info
            (slave_id, last_seen, status)
            VALUES (?, datetime('now'), 'online')
        ''', (slave_id,))

        # 检查是否需要记录警报
        if overall_status in ['alarm', 'warning']:
            alert_type = 'fire' if overall_status == 'alarm' else 'warning'
            severity = 'high' if overall_status == 'alarm' else 'medium'

            cursor.execute('''
                INSERT INTO slave_alert_history
                (slave_id, alert_type, severity, flame_value, mq2_value, message)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (slave_id, alert_type, severity, flame_analog, mq2_analog,
                  f"从机{slave_id}检测到{overall_status}状态"))

        conn.commit()
        conn.close()

        # 打印处理结果
        log_message(f"✅ 数据处理成功 - 从机:{slave_id} 序列:{sequence} 状态:{overall_status}")
        log_message(f"   火焰:{flame_analog}({flame_status}) 烟雾:{mq2_analog}({mq2_status})")

        # 如果是警报状态，特别标记
        if overall_status == 'alarm':
            log_message(f"🚨 警报！从机{slave_id}检测到火灾风险！")
        elif overall_status == 'warning':
            log_message(f"⚠️  警告！从机{slave_id}环境异常！")

        return True

    except Exception as e:
        log_message(f"❌ 数据处理错误: {e}")
        return False

def process_startup_message(data):
    """处理从机启动消息"""
    try:
        slave_id = data.get('slave_id')
        slave_name = data.get('slave_name', 'Unknown')
        ip_address = data.get('ip')
        sensors = data.get('sensors', [])

        log_message(f"📱 从机启动 - ID:{slave_id} 名称:{slave_name} IP:{ip_address}")

        # 更新从机信息
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()

        cursor.execute('''
            INSERT OR REPLACE INTO slave_info
            (slave_id, slave_name, ip_address, last_seen, status, sensors)
            VALUES (?, ?, ?, datetime('now'), 'online', ?)
        ''', (slave_id, slave_name, ip_address, json.dumps(sensors)))

        conn.commit()
        conn.close()

        return True

    except Exception as e:
        log_message(f"❌ 启动消息处理错误: {e}")
        return False

# ==================== UDP服务器类 ====================
class UDPServer:
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.socket = None
        self.running = False

    def start(self):
        """启动UDP服务器"""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.socket.bind((self.host, self.port))
            self.running = True
            log_message(f"✅ UDP服务器启动成功，监听 {self.host}:{self.port}")
            return True
        except Exception as e:
            log_message(f"❌ UDP服务器启动失败: {e}")
            return False

    def receive_data(self):
        """接收数据的主循环"""
        log_message("📡 开始监听从机数据...")

        while self.running:
            try:
                # 接收数据
                data, addr = self.socket.recvfrom(1024)
                client_ip = addr[0]
                client_port = addr[1]

                # 解析JSON数据
                try:
                    json_data = json.loads(data.decode('utf-8'))
                except json.JSONDecodeError:
                    log_message(f"❌ JSON解析失败 - 来自 {client_ip}:{client_port}")
                    continue

                # 记录接收信息
                message_type = json_data.get('type', 'unknown')
                log_message(f"📨 收到{message_type}消息 - 来自 {client_ip}:{client_port}")

                # 根据消息类型处理
                if message_type == 'sensor_data':
                    process_sensor_data(json_data)
                elif message_type == 'startup':
                    process_startup_message(json_data)
                elif message_type == 'test':
                    log_message(f"🔧 测试消息 - 从机:{json_data.get('slave_id')}")
                else:
                    log_message(f"⚠️  未知消息类型: {message_type}")

            except socket.timeout:
                continue
            except Exception as e:
                log_message(f"❌ 数据接收错误: {e}")
                time.sleep(1)  # 防止错误循环

    def stop(self):
        """停止UDP服务器"""
        self.running = False
        if self.socket:
            self.socket.close()
        log_message("UDP服务器已停止")

# ==================== 状态监控函数 ====================
def monitor_slaves():
    """监控从机状态"""
    while True:
        try:
            time.sleep(60)  # 每分钟检查一次

            conn = sqlite3.connect(DB_NAME)
            cursor = conn.cursor()

            # 检查超过5分钟未更新的从机
            cursor.execute('''
                SELECT slave_id, last_seen FROM slave_info
                WHERE datetime(last_seen) < datetime('now', '-5 minutes')
            ''')
            offline_slaves = cursor.fetchall()

            for slave_id, last_seen in offline_slaves:
                log_message(f"⚠️  从机 {slave_id} 可能离线 (最后活动: {last_seen})")

                # 标记为离线
                cursor.execute('''
                    UPDATE slave_info SET status = 'offline' WHERE slave_id = ?
                ''', (slave_id,))

            conn.commit()
            conn.close()

        except Exception as e:
            log_message(f"❌ 状态监控错误: {e}")

# ==================== 主程序 ====================
def main():
    print("🚀 ESP32火灾报警系统主机UDP接收程序启动")
    print("=" * 60)

    # 初始化数据库
    init_database()

    # 创建UDP服务器
    udp_server = UDPServer(UDP_HOST, UDP_PORT)
    if not udp_server.start():
        print("❌ UDP服务器启动失败，程序退出")
        return

    # 启动状态监控线程
    monitor_thread = threading.Thread(target=monitor_slaves, daemon=True)
    monitor_thread.start()
    log_message("✅ 从机状态监控已启动")

    try:
        # 主循环
        udp_server.receive_data()

    except KeyboardInterrupt:
        log_message("\n程序被用户中断")
    except Exception as e:
        log_message(f"❌ 程序异常: {e}")
    finally:
        udp_server.stop()
        log_message("程序已安全退出")

if __name__ == "__main__":
    main()