#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试报警通知修复效果
"""

import json
import time
import paho.mqtt.client as mqtt
import threading

# MQTT配置
MQTT_BROKER = "localhost"
MQTT_PORT = 1883
TEST_DEVICE_ID = "esp32_fire_alarm_01"

def on_connect(client, userdata, flags, rc):
    """MQTT连接回调"""
    print(f"Connected to MQTT broker with result code {rc}")
    # 订阅所有主题来查看消息
    client.subscribe("esp32/#")

def on_message(client, userdata, msg):
    """MQTT消息回调"""
    print(f"Received message: {msg.topic} - {msg.payload.decode()}")

def test_alert_message():
    """测试报警消息"""
    client = mqtt.Client()
    client.on_connect = on_connect
    client.on_message = on_message

    try:
        client.connect(MQTT_BROKER, MQTT_PORT, 60)
        client.loop_start()

        # 等待连接建立
        time.sleep(2)

        # 发送测试报警消息
        alert_message = {
            "message": "检测到火灾风险！",
            "type": "fire",
            "data": {
                "timestamp": int(time.time()),
                "temperature": 45,
                "smoke": 1329,
                "light": 6816.7,
                "humidity": 50,
                "status": "alarm",
                "flame": 800,
                "device_id": TEST_DEVICE_ID
            },
            "level": "high"
        }

        topic = f"esp32/{TEST_DEVICE_ID}/alert/fire"
        payload = json.dumps(alert_message)

        print(f"Sending alert message to {topic}: {payload}")
        client.publish(topic, payload)

        # 等待消息处理
        time.sleep(5)

    except Exception as e:
        print(f"Error: {e}")
    finally:
        client.loop_stop()
        client.disconnect()

if __name__ == "__main__":
    print("Testing alert notification fix...")
    test_alert_message()
    print("Test completed.")