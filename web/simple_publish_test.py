#!/usr/bin/env python3
"""
简单的MQTT发布测试
测试修复后的发布功能
"""

import machine
import time
import network
import socket
import json

# WiFi配置
WIFI_SSID = "syh2031"
WIFI_PASSWORD = "12345678"

# MQTT配置
MQTT_SERVER = "192.168.24.32"
MQTT_PORT = 1883

def connect_wifi():
    """连接WiFi网络"""
    print("正在连接WiFi...")
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)

    if not wlan.isconnected():
        wlan.connect(WIFI_SSID, WIFI_PASSWORD)
        timeout = 0
        while not wlan.isconnected() and timeout < 30:
            time.sleep(1)
            timeout += 1
            print(".", end="")
        print()
    else:
        print("✅ WiFi已连接")

    if wlan.isconnected():
        print(f"ESP32 IP: {wlan.ifconfig()[0]}")
        return True
    else:
        print("❌ WiFi连接失败!")
        return False

def test_mqtt_connect():
    """测试MQTT连接"""
    try:
        print(f"连接MQTT: {MQTT_SERVER}:{MQTT_PORT}")
        sock = socket.socket()
        sock.settimeout(10)
        addr = socket.getaddrinfo(MQTT_SERVER, MQTT_PORT)[0][-1]
        sock.connect(addr)
        print("✅ TCP连接成功")

        # 构建MQTT CONNECT消息
        client_id = "ESP32-SIMPLE-TEST"
        protocol_name = b"MQTT"
        protocol_level = 4
        flags = 0x02
        keep_alive = 60

        # 可变头部
        var_header = bytearray()
        var_header.append(0)  # MSB
        var_header.append(len(protocol_name))  # LSB
        var_header.extend(protocol_name)
        var_header.append(protocol_level)
        var_header.append(flags)
        var_header.append(keep_alive >> 8)
        var_header.append(keep_alive & 0xFF)

        # 负载
        payload = bytearray()
        client_id_bytes = client_id.encode()
        payload.append(len(client_id_bytes) >> 8)
        payload.append(len(client_id_bytes) & 0xFF)
        payload.extend(client_id_bytes)

        # 完整消息
        remaining_length = len(var_header) + len(payload)
        connect_msg = bytearray()
        connect_msg.append(0x10)  # CONNECT
        connect_msg.append(remaining_length)
        connect_msg.extend(var_header)
        connect_msg.extend(payload)

        sock.send(connect_msg)

        # 等待CONNACK
        response = sock.recv(1024)
        if len(response) >= 4 and response[0] == 0x20 and response[3] == 0x00:
            print("✅ MQTT连接成功!")
            return sock
        else:
            print(f"❌ MQTT连接失败: {response}")
            sock.close()
            return None

    except Exception as e:
        print(f"❌ MQTT连接异常: {e}")
        return None

def test_simple_publish(sock):
    """测试简单消息发布"""
    try:
        topic = "esp32/test/simple"
        message = "Hello MQTT!"

        print(f"发布消息到主题: {topic}")
        print(f"消息内容: {message}")

        topic_bytes = topic.encode()
        message_bytes = message.encode()

        # 计算长度
        topic_length = len(topic_bytes)
        message_length = len(message_bytes)
        remaining_length = 2 + topic_length + message_length

        print(f"剩余长度: {remaining_length}")

        # 构建PUBLISH消息
        publish_msg = bytearray()
        publish_msg.append(0x30)  # PUBLISH QoS 0
        publish_msg.append(remaining_length)
        publish_msg.append(topic_length >> 8)
        publish_msg.append(topic_length & 0xFF)
        publish_msg.extend(topic_bytes)
        publish_msg.extend(message_bytes)

        print(f"PUBLISH消息: {[hex(b) for b in publish_msg]}")

        sock.send(publish_msg)
        print("✅ 消息发布成功!")
        return True

    except Exception as e:
        print(f"❌ 发布失败: {e}")
        return False

def main():
    """主函数"""
    print("ESP32 简单MQTT发布测试")
    print("=====================")

    # 连接WiFi
    if not connect_wifi():
        print("❌ WiFi连接失败")
        return

    # 连接MQTT
    sock = test_mqtt_connect()
    if not sock:
        print("❌ MQTT连接失败")
        return

    # 测试发布
    try:
        for i in range(3):
            print(f"\n--- 测试 {i+1} ---")
            if test_simple_publish(sock):
                print("✅ 测试成功")
            else:
                print("❌ 测试失败")
                break
            time.sleep(2)

    finally:
        sock.close()
        print("连接已关闭")

if __name__ == "__main__":
    main()