#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MQTT数据监控脚本 - 完整版本
用于监控ESP32火灾报警系统上传的所有MQTT数据
"""

import paho.mqtt.client as mqtt
import json
import time
from datetime import datetime

# MQTT配置
MQTT_SERVER = "192.168.24.32"
MQTT_PORT = 1883

# 订阅正式设备的主题
TOPIC = "esp32/esp32_fire_alarm_01/data/json"
ALERT_TOPIC = "esp32/esp32_fire_alarm_01/alert/#"
STATUS_TOPIC = "esp32/esp32_fire_alarm_01/status/online"

# 也订阅模拟设备的主题（用于测试）
SIM_TOPIC = "esp32/esp32_fire_alarm_sim_01/data/json"
SIM_ALERT_TOPIC = "esp32/esp32_fire_alarm_sim_01/alert/#"
SIM_STATUS_TOPIC = "esp32/esp32_fire_alarm_sim_01/status/online"

# 数据统计
message_count = 0
start_time = None

def on_connect(client, userdata, flags, rc, properties=None):
    """连接回调"""
    global start_time
    if rc == 0:
        start_time = datetime.now()
        print(f"✅ 连接到MQTT服务器: {MQTT_SERVER}")
        print(f"📡 订阅主题: {TOPIC}")
        print(f"🚨 订阅警报主题: {ALERT_TOPIC}")
        print(f"📡 订阅状态主题: {STATUS_TOPIC}")
        print(f"📡 也订阅模拟主题: {SIM_TOPIC}")

        # 订阅所有相关主题
        client.subscribe(TOPIC)
        client.subscribe(ALERT_TOPIC)
        client.subscribe(STATUS_TOPIC)
        client.subscribe(SIM_TOPIC)
        client.subscribe(SIM_ALERT_TOPIC)
        client.subscribe(SIM_STATUS_TOPIC)

        print("=" * 100)
        print("🚀 开始接收ESP32火灾报警系统数据...")
        print("=" * 100)
    else:
        print(f"❌ 连接失败，返回码: {rc}")

def on_message(client, userdata, msg):
    """消息接收回调"""
    global message_count
    message_count += 1

    try:
        # 解析JSON数据
        data = json.loads(msg.payload.decode())
        topic = msg.topic

        print(f"\n📊 数据包 #{message_count} - 主题: {topic}")
        print("=" * 80)

        # 根据主题类型处理不同的数据
        if topic == TOPIC:
            # 传感器数据
            process_sensor_data(data)
        elif "alert" in topic:
            # 警报数据
            process_alert_data(data, topic)
        elif "status" in topic:
            # 状态数据
            process_status_data(data)
        else:
            # 未知主题
            print(f"❓ 未知主题数据: {data}")

        print("=" * 80)

        # 数据统计
        if start_time:
            run_time = (datetime.now() - start_time).total_seconds()
            if run_time > 0:
                frequency = message_count / run_time
                print(f"📊 统计: 已接收 {message_count} 条消息, 平均 {frequency:.2f} 消息/秒")

    except json.JSONDecodeError as e:
        print(f"❌ JSON解析错误: {e}")
        print(f"原始数据: {msg.payload}")
    except Exception as e:
        print(f"❌ 数据处理错误: {e}")
        print(f"原始数据: {msg.payload}")

def process_sensor_data(data):
    """处理传感器数据"""
    # 获取基础信息
    timestamp = data.get('timestamp', 0)
    device_id = data.get('device_id', '未知设备')
    status = data.get('status', 'unknown')
    time_str = datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')

    print(f"📡 传感器数据 - {time_str}")
    print(f"📍 设备ID: {device_id}")
    print()

    # 传感器数据详情
    print("🔍 传感器读数:")
    print("-" * 40)

    # 火焰传感器 (模拟值: <500=火焰, <1000=警告, >=1000=正常)
    flame = data.get('flame')
    if flame is not None:
        if flame < 500:
            flame_status = "🚨 检测到火焰"
        elif flame < 1000:
            flame_status = "⚠️ 火焰警告"
        else:
            flame_status = "✅ 正常"
        print(f"🔥 火焰传感器: {flame} ({flame_status})")
    else:
        print("🔥 火焰传感器: 无数据")

    # 烟雾传感器 (MQ2模拟值: <1000=警报, <1500=警告, >=1500=正常)
    smoke = data.get('smoke')
    if smoke is not None:
        if smoke < 1000:
            smoke_status = "🚨 烟雾警报"
        elif smoke < 1500:
            smoke_status = "⚠️ 烟雾警告"
        else:
            smoke_status = "✅ 空气清新"
        print(f"💨 烟雾传感器: {smoke} ({smoke_status})")
    else:
        print("💨 烟雾传感器: 无数据")

    # 温度
    temperature = data.get('temperature')
    if temperature is not None:
        if temperature > 40:
            temp_status = "🚨 温度过高"
        elif temperature > 35:
            temp_status = "⚠️ 温度偏高"
        else:
            temp_status = "✅ 正常"
        print(f"🌡️ 温度: {temperature}°C ({temp_status})")
    else:
        print("🌡️ 温度: 无数据")

    # 湿度
    humidity = data.get('humidity')
    if humidity is not None:
        if humidity > 70:
            humidity_status = "💧 湿度较高"
        elif humidity < 30:
            humidity_status = "🏜️ 湿度偏低"
        else:
            humidity_status = "✅ 舒适"
        print(f"💧 湿度: {humidity}% ({humidity_status})")
    else:
        print("💧 湿度: 无数据")

    # 光照传感器 (BH1750: >30=警报, >20=警告, <=20=正常)
    light = data.get('light')
    if light is not None:
        if light > 30:
            light_status = "🚨 光照警报"
        elif light > 20:
            light_status = "⚠️ 光照警告"
        else:
            light_status = "✅ 正常"
        print(f"💡 光照: {light}lux ({light_status})")
    else:
        print("💡 光照: 无数据")

    print()

    # 系统状态
    print("📈 系统状态:")
    print("-" * 40)
    print(f"🎯 总体状态: {status}")

    # 状态图标
    if status == "alarm":
        print("🚨 火灾警报！")
    elif status == "warning":
        print("⚠️ 环境警告！")
    else:
        print("✅ 系统正常")

def process_alert_data(data, topic):
    """处理警报数据"""
    alert_type = data.get('type', 'unknown')
    level = data.get('level', 'unknown')
    message = data.get('message', '未知警报')
    alert_data = data.get('data', {})

    print(f"🚨 {alert_type.upper()} 警报")
    print("-" * 40)
    print(f"⚠️ 警报级别: {level}")
    print(f"📝 警报信息: {message}")

    if alert_data:
        # 火焰传感器状态
        flame = alert_data.get('flame', 'N/A')
        if flame != 'N/A':
            if flame < 500:
                flame_status = "🚨 检测到火焰"
            elif flame < 1000:
                flame_status = "⚠️ 火焰警告"
            else:
                flame_status = "✅ 正常"
            print(f"🔥 火焰传感器: {flame} ({flame_status})")
        else:
            print(f"🔥 火焰传感器: {flame}")

        # 烟雾传感器状态
        smoke = alert_data.get('smoke', 'N/A')
        if smoke != 'N/A':
            if smoke < 1000:
                smoke_status = "🚨 烟雾警报"
            elif smoke < 1500:
                smoke_status = "⚠️ 烟雾警告"
            else:
                smoke_status = "✅ 空气清新"
            print(f"💨 烟雾传感器: {smoke} ({smoke_status})")
        else:
            print(f"💨 烟雾传感器: {smoke}")

        # 温度状态
        temp = alert_data.get('temperature', 'N/A')
        if temp != 'N/A':
            if temp > 40:
                temp_status = "🚨 温度过高"
            elif temp > 35:
                temp_status = "⚠️ 温度偏高"
            else:
                temp_status = "✅ 正常"
            print(f"🌡️ 温度: {temp}°C ({temp_status})")
        else:
            print(f"🌡️ 温度: {temp}°C")

        # 湿度状态
        humidity = alert_data.get('humidity', 'N/A')
        if humidity != 'N/A':
            if humidity > 70:
                humidity_status = "💧 湿度较高"
            elif humidity < 30:
                humidity_status = "🏜️ 湿度偏低"
            else:
                humidity_status = "✅ 舒适"
            print(f"💧 湿度: {humidity}% ({humidity_status})")
        else:
            print(f"💧 湿度: {humidity}%")

        # 光照状态
        light = alert_data.get('light', 'N/A')
        if light != 'N/A':
            if light > 30:
                light_status = "🚨 光照警报"
            elif light > 20:
                light_status = "⚠️ 光照警告"
            else:
                light_status = "✅ 正常"
            print(f"💡 光照: {light}lux ({light_status})")
        else:
            print(f"💡 光照: {light}lux")

def process_status_data(data):
    """处理设备状态数据"""
    print("📡 设备状态更新:")
    print("-" * 40)

    if isinstance(data, str):
        if data == "1":
            print("✅ 设备在线")
        else:
            print("❌ 设备离线")
    else:
        print(f"📊 状态数据: {data}")

def on_disconnect(client, userdata, rc, properties=None):
    """断开连接回调"""
    if rc != 0:
        print(f"❌ 意外断开连接，返回码: {rc}")
        print("🔄 尝试重新连接...")
        # 等待2秒后重连
        time.sleep(2)
        try:
            client.reconnect()
        except:
            pass

def main():
    """主函数"""
    print("🚀 ESP32火灾报警系统 MQTT数据监控器")
    print("=" * 60)
    print(f"📡 服务器: {MQTT_SERVER}:{MQTT_PORT}")
    print(f"📰 传感器数据主题: {TOPIC}")
    print(f"🚨 警报主题: {ALERT_TOPIC}")
    print(f"📡 状态主题: {STATUS_TOPIC}")
    print("🎯 监控所有传感器数据、警报和设备状态")
    print()
    print("📊 数据格式说明:")
    print("🔥 火焰传感器: <500=警报, <1000=警告, >=1000=正常")
    print("💨 烟雾传感器: <1000=警报, <1500=警告, >=1500=正常")
    print("🌡️ 温度: >40=警报, >35=警告, <=35=正常 (°C)")
    print("💧 湿度: >70=较高, <30=偏低, 30-70=舒适 (%)")
    print("💡 光照: >30=警报, >20=警告, <=20=正常 (lux)")
    print()
    print("🚨 警报级别: normal(正常) / warning(警告) / alarm(警报)")
    print("=" * 60)

    # 创建MQTT客户端（使用兼容的API版本）
    try:
        client = mqtt.Client(callback_api_version=mqtt.CallbackAPIVersion.VERSION2)
    except:
        # 如果新版本不可用，使用默认版本
        client = mqtt.Client()
        print("使用默认MQTT API版本")

    # 设置回调函数
    client.on_connect = on_connect
    client.on_message = on_message
    client.on_disconnect = on_disconnect

    try:
        # 连接到MQTT服务器
        print("📡 正在连接MQTT服务器...")
        client.connect(MQTT_SERVER, MQTT_PORT, 60)

        print("✅ 连接成功，等待数据...")
        print("💡 提示: 按 Ctrl+C 停止监控")
        print("-" * 60)

        # 启动网络循环
        client.loop_forever()

    except KeyboardInterrupt:
        print("\n\n🛑 用户停止监控")
        if message_count > 0 and start_time:
            run_time = (datetime.now() - start_time).total_seconds()
            print(f"📊 监控统计:")
            print(f"   总消息数: {message_count}")
            print(f"   运行时间: {run_time:.1f} 秒")
            print(f"   平均频率: {message_count/run_time:.2f} 消息/秒")
        client.disconnect()
        print("✅ 已断开连接")
        print("👋 感谢使用!")

    except Exception as e:
        print(f"❌ 连接异常: {e}")
        print("请检查MQTT服务器是否运行")

if __name__ == "__main__":
    main()