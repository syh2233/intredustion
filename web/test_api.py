#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试API端点
"""

import requests
import json

def test_api():
    base_url = "http://localhost:5000"

    print("测试API端点...")

    # 测试test_data端点
    try:
        response = requests.get(f"{base_url}/test_data", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print(f"[OK] test_data API成功: {data}")
        else:
            print(f"[ERROR] test_data API失败: {response.status_code}")
            print(f"响应内容: {response.text}")
    except Exception as e:
        print(f"[ERROR] 无法连接到test_data API: {e}")

    # 测试slaves端点
    try:
        response = requests.get(f"{base_url}/api/slaves", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print(f"[OK] slaves API成功: 获取到 {len(data)} 个从机")
        else:
            print(f"[ERROR] slaves API失败: {response.status_code}")
    except Exception as e:
        print(f"[ERROR] 无法连接到slaves API: {e}")

    # 测试devices端点
    try:
        response = requests.get(f"{base_url}/api/devices", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print(f"[OK] devices API成功: 获取到 {len(data)} 个设备")
        else:
            print(f"[ERROR] devices API失败: {response.status_code}")
    except Exception as e:
        print(f"[ERROR] 无法连接到devices API: {e}")

if __name__ == "__main__":
    test_api()