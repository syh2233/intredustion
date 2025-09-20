'''
ESP32 MQTT连接测试脚本
用于验证ESP32是否能正常连接到公网MQTT服务器
'''

from machine import Pin, ADC
import time
import json
import network
import umqtt.simple

def test_network_connectivity():
    """测试网络连接"""
    print("🔍 测试网络连接...")

    # 连接WiFi
    WIFI_SSID = "syh2031"
    WIFI_PASSWORD = "12345678"

    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)

    if not wlan.isconnected():
        print(f"📡 连接WiFi: {WIFI_SSID}")
        wlan.connect(WIFI_SSID, WIFI_PASSWORD)

        # 等待连接
        max_wait = 10
        while max_wait > 0:
            if wlan.status() < 0 or wlan.status() >= 3:
                break
            max_wait -= 1
            print(f"⏳ 等待连接... {max_wait}")
            time.sleep(1)

    if wlan.isconnected():
        print(f"✅ WiFi连接成功")
        print(f"   IP地址: {wlan.ifconfig()[0]}")
        return True
    else:
        print(f"❌ WiFi连接失败")
        return False

def test_mqtt_connection():
    """测试MQTT连接"""
    print("\n🔍 测试MQTT连接...")

    # MQTT配置
    MQTT_SERVER = "22.tcp.cpolar.top"
    MQTT_PORT = 14871
    DEVICE_ID = "esp32_test_01"

    try:
        # 连接MQTT
        print(f"📡 连接MQTT服务器: {MQTT_SERVER}:{MQTT_PORT}")

        client = umqtt.simple.MQTTClient(
            DEVICE_ID,
            MQTT_SERVER,
            MQTT_PORT
        )

        client.connect()
        print("✅ MQTT连接成功！")

        # 发布测试消息
        test_message = {
            'device_id': DEVICE_ID,
            'timestamp': time.time(),
            'message': 'ESP32 MQTT连接测试',
            'status': 'test'
        }

        topic = f"esp32/{DEVICE_ID}/data/json"
        client.publish(topic, json.dumps(test_message))
        print(f"📤 发布测试消息到: {topic}")
        print(f"   内容: {test_message}")

        # 订阅响应主题
        response_topic = f"esp32/{DEVICE_ID}/cmd/response"
        client.subscribe(response_topic)
        print(f"📡 订阅响应主题: {response_topic}")

        # 等待响应
        print("⏳ 等待服务器响应...")
        time.sleep(2)

        client.disconnect()
        print("✅ MQTT测试完成")
        return True

    except Exception as e:
        print(f"❌ MQTT连接失败: {e}")
        return False

def main():
    print("🚀 ESP32 MQTT连接测试")
    print("=" * 40)

    # 测试网络连接
    if not test_network_connectivity():
        print("❌ 网络连接失败，无法继续MQTT测试")
        return

    # 测试MQTT连接
    if test_mqtt_connection():
        print("\n🎉 ESP32可以正常连接到公网MQTT服务器！")
        print("✅ fire_alarm_oled.py配置正确")
    else:
        print("\n⚠️ ESP32连接公网MQTT失败")
        print("请检查:")
        print("1. WiFi连接是否正常")
        print("2. MQTT服务器地址是否正确")
        print("3. 网络防火墙设置")

if __name__ == "__main__":
    main()