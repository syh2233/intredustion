#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简单的IP地址查找工具
"""

import subprocess
import re
import socket
import platform

def get_computer_ip():
    """获取电脑的IP地址"""
    system = platform.system()

    try:
        if system == "Windows":
            # Windows系统使用ipconfig
            result = subprocess.run(['ipconfig'], capture_output=True, text=True, encoding='gbk')
            output = result.stdout

            print("=== Network Interface Information ===")
            print(output)
            print("\n" + "="*50)

            # 提取IPv4地址
            ipv4_pattern = r'IPv4 Address[ .]*: (\d+\.\d+\.\d+\.\d+)'
            matches = re.findall(ipv4_pattern, output)

        elif system == "Linux" or system == "Darwin":
            # Linux/Mac系统使用ifconfig
            result = subprocess.run(['ifconfig'], capture_output=True, text=True)
            output = result.stdout

            print("=== Network Interface Information ===")
            print(output)
            print("\n" + "="*50)

            # 提取IPv4地址
            ipv4_pattern = r'inet (\d+\.\d+\.\d+\.\d+)'
            matches = re.findall(ipv4_pattern, output)

        else:
            print(f"Unsupported system: {system}")
            return None

        if matches:
            print("Found IP addresses:")
            for i, ip in enumerate(matches):
                print(f"{i+1}. {ip}")

            # 过滤掉回环地址和自动私有地址
            valid_ips = []
            for ip in matches:
                if not ip.startswith('127.') and not ip.startswith('169.254.'):
                    valid_ips.append(ip)

            if valid_ips:
                print(f"\nRecommended IP address: {valid_ips[0]}")
                return valid_ips[0]
            else:
                return matches[0]  # 如果都是特殊地址，返回第一个
        else:
            print("No IPv4 address found")
            return None

    except Exception as e:
        print(f"Failed to get IP address: {e}")
        return None

def test_port(ip, port):
    """测试指定端口是否开放"""
    try:
        print(f"Testing {ip}:{port}...")
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(3)
        result = sock.connect_ex((ip, port))
        sock.close()

        if result == 0:
            print(f"Port {port} is open")
            return True
        else:
            print(f"Port {port} is closed")
            return False

    except Exception as e:
        print(f"Test failed: {e}")
        return False

def main():
    """主函数"""
    print("IP Address Finder Tool")
    print("=" * 50)

    # 获取主机信息
    try:
        hostname = socket.gethostname()
        local_ip = socket.gethostbyname(hostname)
        print(f"Computer name: {hostname}")
        print(f"Local IP: {local_ip}")

        # 分析IP段
        ip_parts = local_ip.split('.')
        if len(ip_parts) == 4:
            base_ip = '.'.join(ip_parts[:3])
            print(f"\nESP32 might be in IP range: {base_ip}.1 to {base_ip}.254")

    except Exception as e:
        print(f"Failed to get host info: {e}")

    print("\n" + "=" * 50)

    # 获取IP地址
    computer_ip = get_computer_ip()

    if computer_ip:
        print(f"\nRecommended computer IP: {computer_ip}")
        print(f"\nPlease update in esp32_manual_ip_clean.py:")
        print(f'COMPUTER_IP = "{computer_ip}"  # <-- Update this!')

        # 测试常用端口
        print(f"\n=== Port Testing ===")
        test_port(computer_ip, 1883)  # MQTT
        test_port(computer_ip, 5000)  # Flask

        print(f"\n=== Quick Test Commands ===")
        print(f"1. First update the IP address in esp32_manual_ip_clean.py")
        print(f"2. Run the program on ESP32")
        print(f"3. Monitor on computer: mosquitto_sub -h {computer_ip} -t \"esp32/fire_alarm/data\" -v")

    print(f"\n=== Alternative Solutions ===")
    print("If local connection fails, use public MQTT servers:")
    print("1. test.mosquitto.org:1883")
    print("2. broker.hivemq.com:1883")
    print("3. Try esp32_simple.py (uses public servers)")

if __name__ == "__main__":
    main()