#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试从机数据显示功能
"""

import requests
import json

def test_slaves_api():
    """测试从机API接口"""
    base_url = "http://localhost:5000"

    print("=" * 50)
    print("测试从机数据显示功能")
    print("=" * 50)

    # 测试从机列表API
    print("\n1. 测试从机列表API...")
    try:
        response = requests.get(f"{base_url}/api/slaves", timeout=5)
        if response.status_code == 200:
            slaves = response.json()
            print(f"   [OK] 成功获取 {len(slaves)} 个从机")
            for slave in slaves:
                print(f"     - {slave['device_id']}: {slave['name']} ({slave['location']})")
                if slave.get('latest_data'):
                    print(f"       最新数据: 火焰={slave['latest_data'].get('flame', 0)}, 烟雾={slave['latest_data'].get('smoke', 0)}")
                else:
                    print(f"       暂无数据")
        else:
            print(f"   [ERROR] 从机列表API错误: {response.status_code}")
            print(f"     响应内容: {response.text}")
    except Exception as e:
        print(f"   [ERROR] 无法连接到从机API: {e}")

    # 测试设备列表API（确认从机没有被错误地放在设备监控中）
    print("\n2. 测试设备列表API...")
    try:
        response = requests.get(f"{base_url}/api/devices", timeout=5)
        if response.status_code == 200:
            devices = response.json()
            print(f"   [OK] 成功获取 {len(devices)} 个设备")
            master_devices = [d for d in devices if d.get('device_type') != 'slave']
            slave_devices = [d for d in devices if d.get('device_type') == 'slave']
            print(f"     - 主机设备: {len(master_devices)} 个")
            print(f"     - 从机设备: {len(slave_devices)} 个 (应该为0，因为从机有独立的API)")

            if slave_devices:
                print("   ⚠ 警告: 发现从机设备在主设备列表中，这可能是前端显示混乱的原因")
        else:
            print(f"   [ERROR] 设备列表API错误: {response.status_code}")
    except Exception as e:
        print(f"   [ERROR] 无法连接到设备API: {e}")

    # 测试从机详情API
    print("\n3. 测试从机详情API...")
    try:
        response = requests.get(f"{base_url}/api/slaves", timeout=5)
        if response.status_code == 200:
            slaves = response.json()
            for slave in slaves:
                slave_id = slave['device_id']
                detail_response = requests.get(f"{base_url}/api/slaves/{slave_id}/data", timeout=5)
                if detail_response.status_code == 200:
                    detail_data = detail_response.json()
                    print(f"   ✓ {slave_id} 详情API正常")
                    print(f"     数据点数: {len(detail_data)}")
                    if detail_data:
                        latest = detail_data[-1]
                        print(f"     最新: 火焰={latest.get('flame', 0)}, 烟雾={latest.get('smoke', 0)}, 状态={latest.get('overall_status', 'normal')}")
                else:
                    print(f"   [ERROR] {slave_id} 详情API错误: {detail_response.status_code}")
        else:
            print(f"   [ERROR] 无法获取从机列表: {response.status_code}")
    except Exception as e:
        print(f"   [ERROR] 测试从机详情API失败: {e}")

    print("\n" + "=" * 50)
    print("测试完成")
    print("请检查:")
    print("1. 从机列表API是否返回了正确的从机数据")
    print("2. 设备列表API中的从机设备数量是否为0")
    print("3. 从机详情API是否返回了正确的历史数据")
    print("4. Web界面的'从机监控'区域是否显示了从机设备")
    print("=" * 50)

if __name__ == "__main__":
    test_slaves_api()