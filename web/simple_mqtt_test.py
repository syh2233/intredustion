#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简单MQTT端口映射测试
"""

import paho.mqtt.client as mqtt
import time

# MQTT配置
LOCAL_BROKER = "127.0.0.1"
LOCAL_PORT = 1883
PUBLIC_BROKER = "22.tcp.cpolar.top"
PUBLIC_PORT = 14871

def test_connection(broker, port, name):
    """测试单个MQTT连接"""
    print(f"\n🔍 测试 {name} MQTT连接...")
    print(f"   地址: {broker}:{port}")

    def on_connect(client, userdata, flags, rc):
        if rc == 0:
            print(f"✅ {name} 连接成功！")
        else:
            print(f"❌ {name} 连接失败，返回码: {rc}")

    def on_message(client, userdata, msg):
        try:
            payload = msg.payload.decode('utf-8')
            print(f"📨 {name} 收到消息: {payload}")
        except:
            print(f"📨 {name} 收到消息: {msg.payload}")

    client = mqtt.Client()
    client.on_connect = on_connect
    client.on_message = on_message

    try:
        client.connect(broker, port, 60)
        client.loop_start()
        time.sleep(2)

        if client.is_connected():
            # 发布测试消息
            test_msg = f"Hello from {name} at {time.time()}"
            client.publish("test/mapping", test_msg)
            print(f"📤 {name} 发送测试消息")

            # 等待接收
            time.sleep(3)
            client.disconnect()
            return True
        else:
            return False

    except Exception as e:
        print(f"❌ {name} 连接异常: {e}")
        return False
    finally:
        try:
            client.loop_stop()
        except:
            pass

if __name__ == "__main__":
    print("🚀 MQTT端口映射测试")
    print("=" * 40)

    # 测试本地连接
    local_ok = test_connection(LOCAL_BROKER, LOCAL_PORT, "本地MQTT")

    # 测试公网连接
    public_ok = test_connection(PUBLIC_BROKER, PUBLIC_PORT, "公网MQTT")

    print("\n" + "=" * 40)
    print("📊 测试结果:")
    print(f"本地MQTT (127.0.0.1:1883): {'✅ 正常' if local_ok else '❌ 失败'}")
    print(f"公网MQTT (22.tcp.cpolar.top:14871): {'✅ 正常' if public_ok else '❌ 失败'}")

    if public_ok:
        print("\n🎉 公网端口映射正常！ESP32可以使用公网地址")
    else:
        print("\n⚠️ 公网端口映射有问题，请检查cpolar配置")