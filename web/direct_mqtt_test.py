#!/usr/bin/env python3
"""
直接MQTT舵机控制测试 - 绕过Flask服务器
直接发送MQTT消息测试ESP32舵机响应
"""

import paho.mqtt.client as mqtt
import json
import time

# MQTT配置
BROKER = "22.tcp.cpolar.top"
PORT = 11390
TOPIC = "esp32/esp32_fire_alarm_01/control"

def on_connect(client, userdata, flags, rc):
    """连接回调"""
    if rc == 0:
        print(f"✅ 连接到MQTT代理成功: {BROKER}:{PORT}")
        print(f"📋 将发送控制命令到主题: {TOPIC}")
    else:
        print(f"❌ 连接失败，返回码: {rc}")

def on_publish(client, userdata, mid):
    """发布回调"""
    print(f"📤 消息 {mid} 发布成功")

def test_servo_control():
    """测试舵机控制 - 只测试0-180和180-90"""
    client = mqtt.Client()
    client.on_connect = on_connect
    client.on_publish = on_publish

    print("🔧 ESP32舵机关键动作测试 - 0→180, 180→90")
    print("=" * 60)

    # 连接到MQTT代理
    print(f"🔗 正在连接MQTT代理...")
    try:
        client.connect(BROKER, PORT, 60)
        client.loop_start()

        # 等待连接建立
        time.sleep(3)

        # 测试命令序列 - 只测试两个关键动作
        test_commands = [
            {
                "name": "舵机从0度转到180度",
                "command": {"device": "servo", "action": "test", "angle": 180, "timestamp": int(time.time())}
            },
            {
                "name": "舵机从180度转到90度（关闭）",
                "command": {"device": "servo", "action": "off", "timestamp": int(time.time())}
            }
        ]

        for i, test in enumerate(test_commands, 1):
            print(f"\n🎯 测试 {i}/{len(test_commands)}: {test['name']}")
            print("📋 这个测试专门检查Brownout问题是否解决")

            # 准备命令
            command_json = json.dumps(test['command'])
            print(f"📤 发送命令: {command_json}")

            # 发布消息
            result = client.publish(TOPIC, command_json)

            # 等待ESP32响应 - 延长等待时间观察是否重启
            print("⏳ 等待8秒观察ESP32是否重启...")
            print("💡 请观察:")
            print("   1. ESP32是否显示'收到MQTT消息'")
            print("   2. 舵机是否渐进式转动")
            print("   3. 是否出现'Brownout detector'重启")
            print("   4. OLED显示是否正常更新")
            time.sleep(8)

        print(f"\n🎉 关键动作测试完成!")
        print("🔍 分析结果:")
        print("   ✅ 如果没有'brownout detector'重启 = 问题已解决")
        print("   ⚠️  如果仍然出现重启 = 需要更换电源适配器")
        print("💡 建议: 使用5V 2A或更高功率的电源适配器")

    except Exception as e:
        print(f"❌ 测试过程中发生错误: {e}")
    finally:
        try:
            client.loop_stop()
            client.disconnect()
            print("🔌 MQTT连接已断开")
        except:
            pass

if __name__ == "__main__":
    try:
        test_servo_control()
    except KeyboardInterrupt:
        print("\n⏹️ 测试被用户中断")
    except Exception as e:
        print(f"\n❌ 测试异常: {e}")