'''
舵机控制 - 精简版本
接线：信号线->GPIO15, VCC->5V, GND->GND
'''

from machine import Pin, PWM
import time

# 配置舵机（GPIO15，PWM频率50Hz）
servo_pin = PWM(Pin(15), freq=50)

def set_servo_angle(angle):
    """设置舵机角度（0-180度）"""
    # 将角度转换为PWM占空比（0-1023）
    # 0度 = 0.5ms (占空比约25), 180度 = 2.5ms (占空比约128)
    duty_cycle = int(25 + (angle / 180) * 103)  # 25-128范围
    servo_pin.duty(duty_cycle)

def test_servo():
    """舵机测试功能"""
    print("舵机控制测试")
    print("-" * 30)

    # 测试不同角度
    angles = [0, 45, 90, 135, 180, 90, 0]

    for angle in angles:
        print(f"舵机转到 {angle}°")
        set_servo_angle(angle)
        time.sleep(1)

    print("测试完成")

def manual_control():
    """手动控制模式"""
    print("舵机手动控制")
    print("-" * 30)
    print("输入角度 (0-180)，输入 'q' 退出")
    print("-" * 30)

    while True:
        try:
            user_input = input("请输入角度 (0-180): ")

            if user_input.lower() == 'q':
                print("退出控制")
                break

            angle = float(user_input)

            if 0 <= angle <= 180:
                set_servo_angle(angle)
                print(f"舵机已转到 {angle}°")
            else:
                print("角度超出范围，请输入0-180之间的数值")

        except ValueError:
            print("输入无效，请输入数字")
        except KeyboardInterrupt:
            print("\n退出控制")
            break

# 主程序
if __name__ == "__main__":
    print("舵机控制程序")
    print("=" * 40)

    # 初始化舵机到0度位置
    set_servo_angle(0)
    print("舵机已初始化到0度位置")

    choice = input("选择模式:\n1. 自动测试\n2. 手动控制\n请选择 (1/2): ")

    if choice == '1':
        test_servo()
    elif choice == '2':
        manual_control()
    else:
        print("无效选择，运行自动测试")
        test_servo()

    # 最后回到0度位置
    set_servo_angle(0)
    print("舵机已回到0度位置")