'''
MQ2烟雾传感器 - 精简版本
接线：AO->GPIO34(模拟), DO->GPIO2(数字), VCC->5V, GND->GND
'''

from machine import Pin, ADC
import time

# 配置MQ2传感器
mq2_ao = ADC(Pin(34))  # 模拟输出
mq2_do = Pin(2, Pin.IN)  # 数字输出

# 设置ADC衰减（11dB范围，0-3.3V）
mq2_ao.atten(ADC.ATTN_11DB)

def read_mq2():
    """读取MQ2传感器数据"""
    try:
        # 读取模拟值和数字值
        analog_value = mq2_ao.read()
        digital_value = mq2_do.value()
        return analog_value, digital_value
    except:
        return None, None

def get_smoke_status(analog_value, digital_value):
    """获取烟雾状态"""
    if analog_value is None or digital_value is None:
        return "读取错误"

    # 计算烟雾浓度百分比 (0-100%)
    concentration = min(100, max(0, (analog_value / 4095) * 100))

    # 数字输出：0表示检测到烟雾，1表示正常
    if digital_value == 0:
        if analog_value < 1000:
            return f"检测到烟雾！浓度{concentration:.0f}% (高)"
        else:
            return f"检测到烟雾！浓度{concentration:.0f}% (中等)"
    else:
        if analog_value > 3000:
            return f"空气清新 浓度{concentration:.0f}%"
        elif analog_value > 2000:
            return f"空气质量良好 浓度{concentration:.0f}%"
        else:
            return f"可能有轻微污染 浓度{concentration:.0f}%"

# 主程序
if __name__ == "__main__":
    print("MQ2烟雾传感器监测")
    print("-" * 40)
    print("模拟值: 0-4095 (原始ADC读数)")
    print("浓度: 0-100% (烟雾浓度百分比)")
    print("数字值: 0=有烟雾, 1=无烟雾")
    print("-" * 40)

    while True:
        analog_value, digital_value = read_mq2()

        if analog_value is not None and digital_value is not None:
            status = get_smoke_status(analog_value, digital_value)
            print(f"模拟: {analog_value:4d} | 数字: {digital_value} | {status}")
        else:
            print("读取失败")

        time.sleep(2)