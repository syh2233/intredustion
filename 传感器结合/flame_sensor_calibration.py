#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
火焰传感器校准和诊断程序
用于校准火焰传感器的灵敏度并诊断问题
"""

from machine import Pin
import time

# 配置
FLAME_DO_PIN = 14  # 火焰传感器数字输入

def calibrate_flame_sensor():
    """校准火焰传感器"""
    print("🔥 火焰传感器校准程序")
    print("=" * 60)
    print("这个程序将帮助您校准火焰传感器的灵敏度")
    print("=" * 60)

    try:
        flame_do = Pin(FLAME_DO_PIN, Pin.IN)
        print("✅ 火焰传感器初始化成功")

        # 步骤1：检查当前状态
        print("\n📊 步骤1：检查当前传感器状态")
        print("-" * 40)

        current_value = flame_do.value()
        if current_value == 0:
            print(f"当前读数: {current_value} (检测到火焰)")
            print("⚠️ 传感器可能过于敏感或环境有干扰")
        else:
            print(f"当前读数: {current_value} (正常状态)")
            print("✅ 传感器当前状态正常")

        # 步骤2：连续监测
        print("\n📈 步骤2：连续监测10秒")
        print("-" * 40)
        print("请观察传感器读数是否稳定...")

        readings = []
        for i in range(20):
            value = flame_do.value()
            readings.append(value)
            status = "火焰" if value == 0 else "正常"
            print(f"[{i+1:2d}] 读数: {value} ({status})")
            time.sleep(0.5)

        # 分析读数
        zero_count = readings.count(0)
        one_count = readings.count(1)

        print(f"\n📊 读数统计:")
        print(f"   检测到火焰: {zero_count}次")
        print(f"   正常状态: {one_count}次")

        if zero_count == len(readings):
            print("🚨 问题：传感器一直检测到火焰！")
            print("建议：")
            print("1. 检查传感器上的电位器，顺时针旋转降低灵敏度")
            print("2. 确保没有强光源直射传感器")
            print("3. 检查接线是否正确")
        elif zero_count > len(readings) * 0.3:
            print("⚠️ 警告：传感器过于敏感")
            print("建议：微调电位器降低灵敏度")
        else:
            print("✅ 传感器灵敏度正常")

        # 步骤3：电位器调整指导
        print("\n🔧 步骤3：电位器调整指导")
        print("-" * 40)
        print("火焰传感器模块上有一个蓝色的电位器")
        print("顺时针旋转：降低灵敏度（需要更强的火焰才能触发）")
        print("逆时针旋转：提高灵敏度（微弱的火焰也能触发）")
        print("\n建议调整方法：")
        print("1. 如果一直检测到火焰：顺时针旋转电位器")
        print("2. 如果检测不到火焰：逆时针旋转电位器")
        print("3. 调整时观察DO指示灯的变化")

        # 步骤4：实时测试
        print("\n🧪 步骤4：实时测试模式")
        print("-" * 40)
        print("现在进入实时测试模式，您可以：")
        print("1. 用打火机测试传感器（保持安全距离）")
        print("2. 调整电位器观察读数变化")
        print("3. 按Ctrl+C退出测试")
        print("-" * 40)

        try:
            while True:
                value = flame_do.value()
                status = "🔥 火焰" if value == 0 else "✅ 正常"
                print(f"读数: {value} | {status}", end='\r')
                time.sleep(0.1)

        except KeyboardInterrupt:
            print("\n\n⏹️ 测试完成")

    except Exception as e:
        print(f"❌ 错误: {e}")

def check_wiring():
    """检查接线"""
    print("\n🔌 火焰传感器接线检查")
    print("=" * 60)
    print("标准接线方式：")
    print(f"  - DO (数字输出) -> GPIO{FLAME_DO_PIN}")
    print("  - VCC -> 5V")
    print("  - GND -> GND")
    print("\n常见问题：")
    print("1. 接线松动或接触不良")
    print("2. VCC和GND接反")
    print("3. 使用了3.3V而不是5V")
    print("4. DO引脚连接错误")
    print("\n传感器模块指示灯：")
    print("  - 电源指示灯(PWR)：常亮表示供电正常")
    print("  - 数字指示灯(DO)：灭表示检测到火焰，亮表示正常")

def test_different_pins():
    """测试不同引脚"""
    print("\n🔍 测试其他GPIO引脚")
    print("=" * 60)
    print("如果GPIO27有问题，可以尝试其他引脚")

    test_pins = [12, 13, 14, 15, 16, 17, 18, 19, 21, 22, 23, 25, 26, 32, 33]

    for pin in test_pins:
        try:
            test_pin = Pin(pin, Pin.IN)
            value = test_pin.value()
            print(f"GPIO{pin:2d}: 读数={value} {'✅' if value == 1 else '⚠️'}")
        except:
            print(f"GPIO{pin:2d}: 不可用 ❌")

if __name__ == "__main__":
    print("🔧 火焰传感器诊断和校准工具")
    print("=" * 60)

    # 检查接线
    check_wiring()

    # 询问是否继续校准
    try:
        response = input("\n是否开始校准？(y/n): ")
        if response.lower() == 'y':
            calibrate_flame_sensor()

        # 询问是否测试其他引脚
        response = input("\n是否测试其他GPIO引脚？(y/n): ")
        if response.lower() == 'y':
            test_different_pins()

        print("\n✅ 诊断完成！")

    except KeyboardInterrupt:
        print("\n⏹️ 程序被用户中断")
    except Exception as e:
        print(f"\n❌ 错误: {e}")