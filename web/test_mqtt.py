#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试MQTT连接和数据接收
"""

import paho.mqtt.client as mqtt
import json
import time

def on_connect(client, userdata, flags, rc):
    """MQTT连接回调"""
    print(f"MQTT连接成功，返回码: {rc}")
    # 订阅主题
    client.subscribe('esp32/+/data/json')
    client.subscribe('esp32/+/alert/#')
    client.subscribe('esp32/+/status/#')
    print("MQTT主题订阅: esp32/+/data/json, esp32/+/alert/#, esp32/+/status/#")

def on_disconnect(client, userdata, rc):
    """MQTT断开连接回调"""
    if rc != 0:
        print(f"MQTT意外断开连接，返回码: {rc}")
    else:
        print("MQTT正常断开连接")

def on_message(client, userdata, msg):
    """MQTT消息接收回调"""
    try:
        topic = msg.topic
        payload = msg.payload.decode('utf-8') if isinstance(msg.payload, bytes) else msg.payload

        print(f"收到MQTT消息 - 主题: {topic}")
        print(f"消息内容: {payload}")

        if '/data/json' in topic:
            data = json.loads(payload)
            print(f"解析的传感器数据: {data}")

    except Exception as e:
        print(f"处理MQTT消息错误: {e}")

# 创建MQTT客户端
client = mqtt.Client()

# 设置回调
client.on_connect = on_connect
client.on_disconnect = on_disconnect
client.on_message = on_message

# 连接MQTT broker
try:
    print("正在连接MQTT broker...")
    client.connect("22.tcp.cpolar.top", 14871, 60)
    client.loop_start()
    print("MQTT客户端启动")

    # 监听30秒
    print("开始监听MQTT消息(30秒)...")
    time.sleep(30)

except Exception as e:
    print(f"MQTT连接失败: {e}")
finally:
    client.loop_stop()
    client.disconnect()
    print("测试完成")