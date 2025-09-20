'''
DHT11温湿度传感器 - 精简版本
接线：DATA->GPIO4, VCC->5V, GND->GND
'''

from machine import Pin
import time

def read_dht11():
    """读取DHT11温湿度数据"""
    pin = Pin(4)

    # 发送启动信号
    pin.init(Pin.OUT)
    pin.value(0)
    time.sleep_ms(20)
    pin.value(1)

    # 切换到输入模式并记录信号
    pin.init(Pin.IN, Pin.PULL_UP)

    changes = []
    last_value = 1
    last_time = time.ticks_us()

    start_time = time.ticks_us()
    while time.ticks_diff(time.ticks_us(), start_time) < 50000:
        current_value = pin.value()
        if current_value != last_value:
            current_time = time.ticks_us()
            duration = time.ticks_diff(current_time, last_time)
            changes.append((last_value, duration))
            last_value = current_value
            last_time = current_time
        time.sleep_us(1)

    # 解析数据
    if len(changes) < 10:
        return None, None

    bits = []
    for i in range(2, len(changes), 2):
        if i + 1 < len(changes):
            high_duration = changes[i][1]
            bit = 1 if high_duration > 50 else 0
            bits.append(bit)
            if len(bits) >= 40:
                break

    if len(bits) < 40:
        return None, None

    # 转换为字节数据
    data = bytearray(5)
    for i in range(5):
        for j in range(8):
            data[i] = (data[i] << 1) | bits[i*8 + j]

    # 校验和检查
    checksum = (data[0] + data[1] + data[2] + data[3]) & 0xFF
    if checksum != data[4]:
        return None, None

    # 返回温度和湿度
    temperature = data[2]
    humidity = data[0]

    if 0 <= humidity <= 95 and 0 <= temperature <= 50:
        return temperature, humidity
    else:
        return None, None

# 主程序
if __name__ == "__main__":
    print("DHT11温湿度传感器")
    print("-" * 30)

    while True:
        temp, hum = read_dht11()

        if temp is not None and hum is not None:
            print(f"温度: {temp}°C, 湿度: {hum}%")
        else:
            print("读取失败")

        time.sleep(5)