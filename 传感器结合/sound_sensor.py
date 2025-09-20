'''
声音传感器 - 精简版本
接线：DO->GPIO35(数字), AO->GPIO13(模拟), VCC->5V, GND->GND
'''

from machine import Pin, ADC
import time

# 配置声音传感器
sound_do = Pin(35, Pin.IN)   # 数字输出
sound_ao = ADC(Pin(13))      # 模拟输出

# 设置ADC衰减（11dB范围，0-3.3V）
sound_ao.atten(ADC.ATTN_11DB)

def read_sound_sensor():
    """读取声音传感器数据"""
    try:
        # 读取模拟值和数字值
        analog_value = sound_ao.read()
        digital_value = sound_do.value()
        return analog_value, digital_value
    except:
        return None, None

def get_sound_status(analog_value, digital_value):
    """获取声音状态"""
    if analog_value is None or digital_value is None:
        return "读取错误"

    # 数字输出：0表示检测到声音，1表示安静
    sound_level = min(100, (analog_value / 4095) * 100)  # 转换为百分比

    if digital_value == 0:
        if sound_level > 30:
            return f"检测到声音！强度{sound_level:.0f}% (大声)"
        elif sound_level > 15:
            return f"检测到声音！强度{sound_level:.0f}% (中等)"
        else:
            return f"检测到声音！强度{sound_level:.0f}% (小声)"
    else:
        if sound_level > 50:
            return f"环境安静但有背景音 {sound_level:.0f}%"
        elif sound_level > 20:
            return f"环境安静 {sound_level:.0f}%"
        else:
            return f"非常安静 {sound_level:.0f}%"

def detect_sound_pattern():
    """检测声音模式"""
    """连续检测声音模式"""
    readings = []
    for i in range(10):
        analog_value, digital_value = read_sound_sensor()
        if analog_value is not None:
            readings.append(analog_value)
        time.sleep(0.1)  # 快速采样

    if len(readings) >= 5:
        avg_sound = sum(readings) / len(readings)
        max_sound = max(readings)
        min_sound = min(readings)
        variation = max_sound - min_sound

        if variation > 1000:
            return "声音波动大 (可能有人在说话)"
        elif variation > 500:
            return "声音有变化"
        elif avg_sound > 2000:
            return "环境噪音较大"
        else:
            return "环境声音稳定"

# 主程序
if __name__ == "__main__":
    print("声音传感器监测")
    print("-" * 40)
    print("模拟值: 0-4095 (数值越高声音越大)")
    print("数字值: 0=有声音, 1=安静")
    print("-" * 40)

    # 快速测试
    print("快速声音检测测试...")
    for i in range(5):
        analog_value, digital_value = read_sound_sensor()

        if analog_value is not None and digital_value is not None:
            status = get_sound_status(analog_value, digital_value)
            print(f"模拟: {analog_value:4d} | 数字: {digital_value} | {status}")
        else:
            print("读取失败")

        time.sleep(1)

    print("\n" + "=" * 40)
    print("开始连续监测...")
    print("请制造一些声音进行测试！")
    print("=" * 40)

    while True:
        analog_value, digital_value = read_sound_sensor()

        if analog_value is not None and digital_value is not None:
            status = get_sound_status(analog_value, digital_value)
            print(f"模拟: {analog_value:4d} | 数字: {digital_value} | {status}")

            # 每10秒分析一次声音模式
            if 'pattern_counter' not in globals():
                global pattern_counter
                pattern_counter = 0
            pattern_counter += 1

            if pattern_counter % 50 == 0:  # 每50次循环（约10秒）
                pattern = detect_sound_pattern()
                print(f"声音模式分析: {pattern}")
        else:
            print("读取失败")

        time.sleep(0.2)  # 快速响应