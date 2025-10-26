'''
舵机控制 - 精简版本
接线：信号线->GPIO15, VCC->5V, GND->GND
'''

from machine import Pin, PWM
import time

class ServoController:
    """舵机控制器类"""

    def __init__(self, pin_number=SERVO_PIN):
        """初始化舵机控制器"""
        try:
            print(f"🔧 初始化舵机控制器，引脚: {pin_number}")
            self.servo_pin = PWM(Pin(pin_number), freq=50)
            self.servo_pin.duty(0)  # 初始位置为0
            self.current_angle = 0
            self.is_active = False
            self.auto_off_timer = 0
            print("✅ 舵机控制器初始化成功")
        except Exception as e:
            print(f"❌ 舵机控制器初始化失败: {e}")
            self.pin = None
            self.current_angle = 0
            self.is_active = False

    def set_angle(self, angle):
        """设置舵机角度（0-180度）"""
        if self.pin is None:
            print("❌ 舵机未初始化")
            return False

        try:
            # 限制角度范围
            angle = max(0, min(180, angle))

            # 将角度转换为PWM占空比
            # 0度 = 0.5ms (占空比约25), 180度 = 2.5ms (占空比约128)
            duty_cycle = int(25 + (angle / 180) * 103)  # 25-128范围
            self.servo_pin.duty(duty_cycle)
            self.current_angle = angle
            print(f"🎯 舵机设置角度: {angle}° (占空比: {duty_cycle})")

            # 给舵机时间移动
            time.sleep(0.1)  # 100ms延迟
            return True
        except Exception as e:
            print(f"❌ 设置舵机角度失败: {e}")
            return False

    def on(self):
        """打开舵机（转到180度）"""
        print("🔛 舵机开启")
        result = self.set_angle(180)
        if result:
            self.is_active = True
        return result

    def off(self):
        """关闭舵机（转到0度）"""
        print("🔴 舵机关闭")
        result = self.set_angle(0)
        if result:
            self.is_active = False
        return result

    def process_control_command(self, command_data):
        """处理控制命令"""
        try:
            device = command_data.get('device', '')
            action = command_data.get('action', '')
            timestamp = command_data.get('timestamp', 0)

            print(f"📡 处理舵机控制命令: {device} - {action}")

            if device == 'servo':
                if action == 'on':
                    result = self.on()
                elif action == 'off':
                    result = self.off()
                elif action == 'test' and 'angle' in command_data:
                    angle = command_data.get('angle', 0)
                    result = self.set_angle(angle)
                else:
                    print(f"⚠️ 未知的舵机动作: {action}")
                    result = False

                return {
                    'success': result,
                    'action': action,
                    'angle': self.current_angle,
                    'is_active': self.is_active
                }
            else:
                print(f"⚠️ 非舵机控制命令: {device}")
                return {'success': False, 'error': 'Not a servo command'}

        except Exception as e:
            print(f"❌ 处理控制命令失败: {e}")
            return {'success': False, 'error': str(e)}

    def check_auto_off(self):
        """检查自动关闭"""
        # 这里可以实现自动关闭逻辑
        return False

    def get_status(self):
        """获取舵机状态"""
        return {
            'current_angle': self.current_angle,
            'is_active': self.is_active,
            'is_initialized': self.pin is not None
        }

# 保持向后兼容的简单函数

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

