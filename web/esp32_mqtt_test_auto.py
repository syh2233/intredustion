#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ESP32 MQTT连接测试 - 自动发现版本
自动检测MQTT服务器地址
"""

import machine
import time
import json
import network
from machine import Pin, ADC
import socket

# WiFi配置
WIFI_SSID = "syh2031"
WIFI_PASSWORD = "12345678"

def connect_wifi():
    """连接WiFi网络"""
    print("正在连接WiFi...")
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
            print("✅ WiFi连接成功!")
            ip_config = wlan.ifconfig()
            print(f"ESP32 IP: {ip_config[0]}")
            print(f"网关: {ip_config[2]}")
            return ip_config
        else:
            print("❌ WiFi连接失败!")
            return None
    else:
        print("✅ WiFi已连接")
        ip_config = wlan.ifconfig()
        print(f"ESP32 IP: {ip_config[0]}")
        print(f"网关: {ip_config[2]}")
        return ip_config

def find_mqtt_servers(gateway_ip):
    """查找可能的MQTT服务器"""
    print("正在查找MQTT服务器...")

    # 从网关IP生成可能的MQTT服务器地址
    gateway_parts = gateway_ip.split('.')
    if len(gateway_parts) != 4:
        return []

    base_ip = f"{gateway_parts[0]}.{gateway_parts[1]}.{gateway_parts[2]}"

    # 可能的MQTT服务器地址
    possible_servers = []

    # 网关地址通常是路由器，不太可能运行MQTT
    # 尝试常见的内网IP
    for i in range(1, 255):
        if i != int(gateway_parts[3]):  # 跳过网关地址
            possible_servers.append(f"{base_ip}.{i}")
            if len(possible_servers) >= 10:  # 限制测试数量
                break

    return possible_servers

class SimpleMQTTClient:
    """简化的MQTT客户端"""
    def __init__(self, client_id, server, port):
        self.client_id = client_id
        self.server = server
        self.port = port
        self.sock = None
        self.connected = False

    def connect(self):
        """连接到MQTT服务器"""
        try:
            print(f"正在连接MQTT: {self.server}:{self.port}")

            # 创建socket连接
            self.sock = socket.socket()
            self.sock.settimeout(5)  # 减少超时时间
            addr = socket.getaddrinfo(self.server, self.port)[0][-1]
            self.sock.connect(addr)
            print("TCP连接成功")

            # 构建MQTT CONNECT消息
            protocol_name = b"MQTT"
            protocol_level = 4  # MQTT 3.1.1
            flags = 0x02  # Clean session
            keep_alive = 60

            # 可变头部
            var_header = bytearray()
            var_header.append(len(protocol_name))
            var_header.append(len(protocol_name))
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
                print("✅ MQTT连接成功!")
                return True
            else:
                print(f"❌ MQTT连接失败: {response}")
                return False

        except Exception as e:
            print(f"❌ MQTT连接异常: {e}")
            if self.sock:
                self.sock.close()
            self.connected = False
            return False

    def publish(self, topic, message):
        """发布消息"""
        if not self.connected:
            return False

        try:
            topic_bytes = topic.encode()
            message_bytes = message.encode()

            # 负载
            payload = bytearray()
            payload.append(len(topic_bytes) >> 8)
            payload.append(len(topic_bytes) & 0xFF)
            payload.extend(topic_bytes)
            payload.extend(message_bytes)

            # PUBLISH消息 (QoS 0)
            publish_msg = bytearray()
            publish_msg.append(0x30)  # PUBLISH
            publish_msg.append(len(payload))
            publish_msg.extend(payload)

            self.sock.send(publish_msg)
            return True

        except Exception as e:
            print(f"❌ 发布失败: {e}")
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

def test_tcp_connection(server, port):
    """测试TCP连接"""
    try:
        sock = socket.socket()
        sock.settimeout(3)
        addr = socket.getaddrinfo(server, port)[0][-1]
        sock.connect(addr)
        sock.close()
        return True
    except:
        return False

def generate_test_data():
    """生成测试数据"""
    import random
    return {
        "temperature": round(random.uniform(20.0, 30.0), 1),
        "humidity": round(random.uniform(50.0, 70.0), 1),
        "flame": random.randint(1000, 2000),
        "smoke": random.randint(300, 800),
        "light": random.randint(500, 1500),
        "sound": random.randint(50, 200)
    }

def main():
    """主函数"""
    print("ESP32 MQTT自动发现连接测试")
    print("=========================")
    print(f"设备ID: ESP32-TEST-{int(time.time())}")

    # 连接WiFi
    ip_config = connect_wifi()
    if not ip_config:
        print("❌ WiFi连接失败，无法继续")
        return

    # 获取网关地址
    gateway_ip = ip_config[2]
    print(f"网关地址: {gateway_ip}")

    # 查找可能的MQTT服务器
    possible_servers = find_mqtt_servers(gateway_ip)

    # 添加一些固定的测试地址
    test_servers = [
        "192.168.24.1",    # 路由器
        "192.168.24.2",    # 可能的服务器
        "192.168.24.100",  # 可能的服务器
        "192.168.1.100",   # 常见的服务器IP
        "test.mosquitto.org",  # 公共服务器
    ]

    # 去重并合并
    all_servers = list(set(test_servers + possible_servers[:10]))

    print(f"将测试 {len(all_servers)} 个可能的服务器地址...")

    # 测试每个服务器
    mqtt_client = None
    connected_server = None

    for server in all_servers:
        print(f"\n测试服务器: {server}")

        # 先测试TCP连接
        if test_tcp_connection(server, 1883):
            print("  ✅ TCP连接成功")

            # 尝试MQTT连接
            try:
                client_id = f"ESP32-TEST-{int(time.time())}"
                client = SimpleMQTTClient(client_id, server, 1883)

                if client.connect():
                    mqtt_client = client
                    connected_server = server
                    print(f"  ✅ MQTT连接成功!")
                    break
                else:
                    print("  ❌ MQTT连接失败")

            except Exception as e:
                print(f"  ❌ MQTT连接异常: {e}")
        else:
            print("  ❌ TCP连接失败")

    if not mqtt_client:
        print("❌ 所有服务器连接失败")
        print("请检查:")
        print("1. MQTT服务器是否正在运行")
        print("2. 防火墙是否允许1883端口")
        print("3. 网络连接是否正常")
        return

    print(f"✅ 已连接到MQTT服务器: {connected_server}")
    print("开始发送测试数据...")
    print("按 Ctrl+C 停止")

    try:
        count = 0
        while True:
            count += 1

            # 生成测试数据
            sensor_data = generate_test_data()

            # 发送数据
            data = {
                "device_id": mqtt_client.client_id,
                "timestamp": time.time(),
                "data": sensor_data,
                "status": {
                    "system_status": "normal",
                    "status_reason": "Test running",
                    "mqtt_server": connected_server
                },
                "location": "Test Location",
                "test_count": count
            }

            payload = json.dumps(data)
            topic = "esp32/fire_alarm/data"

            if mqtt_client.publish(topic, payload):
                print(f"[{count}] ✅ 数据已发送到 {connected_server}")
                print(f"    温度: {sensor_data['temperature']}°C")
            else:
                print(f"[{count}] ❌ 发送失败")

            # 每10秒发送一次
            time.sleep(10)

    except KeyboardInterrupt:
        print("\n用户中断")

    except Exception as e:
        print(f"主循环异常: {e}")

    finally:
        if mqtt_client:
            mqtt_client.disconnect()
            print("MQTT连接已断开")

    print("测试结束")

if __name__ == "__main__":
    main()