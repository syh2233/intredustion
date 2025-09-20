#!/usr/bin/env python3
"""
MQTT协议调试测试
专门测试MQTT连接问题
"""

import machine
import time
import network
import socket

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
            print(f"ESP32 IP: {wlan.ifconfig()[0]}")
            return True
        else:
            print("❌ WiFi连接失败!")
            return False
    else:
        print("✅ WiFi已连接")
        print(f"ESP32 IP: {wlan.ifconfig()[0]}")
        return True

def test_mqtt_connection():
    """测试MQTT连接"""
    try:
        print(f"正在测试MQTT连接到 {MQTT_SERVER}:{MQTT_PORT}")

        # 创建socket连接
        sock = socket.socket()
        sock.settimeout(10)
        addr = socket.getaddrinfo(MQTT_SERVER, MQTT_PORT)[0][-1]
        sock.connect(addr)
        print("✅ TCP连接成功")

        # 构建MQTT CONNECT消息
        client_id = "ESP32-DEBUG-TEST"
        protocol_name = b"MQTT"
        protocol_level = 4  # MQTT 3.1.1
        flags = 0x02  # Clean session
        keep_alive = 60

        # 可变头部
        var_header = bytearray()
        # 协议名长度字段 (MSB + LSB)
        var_header.append(0)  # MSB of protocol name length
        var_header.append(len(protocol_name))  # LSB of protocol name length
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

        # 剩余长度
        remaining_length = len(var_header) + len(payload)

        # 完整消息
        connect_msg = bytearray()
        connect_msg.append(0x10)  # CONNECT
        connect_msg.append(remaining_length)
        connect_msg.extend(var_header)
        connect_msg.extend(payload)

        print(f"发送MQTT CONNECT消息 (长度: {len(connect_msg)})")
        print(f"消息内容: {[hex(b) for b in connect_msg]}")

        # 发送连接消息
        sock.send(connect_msg)

        # 等待CONNACK
        response = sock.recv(1024)

        print(f"收到响应: {response}")
        print(f"响应长度: {len(response)}")
        if len(response) > 0:
            print(f"响应字节: {[hex(b) for b in response]}")

        if len(response) >= 4 and response[0] == 0x20 and response[3] == 0x00:
            print("✅ MQTT连接成功!")

            # 测试发布消息
            print("测试发布消息...")
            topic = "esp32/debug/test"
            message = "Debug test message"

            # 构建PUBLISH消息
            topic_bytes = topic.encode()
            message_bytes = message.encode()

            publish_payload = bytearray()
            publish_payload.append(len(topic_bytes) >> 8)
            publish_payload.append(len(topic_bytes) & 0xFF)
            publish_payload.extend(topic_bytes)
            publish_payload.extend(message_bytes)

            publish_msg = bytearray()
            publish_msg.append(0x30)  # PUBLISH
            publish_msg.append(len(publish_payload))
            publish_msg.extend(publish_payload)

            sock.send(publish_msg)
            print("✅ 测试消息已发布")

            sock.close()
            return True
        else:
            print(f"❌ MQTT连接失败")
            sock.close()
            return False

    except Exception as e:
        print(f"❌ MQTT连接异常: {e}")
        return False

def main():
    """主函数"""
    print("ESP32 MQTT调试测试")
    print("=================")

    # 连接WiFi
    if not connect_wifi():
        print("❌ WiFi连接失败，无法继续")
        return

    # 测试MQTT连接
    if test_mqtt_connection():
        print("✅ MQTT连接测试成功")
    else:
        print("❌ MQTT连接测试失败")

if __name__ == "__main__":
    main()