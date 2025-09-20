#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试MQTT端口映射是否正常工作
"""

import paho.mqtt.client as mqtt
import json
import time
import threading

# MQTT配置
LOCAL_BROKER = "127.0.0.1"
LOCAL_PORT = 1883
PUBLIC_BROKER = "22.tcp.cpolar.top"
PUBLIC_PORT = 14871

# 测试结果
test_results = {
    'local_connected': False,
    'public_connected': False,
    'local_messages_received': 0,
    'public_messages_received': 0,
    'local_publish_success': False,
    'public_publish_success': False
}

def on_connect(client, userdata, flags, rc, properties=None):
    """MQTT连接回调"""
    broker_type = userdata.get('type', 'unknown')
    if rc == 0:
        print(f"✅ {broker_type} MQTT连接成功！")
        test_results[f'{broker_type}_connected'] = True
        # 订阅测试主题
        client.subscribe("test/port_mapping")
        print(f"📡 {broker_type} 订阅主题: test/port_mapping")
    else:
        print(f"❌ {broker_type} MQTT连接失败，返回码: {rc}")

def on_message(client, userdata, msg):
    """MQTT消息接收回调"""
    broker_type = userdata.get('type', 'unknown')
    try:
        payload = msg.payload.decode('utf-8')
        print(f"📨 {broker_type} 收到消息: {payload}")
        test_results[f'{broker_type}_messages_received'] += 1
    except Exception as e:
        print(f"❌ {broker_type} 消息解析错误: {e}")

def on_publish(client, userdata, mid):
    """MQTT发布回调"""
    broker_type = userdata.get('type', 'unknown')
    print(f"📤 {broker_type} 消息发布成功: {mid}")
    test_results[f'{broker_type}_publish_success'] = True

def test_mqtt_connection(broker, port, broker_type):
    """测试MQTT连接"""
    print(f"\n🔍 测试 {broker_type} MQTT连接...")
    print(f"   服务器: {broker}:{port}")

    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, userdata={'type': broker_type})
    client.on_connect = on_connect
    client.on_message = on_message
    client.on_publish = on_publish

    try:
        client.connect(broker, port, 60)
        return client
    except Exception as e:
        print(f"❌ {broker_type} 连接失败: {e}")
        return None

def main():
    print("🚀 开始MQTT端口映射测试")
    print("=" * 50)

    # 创建两个客户端
    local_client = test_mqtt_connection(LOCAL_BROKER, LOCAL_PORT, "本地")
    public_client = test_mqtt_connection(PUBLIC_BROKER, PUBLIC_PORT, "公网")

    clients = []
    if local_client:
        clients.append(local_client)
    if public_client:
        clients.append(public_client)

    if not clients:
        print("❌ 没有成功的MQTT连接")
        return

    # 启动客户端循环
    for client in clients:
        client.loop_start()

    # 等待连接建立
    print("\n⏳ 等待连接建立...")
    time.sleep(3)

    # 测试消息发布
    test_message = {
        'timestamp': time.time(),
        'message': '端口映射测试消息',
        'test_id': 'port_mapping_test'
    }

    print("\n📤 发送测试消息...")

    # 本地客户端发布消息
    if local_client and test_results['local_connected']:
        try:
            local_client.publish("test/port_mapping", json.dumps(test_message))
            print("📡 本地客户端发布测试消息")
        except Exception as e:
            print(f"❌ 本地发布失败: {e}")

    # 公网客户端发布消息
    if public_client and test_results['public_connected']:
        try:
            public_client.publish("test/port_mapping", json.dumps(test_message))
            print("📡 公网客户端发布测试消息")
        except Exception as e:
            print(f"❌ 公网发布失败: {e}")

    # 等待消息接收
    print("\n⏳ 等待消息接收...")
    time.sleep(5)

    # 停止客户端
    for client in clients:
        client.loop_stop()
        client.disconnect()

    # 显示测试结果
    print("\n" + "=" * 50)
    print("📊 测试结果:")
    print("=" * 50)
    print(f"本地MQTT连接: {'✅ 成功' if test_results['local_connected'] else '❌ 失败'}")
    print(f"公网MQTT连接: {'✅ 成功' if test_results['public_connected'] else '❌ 失败'}")
    print(f"本地消息接收: {test_results['local_messages_received']} 条")
    print(f"公网消息接收: {test_results['public_messages_received']} 条")
    print(f"本地消息发布: {'✅ 成功' if test_results['local_publish_success'] else '❌ 失败'}")
    print(f"公网消息发布: {'✅ 成功' if test_results['public_publish_success'] else '❌ 失败'}")

    # 判断端口映射是否正常
    if test_results['public_connected']:
        print("\n🎉 公网MQTT端口映射正常工作！")
        print(f"   可以使用: {PUBLIC_BROKER}:{PUBLIC_PORT}")
    else:
        print("\n⚠️ 公网MQTT端口映射可能有问题")
        print("   请检查:")
        print("   1. cpolar隧道是否正常运行")
        print("   2. 防火墙设置")
        print("   3. MQTT broker配置")

if __name__ == "__main__":
    main()