'''
OLED显示屏测试文件 - 显示Hello World
基于esp32_slave_simple.py中的OLED初始化和显示方法
'''

from machine import Pin, SoftI2C
import time
import ssd1306

# OLED引脚配置 (与从机相同)
OLED_SDA = 26  # OLED SDA引脚
OLED_SCL = 25  # OLED SCL引脚

def main():
    """主测试函数"""
    print("🔧 OLED Hello World测试开始")

    # 初始化OLED显示屏
    print(f"初始化OLED显示屏 - SDA:GPIO{OLED_SDA}, SCL:GPIO{OLED_SCL}")

    try:
        # 创建I2C总线
        i2c = SoftI2C(scl=Pin(OLED_SCL), sda=Pin(OLED_SDA))

        # OLED显示参数
        oled_width = 128
        oled_height = 64

        # 创建OLED对象
        oled = ssd1306.SSD1306_I2C(oled_width, oled_height, i2c)

        # 清空显示屏
        oled.fill(0)

        # 显示Hello World
        oled.text("Hello World!", 0, 0)
        oled.text("ESP32 OLED", 0, 16)
        oled.text("Test Running", 0, 32)

        # 更新显示
        oled.show()

        print("✅ OLED显示屏初始化成功")
        print("✅ Hello World显示成功")

        # 显示成功信息
        print("📱 显示内容:")
        print("   第一行: Hello World!")
        print("   第二行: ESP32 OLED")
        print("   第三行: Test Running")

        # 等待3秒让用户看到显示
        time.sleep(20)

        # 清空屏幕
        oled.fill(0)
        oled.text("Test Complete", 0, 24)
        oled.show()

        print("✅ 测试完成")

    except Exception as e:
        print(f"❌ OLED显示屏初始化失败: {e}")
        print("请检查:")
        print("   1. OLED接线是否正确")
        print("   2. I2C地址是否为0x3C")
        print("   3. 电源和地线连接")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n测试被中断")
    except Exception as e:
        print(f"❌ 测试过程中出现错误: {e}")