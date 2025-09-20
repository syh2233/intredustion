#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
通用MQTT数据监控脚本
监控所有ESP32火灾报警系统设备的MQTT数据
"""

import paho.mqtt.client as mqtt
import json
import time
import re
from datetime import datetime

# MQTT配置
MQTT_SERVER = "192.168.24.32"
MQTT_PORT = 1883

# 通配符主题 - 监控所有ESP32设备
DATA_TOPIC = "esp32/+/data/json"
ALERT_TOPIC = "esp32/+/alert/#"
STATUS_TOPIC = "esp32/+/status/online"

# 数据统计
message_count = 0
start_time = None
device_stats = {}

def on_connect(client, userdata, flags, rc, properties=None):
    """连接回调"""
    global start_time
    if rc == 0:
        start_time = datetime.now()
        print(f"✅ 连接到MQTT服务器: {MQTT_SERVER}")
        print(f"📡 订阅数据主题: {DATA_TOPIC}")
        print(f"🚨 订阅警报主题: {ALERT_TOPIC}")
        print(f"📡 订阅状态主题: {STATUS_TOPIC}")

        # 订阅所有相关主题
        client.subscribe(DATA_TOPIC)
        client.subscribe(ALERT_TOPIC)
        client.subscribe(STATUS_TOPIC)

        print("=" * 100)
        print("🚀 开始接收所有ESP32火灾报警系统数据...")
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

        # 从主题中提取设备ID
        device_id = extract_device_id(topic)
        if device_id:
            update_device_stats(device_id, topic)

        # 根据主题类型处理不同的数据
        if "data/json" in topic:
            # 传感器数据
            process_sensor_data(data, device_id)
        elif "alert" in topic:
            # 警报数据
            process_alert_data(data, topic, device_id)
        elif "status" in topic:
            # 状态数据
            process_status_data(data, device_id)
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

def extract_device_id(topic):
    """从主题中提取设备ID"""
    # 主题格式: esp32/{device_id}/data/json
    match = re.match(r'esp32/([^/]+)/', topic)
    if match:
        return match.group(1)
    return None

def update_device_stats(device_id, topic):
    """更新设备统计信息"""
    if device_id not in device_stats:
        device_stats[device_id] = {
            'data_count': 0,
            'alert_count': 0,
            'status_count': 0,
            'last_seen': None
        }

    device_stats[device_id]['last_seen'] = datetime.now()

    if "data/json" in topic:
        device_stats[device_id]['data_count'] += 1
    elif "alert" in topic:
        device_stats[device_id]['alert_count'] += 1
    elif "status" in topic:
        device_stats[device_id]['status_count'] += 1

def process_sensor_data(data, device_id):
    """处理传感器数据"""
    # 获取基础信息
    timestamp = data.get('timestamp', 0)
    status = data.get('status', 'unknown')
    simulation_mode = data.get('simulation_mode', 'unknown')
    time_str = datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')

    print(f"📡 传感器数据 - {time_str}")
    print(f"📍 设备ID: {device_id}")
    if simulation_mode != 'unknown':
        print(f"🎮 模拟模式: {simulation_mode}")
    print()

    # 传感器数据详情
    print("🔍 传感器读数:")
    print("-" * 40)

    # 火焰传感器
    flame = data.get('flame')
    if flame is not None:
        print(f"🔥 火焰传感器: {flame}")
    else:
        print("🔥 火焰传感器: 无数据")

    # 烟雾传感器
    smoke = data.get('smoke')
    if smoke is not None:
        print(f"💨 烟雾传感器: {smoke}")
    else:
        print("💨 烟雾传感器: 无数据")

    # 温度
    temperature = data.get('temperature')
    if temperature is not None:
        print(f"🌡️ 温度: {temperature}°C")
    else:
        print("🌡️ 温度: 无数据")

    # 湿度
    humidity = data.get('humidity')
    if humidity is not None:
        print(f"💧 湿度: {humidity}%")
    else:
        print("💧 湿度: 无数据")

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

def process_alert_data(data, topic, device_id):
    """处理警报数据"""
    alert_type = data.get('type', 'unknown')
    level = data.get('level', 'unknown')
    message = data.get('message', '未知警报')
    alert_data = data.get('data', {})

    print(f"🚨 {alert_type.upper()} 警报 - 设备: {device_id}")
    print("-" * 40)
    print(f"⚠️ 警报级别: {level}")
    print(f"📝 警报信息: {message}")

    if alert_data:
        print(f"🔥 火焰值: {alert_data.get('flame', 'N/A')}")
        print(f"💨 烟雾值: {alert_data.get('smoke', 'N/A')}")
        print(f"🌡️ 温度: {alert_data.get('temperature', 'N/A')}°C")
        print(f"💧 湿度: {alert_data.get('humidity', 'N/A')}%")

def process_status_data(data, device_id):
    """处理设备状态数据"""
    print(f"📡 设备状态更新 - 设备: {device_id}")
    print("-" * 40)

    if isinstance(data, str):
        if data == "1":
            print("✅ 设备在线")
        else:
            print("❌ 设备离线")
    else:
        print(f"📊 状态数据: {data}")

def print_device_stats():
    """打印设备统计信息"""
    if not device_stats:
        return

    print(f"\n📊 设备统计:")
    print("-" * 60)
    for device_id, stats in device_stats.items():
        last_seen = stats['last_seen'].strftime('%H:%M:%S') if stats['last_seen'] else 'N/A'
        print(f"📍 {device_id}: 数据{stats['data_count']} | 警报{stats['alert_count']} | 状态{stats['status_count']} | 最后:{last_seen}")

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
    print("🚀 通用ESP32火灾报警系统 MQTT数据监控器")
    print("=" * 60)
    print(f"📡 服务器: {MQTT_SERVER}:{MQTT_PORT}")
    print(f"📰 数据主题: {DATA_TOPIC}")
    print(f"🚨 警报主题: {ALERT_TOPIC}")
    print(f"📡 状态主题: {STATUS_TOPIC}")
    print("🎯 监控所有ESP32设备的传感器数据、警报和状态")
    print("=" * 60)

    # 创建MQTT客户端
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
        print_final_stats()
        client.disconnect()
        print("✅ 已断开连接")
        print("👋 感谢使用!")

    except Exception as e:
        print(f"❌ 连接异常: {e}")
        print("请检查MQTT服务器是否运行")

def print_final_stats():
    """打印最终统计信息"""
    if message_count > 0 and start_time:
        run_time = (datetime.now() - start_time).total_seconds()
        print(f"📊 监控统计:")
        print(f"   总消息数: {message_count}")
        print(f"   运行时间: {run_time:.1f} 秒")
        print(f"   平均频率: {message_count/run_time:.2f} 消息/秒")

        if device_stats:
            print(f"   发现设备数: {len(device_stats)}")
            print_device_stats()

if __name__ == "__main__":
    main()