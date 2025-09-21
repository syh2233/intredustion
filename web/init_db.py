#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
初始化数据库
"""

from app import app, db

def init_database():
    """初始化数据库表"""
    with app.app_context():
        # 删除所有表
        db.drop_all()
        # 创建所有表
        db.create_all()
        print("数据库表初始化完成")

        # 添加默认主机设备
        from app import DeviceInfo
        master_device = DeviceInfo(
            device_id='esp32_fire_alarm_01',
            name='ESP32火灾报警主机',
            location='宿舍A栋101',
            device_type='master',
            status='online'
        )
        db.session.add(master_device)

        # 添加默认从机设备
        slave_device = DeviceInfo(
            device_id='esp32_slave_01',
            name='ESP32从机-01',
            location='宿舍A栋102',
            device_type='slave',
            master_id='esp32_fire_alarm_01',
            status='online'
        )
        db.session.add(slave_device)

        db.session.commit()
        print("默认设备添加完成")

if __name__ == "__main__":
    init_database()