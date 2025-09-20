#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试数据流向：ESP32 -> 公网MQTT -> 本地web应用
"""

import paho.mqtt.client as mqtt
import json
import time
import threading

# MQTT配置
PUBLIC_BROKER = "22.tcp.cpolar.top"
PUBLIC_PORT = 14871

# 测试结果
messages_received = 0

def on_connect(client, userdata, flags, rc):
    """MQTT连接回调"""
    if rc == 0:
        print("✅ 成功连接到公网MQTT服务器")
        # 订阅ESP32数据主题
        client.subscribe("esp32/+/data/json")
        client.subscribe("esp32/+/alert/#")
        print("📡 已订阅ESP32数据主题")
    else:
        print(f"❌ 连接失败，返回码: {rc}")

def on_message(client, userdata, msg):
    """MQTT消息接收回调"""
    global messages_received
    try:
        topic = msg.topic
        payload = msg.payload.decode('utf-8')

        messages_received += 1
        print(f"\n📨 收到第 {messages_received} 条消息:")
        print(f"   主题: {topic}")
        print(f"   内容: {payload}")

        # 解析JSON数据
        try:
            data = json.loads(payload)
            print(f"   解析数据: {data}")

            # 检查是否是ESP32数据
            if 'device_id' in data and 'temperature' in data:
                print(f"   ✅ 这是ESP32传感器数据")
                device_id = data.get('device_id', 'unknown')
                temperature = data.get('temperature', 'N/A')
                flame = data.get('flame', 'N/A')
                smoke = data.get('smoke', 'N/A')
                print(f"   📊 设备: {device_id}")
                print(f"   🌡️ 温度: {temperature}°C")
                print(f"   🔥 火焰: {flame}")
                print(f"   💨 烟雾: {smoke}")

        except json.JSONDecodeError:
            print(f"   ⚠️ 非JSON格式消息")

    except Exception as e:
        print(f"❌ 消息处理错误: {e}")

def main():
    print("🚀 测试数据流向: ESP32 -> 公网MQTT -> 本地接收")
    print("=" * 60)
    print(f"📡 连接到公网MQTT: {PUBLIC_BROKER}:{PUBLIC_PORT}")
    print("⏳ 等待ESP32发送数据...")
    print("💡 请确保ESP32已烧录更新后的fire_alarm_oled.py并正在运行")
    print("=" * 60)

    # 创建MQTT客户端
    client = mqtt.Client()
    client.on_connect = on_connect
    client.on_message = on_message

    try:
        # 连接到公网MQTT
        client.connect(PUBLIC_BROKER, PUBLIC_PORT, 60)
        client.loop_start()

        # 运行5分钟或手动停止
        start_time = time.time()
        timeout = 300  # 5分钟

        while time.time() - start_time < timeout:
            if messages_received > 0:
                print(f"\n📊 已接收 {messages_received} 条消息，继续监听...")
            time.sleep(10)

        print(f"\n⏰ 测试结束，共接收 {messages_received} 条消息")

        if messages_received > 0:
            print("🎉 数据流向测试成功！")
            print("✅ ESP32 -> 公网MQTT -> 本地接收 正常工作")
        else:
            print("⚠️ 没有收到任何数据")
            print("请检查:")
            print("1. ESP32是否正在运行")
            print("2. ESP32的MQTT配置是否正确")
            print("3. 网络连接是否正常")

    except Exception as e:
        print(f"❌ 测试失败: {e}")

    finally:
        try:
            client.loop_stop()
            client.disconnect()
        except:
            pass

if __name__ == "__main__":
    main()