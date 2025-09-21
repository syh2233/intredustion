'''
ESP32主机-从机通信测试程序
用于测试主机和从机之间的UDP通信
'''

import socket
import json
import time
import threading
from datetime import datetime

# 测试配置
TEST_UDP_PORT = 8888
TEST_HOST_IP = '0.0.0.0'  # 监听所有接口
TEST_TIMEOUT = 5.0

class MasterSlaveTester:
    def __init__(self):
        self.socket = None
        self.running = False
        self.received_messages = []

    def start_test_server(self):
        """启动测试服务器 (模拟主机)"""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.socket.bind((TEST_HOST_IP, TEST_UDP_PORT))
            self.socket.settimeout(TEST_TIMEOUT)
            self.running = True
            print(f"✅ 测试服务器启动成功，监听端口: {TEST_UDP_PORT}")
            return True
        except Exception as e:
            print(f"❌ 测试服务器启动失败: {e}")
            return False

    def send_test_message(self, target_ip, target_port, message):
        """发送测试消息 (模拟从机)"""
        try:
            test_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            test_socket.settimeout(TEST_TIMEOUT)

            # 发送测试消息
            json_data = json.dumps(message)
            test_socket.sendto(json_data.encode(), (target_ip, target_port))
            print(f"📤 测试消息已发送到 {target_ip}:{target_port}")

            test_socket.close()
            return True
        except Exception as e:
            print(f"❌ 发送测试消息失败: {e}")
            return False

    def receive_test_message(self):
        """接收测试消息"""
        if not self.running or not self.socket:
            return None

        try:
            data, addr = self.socket.recvfrom(512)
            client_ip = addr[0]
            client_port = addr[1]

            # 解析JSON数据
            try:
                json_data = json.loads(data.decode('utf-8'))
                message_info = {
                    'data': json_data,
                    'client_ip': client_ip,
                    'client_port': client_port,
                    'timestamp': time.time()
                }
                self.received_messages.append(message_info)
                return message_info
            except json.JSONDecodeError:
                print(f"❌ JSON解析失败 - 来自 {client_ip}:{client_port}")
                return None

        except socket.timeout:
            return None
        except Exception as e:
            print(f"❌ 接收测试消息错误: {e}")
            return None

    def test_slave_communication(self, slave_ip):
        """测试从机通信"""
        print(f"\n🔍 测试从机通信: {slave_ip}")

        # 创建测试消息
        test_messages = [
            {
                "type": "startup",
                "slave_id": "test_slave_01",
                "slave_name": "测试从机-01",
                "ip": slave_ip,
                "sensors": ["flame", "mq2_smoke"],
                "timestamp": time.time()
            },
            {
                "type": "sensor_data",
                "slave_id": "test_slave_01",
                "timestamp": time.time(),
                "sensors": {
                    "flame": {
                        "analog": 1200,
                        "digital": 1,
                        "status": "normal"
                    },
                    "mq2_smoke": {
                        "analog": 1800,
                        "digital": 1,
                        "status": "normal"
                    }
                },
                "overall_status": "normal",
                "sequence": 1
            },
            {
                "type": "sensor_data",
                "slave_id": "test_slave_01",
                "timestamp": time.time(),
                "sensors": {
                    "flame": {
                        "analog": 300,
                        "digital": 0,
                        "status": "alarm"
                    },
                    "mq2_smoke": {
                        "analog": 800,
                        "digital": 0,
                        "status": "alarm"
                    }
                },
                "overall_status": "alarm",
                "sequence": 2
            }
        ]

        # 发送测试消息
        for i, message in enumerate(test_messages):
            print(f"  发送测试消息 {i+1}: {message['type']}")
            success = self.send_test_message(slave_ip, TEST_UDP_PORT, message)
            if not success:
                print(f"  ❌ 消息 {i+1} 发送失败")
                return False

            # 等待接收
            time.sleep(0.5)

        # 接收响应
        received_count = 0
        for _ in range(10):  # 等待最多5秒
            message_info = self.receive_test_message()
            if message_info:
                received_count += 1
                print(f"  ✅ 收到消息 {received_count}: {message_info['data']['type']}")

                # 显示消息详情
                data = message_info['data']
                if 'type' in data:
                    print(f"     类型: {data['type']}")
                if 'slave_id' in data:
                    print(f"     从机ID: {data['slave_id']}")
                if 'overall_status' in data:
                    print(f"     状态: {data['overall_status']}")

            time.sleep(0.5)

        print(f"  📊 通信结果: 发送{len(test_messages)}条，收到{received_count}条")
        return received_count > 0

    def run_interactive_test(self):
        """运行交互式测试"""
        print("🚀 ESP32主机-从机通信测试")
        print("=" * 50)

        # 启动测试服务器
        if not self.start_test_server():
            print("❌ 无法启动测试服务器")
            return

        print("\n📋 测试选项:")
        print("1. 测试单个从机")
        print("2. 连续监控模式")
        print("3. 退出")

        while True:
            choice = input("\n请选择测试模式 (1-3): ").strip()

            if choice == '1':
                slave_ip = input("请输入从机IP地址: ").strip()
                if slave_ip:
                    self.test_slave_communication(slave_ip)
                else:
                    print("❌ 请输入有效的IP地址")

            elif choice == '2':
                print("🔄 进入连续监控模式 (按Ctrl+C退出)...")
                print("等待从机连接...")

                try:
                    while True:
                        message_info = self.receive_test_message()
                        if message_info:
                            data = message_info['data']
                            client_ip = message_info['client_ip']
                            timestamp = datetime.fromtimestamp(message_info['timestamp'])

                            print(f"\n📨 收到消息 [{timestamp}]")
                            print(f"   来源: {client_ip}")
                            print(f"   类型: {data.get('type', 'unknown')}")
                            print(f"   从机: {data.get('slave_id', 'unknown')}")

                            if 'sensors' in data:
                                sensors = data['sensors']
                                if 'flame' in sensors:
                                    flame = sensors['flame']
                                    print(f"   火焰: {flame.get('analog', 'N/A')}({flame.get('status', 'unknown')})")
                                if 'mq2_smoke' in sensors:
                                    mq2 = sensors['mq2_smoke']
                                    print(f"   烟雾: {mq2.get('analog', 'N/A')}({mq2.get('status', 'unknown')})")

                            if 'overall_status' in data:
                                status = data['overall_status']
                                print(f"   整体状态: {status}")
                                if status == 'alarm':
                                    print("   🚨 警报状态！")
                                elif status == 'warning':
                                    print("   ⚠️  警告状态！")

                            print("-" * 40)

                except KeyboardInterrupt:
                    print("\n⏹️  监控模式已停止")

            elif choice == '3':
                print("👋 退出测试")
                break

            else:
                print("❌ 无效选择，请重新输入")

    def stop(self):
        """停止测试服务器"""
        if self.socket:
            self.socket.close()
        self.running = False
        print("测试服务器已停止")

def main():
    """主函数"""
    tester = MasterSlaveTester()

    try:
        tester.run_interactive_test()
    except KeyboardInterrupt:
        print("\n程序被用户中断")
    except Exception as e:
        print(f"❌ 程序异常: {e}")
    finally:
        tester.stop()

if __name__ == "__main__":
    main()