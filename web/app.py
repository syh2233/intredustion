#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ESP32 Dormitory Fire Alarm System - Flask Web Server
===================================================

Main Functions:
- MQTT message receiving and processing
- Sensor data storage
- Web interface providing
- Real-time data pushing
- Alarm management
"""

from flask import Flask, render_template, request, jsonify, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from flask_socketio import SocketIO
import paho.mqtt.client as mqtt
import sqlite3
import json
import time
import os
import sys
from datetime import datetime, timedelta, timezone
import threading
import logging
from threading import Lock
from intelligent_analysis import intelligent_analyzer
from ai_alarm_decision import ai_assisted_alarm_decision, ai_decision_engine

# 时区转换函数
def to_local_timestamp(utc_dt):
    """将UTC datetime转换为本地时间戳（北京时间 UTC+8）"""
    if utc_dt is None:
        return time.time()
    
    # 如果是字符串，先解析为datetime
    if isinstance(utc_dt, str):
        try:
            # 假设是UTC时间的ISO格式字符串
            utc_dt = datetime.fromisoformat(utc_dt)
        except:
            return time.time()
    
    # 确保datetime是timezone-aware的UTC时间
    if utc_dt.tzinfo is None:
        utc_dt = utc_dt.replace(tzinfo=timezone.utc)
    
    # 转换为北京时间 (UTC+8)
    beijing_tz = timezone(timedelta(hours=8))
    local_dt = utc_dt.astimezone(beijing_tz)
    
    # 返回时间戳
    return local_dt.timestamp()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Flask application initialization - handle PyInstaller bundled paths
def get_base_dir():
    """Get base directory for resources, works for both dev and PyInstaller"""
    if getattr(sys, 'frozen', False):
        # Running in a PyInstaller bundle - data files are in sys._MEIPASS
        return sys._MEIPASS
    else:
        # Running in normal Python environment
        return os.path.dirname(os.path.abspath(__file__))

BASE_DIR = get_base_dir()
TEMPLATES_DIR = os.path.join(BASE_DIR, 'templates')
STATIC_DIR = os.path.join(BASE_DIR, 'static')

logger.info(f"BASE_DIR: {BASE_DIR}")
logger.info(f"TEMPLATES_DIR: {TEMPLATES_DIR}")
logger.info(f"STATIC_DIR: {STATIC_DIR}")
logger.info(f"Templates exist: {os.path.exists(TEMPLATES_DIR)}")
if os.path.exists(TEMPLATES_DIR):
    logger.info(f"Templates list: {os.listdir(TEMPLATES_DIR)[:5]}")

# Change working directory to BASE_DIR and keep it there for Flask
# This allows Flask to find templates/static with relative paths
original_cwd = os.getcwd()
try:
    os.chdir(BASE_DIR)
    logger.info(f"Changed working directory to: {os.getcwd()}")
except Exception as e:
    logger.warning(f"Failed to change working directory: {e}")
    # If chdir fails, use absolute paths for Flask
    BASE_DIR = original_cwd
    TEMPLATES_DIR = os.path.join(BASE_DIR, 'templates')
    STATIC_DIR = os.path.join(BASE_DIR, 'static')

app = Flask(
    __name__,
    template_folder='templates',
    static_folder='static',
    static_url_path='/static',
    instance_relative_config=True,
)


app.config['SECRET_KEY'] = 'esp32_fire_alarm_system_2024'

# 数据库存放位置：
# - 默认使用 Flask instance 目录（web/instance/fire_alarm.db）
# - 桌面端可通过环境变量 FIRE_ALARM_DATA_DIR 指定可写目录（例如 AppData）
data_dir = os.environ.get('FIRE_ALARM_DATA_DIR')
if data_dir:
    os.makedirs(data_dir, exist_ok=True)
    db_file = os.path.join(data_dir, 'fire_alarm.db')
else:
    os.makedirs(app.instance_path, exist_ok=True)
    db_file = os.path.join(app.instance_path, 'fire_alarm.db')

# Windows 路径需要转成 URI 形式
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + db_file.replace('\\', '/')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# MQTT configuration - 使用公网端口映射
app.config['MQTT_BROKER_URL'] = '2.tcp.vip.cpolar.cn'
app.config['MQTT_BROKER_PORT'] = 14357
app.config['MQTT_USERNAME'] = ''
app.config['MQTT_PASSWORD'] = ''
app.config['MQTT_KEEPALIVE'] = 60
app.config['MQTT_TLS_ENABLED'] = False

# Initialize extensions with simple configuration
db = SQLAlchemy(app)
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# MQTT client setup
mqtt_client = mqtt.Client()

# Eventlet handles concurrency automatically

def on_connect(client, userdata, flags, rc):
    """MQTT连接回调"""
    logger.info(f"MQTT连接成功，返回码: {rc}")
    logger.info(f"Connected to broker: {app.config['MQTT_BROKER_URL']}:{app.config['MQTT_BROKER_PORT']}")
    # 订阅主题
    client.subscribe('esp32/+/data/json')
    client.subscribe('esp32/+/alert/#')
    client.subscribe('esp32/+/status/#')
    client.subscribe('esp32/+/control')  # 添加控制主题订阅
    logger.info("MQTT主题订阅: esp32/+/data/json, esp32/+/alert/#, esp32/+/status/#, esp32/+/control")

def on_disconnect(client, userdata, rc):
    """MQTT断开连接回调"""
    if rc != 0:
        logger.warning(f"MQTT意外断开连接，返回码: {rc}")
    else:
        logger.info("MQTT正常断开连接")

def on_message(client, userdata, msg):
    """MQTT消息接收回调"""
    try:
        # paho-mqtt新版本中topic和payload已经是字符串
        topic = msg.topic
        payload = msg.payload.decode('utf-8') if isinstance(msg.payload, bytes) else msg.payload

        logger.info(f"收到MQTT消息 - 主题: {topic}, 内容: {payload}")
        logger.info(f"消息详情 - 主题长度: {len(topic)}, 内容长度: {len(payload)}")

        # 在Flask应用上下文中处理数据
        with app.app_context():
            if '/data/json' in topic:
                logger.info("处理传感器数据消息...")
                # 处理传感器数据
                data = json.loads(payload)
                logger.info(f"解析的传感器数据: {data}")
                process_sensor_data(data)

            elif '/alert/' in topic:
                logger.info("处理警报数据消息...")
                # 处理警报信息
                alert_data = json.loads(payload)
                logger.info(f"解析的警报数据: {alert_data}")
                process_alert_data(alert_data)
            elif '/control' in topic:
                logger.info("处理控制命令消息...")
                # 处理控制命令
                control_data = json.loads(payload)
                logger.info(f"解析的控制命令: {control_data}")
                process_control_data(control_data, topic)
            else:
                logger.info(f"收到未处理主题的消息: {topic}")

    except json.JSONDecodeError as e:
        logger.error(f"JSON解析错误: {e}, 内容: {payload}")
    except Exception as e:
        logger.error(f"处理MQTT消息错误: {e}")
        logger.error(f"错误详情: {str(e)}")
        # 不再访问可能未定义的topic变量

# 设置MQTT回调
mqtt_client.on_connect = on_connect
mqtt_client.on_disconnect = on_disconnect
mqtt_client.on_message = on_message

# 连接MQTT broker
try:
    logger.info("正在连接MQTT broker...")
    mqtt_client.connect(app.config['MQTT_BROKER_URL'], app.config['MQTT_BROKER_PORT'], 60)
    mqtt_client.loop_start()
    logger.info("MQTT客户端启动")
except Exception as e:
    logger.error(f"MQTT连接失败: {e}")

# Database models
class SensorData(db.Model):
    """Sensor data model"""
    id = db.Column(db.Integer, primary_key=True)
    device_id = db.Column(db.String(50), nullable=False)
    device_type = db.Column(db.String(20), default='master')  # 'master' or 'slave'
    flame_value = db.Column(db.Integer, nullable=False)
    smoke_value = db.Column(db.Integer, nullable=False)
    temperature = db.Column(db.Float)
    humidity = db.Column(db.Float)
    light_level = db.Column(db.Float)  # 光照传感器
    alert_status = db.Column(db.Boolean, default=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

class AlertHistory(db.Model):
    """Alert history model"""
    id = db.Column(db.Integer, primary_key=True)
    device_id = db.Column(db.String(50), nullable=False)
    alert_type = db.Column(db.String(20), nullable=False)
    severity = db.Column(db.String(10), nullable=False)
    flame_value = db.Column(db.Integer)
    smoke_value = db.Column(db.Integer)
    temperature = db.Column(db.Float)
    humidity = db.Column(db.Float)
    light_level = db.Column(db.Float)  # 光照传感器
    location = db.Column(db.String(100))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    resolved = db.Column(db.Boolean, default=False)
    resolved_time = db.Column(db.DateTime)

class DeviceInfo(db.Model):
    """Device information model"""
    id = db.Column(db.Integer, primary_key=True)
    device_id = db.Column(db.String(50), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    location = db.Column(db.String(200))
    ip_address = db.Column(db.String(15))
    device_type = db.Column(db.String(20), default='master')  # 'master' or 'slave'
    master_id = db.Column(db.String(50))  # 对于从机，记录其所属的主机ID
    last_seen = db.Column(db.DateTime)
    status = db.Column(db.String(20), default='online')
    config = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# Create database tables
with app.app_context():
    db.create_all()

# MQTT连接已通过paho-mqtt直接处理

def process_sensor_data(data):
    """Process sensor data with thread safety"""
    try:
        # Debug logging to see available keys
        logger.info(f"Processing sensor data. Keys: {list(data.keys())}")
        if 'data' in data and isinstance(data['data'], dict):
             logger.info(f"Nested data keys: {list(data['data'].keys())}")

        device_id = data.get('device_id', 'unknown')

        # Check if this is slave data (contains slave_id or sensors with slave structure)
        is_slave_data = False
        slave_id = None

        # Initialize sensor values
        flame_value = 0
        smoke_value = 0
        alert_status = False

        if 'slave_id' in data:
            # This is slave data sent directly from slave
            is_slave_data = True
            slave_id = data['slave_id']
            device_id = slave_id  # Use slave_id as device_id
            logger.info(f"Processing slave data from {slave_id}")

            # Extract sensor values from slave structure
            if 'sensors' in data and 'flame' in data['sensors']:
                flame_sensor = data['sensors']['flame']
                flame_value = flame_sensor.get('analog', 1200)

            if 'sensors' in data and 'mq2_smoke' in data['sensors']:
                mq2_sensor = data['sensors']['mq2_smoke']
                smoke_value = mq2_sensor.get('analog', 1800)

            alert_status = data.get('overall_status') in ['alarm', 'warning']

        elif 'sensors' in data and 'flame' in data['sensors'] and 'mq2_smoke' in data['sensors']:
            # This is slave data forwarded by master
            is_slave_data = True
            slave_id = data.get('slave_id', device_id)
            device_id = slave_id

            # Extract sensor values from slave structure
            flame_sensor = data['sensors']['flame']
            mq2_sensor = data['sensors']['mq2_smoke']

            flame_value = flame_sensor.get('analog', 1200)
            smoke_value = mq2_sensor.get('analog', 1800)
            alert_status = data.get('overall_status') in ['alarm', 'warning']

        else:
            # This is master data
            # Check for nested 'data' field which is common in some JSON formats
            source_data = data
            if 'data' in data and isinstance(data['data'], dict):
                logger.info("Detected nested 'data' field, checking for values there as well")
                source_data = data['data']
            
            flame_value = data.get('flame', source_data.get('flame', 0))
            smoke_value = data.get('smoke', source_data.get('smoke', 0))
            alert_status = data.get('alert', source_data.get('alert', False))

        # 获取光照传感器数值 (兼容多种键名)
        light_value = data.get('light')
        if light_value is None:
            light_value = data.get('light_level')
        if light_value is None:
            light_value = data.get('lux')
        if light_value is None:
            light_value = data.get('illuminance')
            
        # Also check nested data if available
        if light_value is None and 'data' in data and isinstance(data['data'], dict):
            nested_data = data['data']
            light_value = nested_data.get('light')
            if light_value is None:
                light_value = nested_data.get('light_level')
            if light_value is None:
                light_value = nested_data.get('lux')

        logger.info(f"DEBUG: Extracted light_value: {light_value} (Type: {type(light_value)})")
        if light_value is None:
             logger.warning(f"DEBUG: Failed to extract light value from data: {data}")

        # 准备传感器数据用于AI分析
        sensor_data_for_ai = {
            'flame_value': flame_value,
            'smoke_value': smoke_value,
            'temperature': data.get('temperature'),
            'humidity': data.get('humidity'),
            'light_level': light_value
        }

        # 获取硬件阈值判断结果（从数据中推断）
        hardware_result = 'alarm' if alert_status else 'normal'
        if data.get('overall_status') == 'warning':
            hardware_result = 'warning'

        # AI辅助决策分析
        try:
            ai_decision = ai_assisted_alarm_decision(device_id, sensor_data_for_ai, hardware_result)

            # 使用AI决策结果更新alert_status
            final_alert_status = ai_decision['final_result'] in ['warning', 'alarm']

            logger.info(f"AI决策 - 设备:{device_id}, 硬件:{hardware_result} -> AI:{ai_decision['final_result']}, 置信度:{ai_decision['confidence']:.2f}, 干预:{ai_decision['intervention']}")

            # 如果AI干预了硬件判断，记录特殊日志
            if ai_decision['intervention']:
                logger.warning(f"AI干预报警决策 - 设备:{device_id}, 原因:{ai_decision['reasoning']}")

        except Exception as e:
            logger.error(f"AI决策分析失败: {e}")
            # AI失败时使用原始硬件判断
            final_alert_status = alert_status
            ai_decision = None

        # Save to database
        sensor_data = SensorData(
            device_id=device_id,
            device_type='slave' if is_slave_data else 'master',
            flame_value=flame_value,
            smoke_value=smoke_value,
            temperature=data.get('temperature'),
            humidity=data.get('humidity'),
            light_level=light_value,  # 光照传感器数据
            alert_status=final_alert_status  # 使用AI决策后的结果
        )
        db.session.add(sensor_data)

        # Update device status
        device = DeviceInfo.query.filter_by(device_id=device_id).first()
        if device:
            device.last_seen = datetime.utcnow()
            device.status = 'online'
            device.device_type = 'slave' if is_slave_data else 'master'
        else:
            # Create new device record
            device_name = data.get('name', f"ESP32-{device_id}")
            device_location = data.get('location', 'Dormitory')
            device_type = 'slave' if is_slave_data else 'master'

            device = DeviceInfo(
                device_id=device_id,
                name=device_name,
                location=device_location,
                device_type=device_type,
                master_id=data.get('master_id') if is_slave_data else None,
                last_seen=datetime.utcnow(),
                status='online'
            )
            db.session.add(device)

        db.session.commit()

        # Prepare data for frontend
        frontend_data = {
            'device_id': device_id,
            'device_type': 'slave' if is_slave_data else 'master',
            'flame': flame_value,
            'smoke': smoke_value,
            'temperature': data.get('temperature'),
            'humidity': data.get('humidity'),
            'light': light_value,
            'light_level': light_value,  # Ensure frontend receives 'light_level'
            'alert': final_alert_status,  # 使用AI决策后的结果
            'hardware_alert': alert_status,  # 保留原始硬件判断
            'timestamp': datetime.utcnow().isoformat(),
            'slave_name': data.get('slave_name') if is_slave_data else None,
            'slave_location': data.get('slave_location') if is_slave_data else None,
            'overall_status': ai_decision['final_result'] if ai_decision else (data.get('overall_status', 'normal' if not final_alert_status else 'alarm')),
            'ai_decision': {
                'intervention': ai_decision['intervention'] if ai_decision else False,
                'confidence': ai_decision['confidence'] if ai_decision else 0.5,
                'reasoning': ai_decision['reasoning'] if ai_decision else 'No AI analysis'
            }
        }

        # Real-time push to frontend via WebSocket (for old UI)
        socketio.emit('sensor_data', frontend_data)

        # Send device update to 5-layer architecture UI
        send_device_update_to_ui(device_id)

        # Special handling for slave data
        if is_slave_data:
            socketio.emit('slave_data_update', frontend_data)
            logger.info(f"Slave data saved and pushed: {device_id}")
        else:
            logger.info(f"Master data saved and pushed: {device_id}")

    except Exception as e:
        logger.error(f"Error processing sensor data: {e}")
        logger.error(f"Data content: {data}")
        db.session.rollback()

def send_device_update_to_ui(device_id):
    """Send device status update to 5-layer architecture UI"""
    try:
        with app.app_context():
            devices_data = get_devices().get_json()
            socketio.emit('devices_update', devices_data)

            # Check if this device has alarm condition
            for device_data in devices_data:
                if device_data['device_id'] == device_id and device_data['status'] == '警报':
                    # Send alarm notification
                    alarm_data = {
                        'timestamp': time.time(),
                        'device_id': device_data['device_id'],
                        'location': device_data['location'],
                        'temperature': device_data['temperature'],
                        'smoke_level': device_data['smoke_level'],
                        'status': '警报',
                        'message': f"{device_data['location']} 检测到火灾风险！"
                    }
                    socketio.emit('alarm', alarm_data)
                    break

    except Exception as e:
        logger.error(f"Error sending device update to UI: {e}")

def process_alert_data(alert_data):
    """Process alert data"""
    try:
        # Extract data from the alert structure
        data = alert_data.get('data', {})
        device_id = data.get('device_id') or alert_data.get('device_id')

        # Save alert record
        alert = AlertHistory(
            device_id=device_id,
            alert_type=alert_data.get('type', 'unknown'),
            severity=alert_data.get('level', 'medium'),
            flame_value=data.get('flame'),
            smoke_value=data.get('smoke'),
            temperature=data.get('temperature'),
            humidity=data.get('humidity'),
            light_level=data.get('light'),
            location=data.get('location', alert_data.get('location', 'Unknown location'))
        )
        db.session.add(alert)
        db.session.commit()

        # Push alert information to frontend
        alarm_data = {
            'timestamp': data.get('timestamp', time.time()),
            'device_id': device_id,
            'location': data.get('location', alert_data.get('location', 'Unknown location')),
            'temperature': data.get('temperature'),
            'smoke_level': data.get('smoke'),
            'status': 'alarm' if data.get('status') == 'alarm' else 'warning',
            'message': alert_data.get('message', f"设备 {device_id} 检测到异常！")
        }

        # Send alarm notification to frontend
        socketio.emit('alarm', alarm_data)
        logger.warning(f"Alert record created and notification sent: {device_id} - {alert_data.get('type')}")

    except Exception as e:
        logger.error(f"Error processing alert data: {e}")
        logger.error(f"Alert data content: {alert_data}")
        db.session.rollback()

def process_control_data(control_data, topic):
    """Process control command data"""
    try:
        device = control_data.get('device', '')
        action = control_data.get('action', '')
        timestamp = control_data.get('timestamp', 0)

        logger.info(f"收到控制命令 - 设备: {device}, 动作: {action}, 时间戳: {timestamp}")

        # 处理舵机控制命令
        if device == 'servo':
            if action == 'on':
                logger.info("舵机开启命令 - 转到180度")
                # 这里可以选择记录日志或发送到前端
                socketio.emit('servo_status', {'status': 'on', 'angle': 180})

            elif action == 'off':
                logger.info("舵机关闭命令 - 转到0度")
                socketio.emit('servo_status', {'status': 'off', 'angle': 0})

            elif action == 'test' and 'angle' in control_data:
                angle = control_data.get('angle', 0)
                logger.info(f"舵机测试命令 - 转到{angle}度")
                socketio.emit('servo_status', {'status': 'test', 'angle': angle})

            else:
                logger.warning(f"未知的舵机控制动作: {action}")

        else:
            logger.info(f"收到其他设备控制命令: {device} - {action}")

        # 可以在这里添加控制历史记录
        logger.info(f"控制命令处理完成: {control_data}")

    except Exception as e:
        logger.error(f"处理控制命令时发生错误: {e}")
        logger.error(f"控制命令内容: {control_data}")

# Flask routes
@app.route('/test_slaves')
def test_slaves():
    """Test page for slave display functionality"""
    return render_template('test_slaves.html')

@app.route('/')
def index():
    """Homepage - ESP32 fire alarm system with 5-layer architecture"""
    try:
        result = render_template('index.html')
        logger.info(f"index.html rendered, length: {len(result) if result else 0}")
        return result
    except Exception as e:
        logger.error(f"Error rendering index.html: {e}")
        logger.error(f"Template folder: {app.template_folder}")
        logger.error(f"Jinja2 loader: {app.jinja_loader.list_templates()}")
        return f"Error: {e}", 500

@app.route('/dashboard')
def dashboard():
    """Dashboard page - detailed data visualization"""
    return render_template('dashboard.html')

@app.route('/monitor')
def monitor():
    """MQTT real-time monitoring page"""
    return render_template('monitor.html')

@app.route('/intelligence')
def intelligence():
    """智能分析页面"""
    return render_template('intelligence.html')

@app.route('/api/data/recent')
def get_recent_data():
    """Get recent sensor data"""
    try:
        limit = int(request.args.get('limit', 20))
        device_id = request.args.get('device_id')
        
        query = SensorData.query.order_by(SensorData.timestamp.desc())
        if device_id:
            query = query.filter_by(device_id=device_id)
            
        data = query.limit(limit).all()
        
        result = []
        for item in data:
            result.append({
                'id': item.id,
                'device_id': item.device_id,
                'flame': item.flame_value,
                'smoke': item.smoke_value,
                'temperature': item.temperature,
                'humidity': item.humidity,
                'light': item.light_level,
                'alert': item.alert_status,
                'timestamp': item.timestamp.isoformat()
            })
        
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error getting recent data: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/data/range')
def get_data_range():
    """Get data within time range"""
    try:
        start_time = request.args.get('start')
        end_time = request.args.get('end')
        device_id = request.args.get('device_id')
        
        query = SensorData.query
        if start_time:
            start = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
            query = query.filter(SensorData.timestamp >= start)
        if end_time:
            end = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
            query = query.filter(SensorData.timestamp <= end)
        if device_id:
            query = query.filter_by(device_id=device_id)
            
        data = query.order_by(SensorData.timestamp.desc()).all()
        
        result = []
        for item in data:
            result.append({
                'id': item.id,
                'device_id': item.device_id,
                'flame': item.flame_value,
                'smoke': item.smoke_value,
                'temperature': item.temperature,
                'humidity': item.humidity,
                'light': item.light_level,
                'alert': item.alert_status,
                'timestamp': item.timestamp.isoformat()
            })
        
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error getting range data: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/alerts')
def get_alerts():
    """Get alert history"""
    try:
        alerts = AlertHistory.query.order_by(AlertHistory.timestamp.desc()).limit(50).all()
        
        result = []
        for alert in alerts:
            result.append({
                'id': alert.id,
                'device_id': alert.device_id,
                'alert_type': alert.alert_type,
                'severity': alert.severity,
                'flame_value': alert.flame_value,
                'smoke_value': alert.smoke_value,
                'temperature': alert.temperature,
                'humidity': alert.humidity,
                'location': alert.location,
                'timestamp': alert.timestamp.isoformat(),
                'resolved': alert.resolved,
                'resolved_time': alert.resolved_time.isoformat() if alert.resolved_time else None
            })
        
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error getting alert history: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/alerts/<int:alert_id>/resolve', methods=['PUT'])
def resolve_alert(alert_id):
    """Mark an alert as resolved"""
    try:
        alert = AlertHistory.query.get(alert_id)
        if not alert:
            return jsonify({'error': 'Alert not found'}), 404

        alert.resolved = True
        alert.resolved_time = datetime.utcnow()
        db.session.commit()

        logger.info(f"Alert {alert_id} marked as resolved")
        return jsonify({'status': 'success', 'message': 'Alert resolved'})

    except Exception as e:
        logger.error(f"Error resolving alert {alert_id}: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/data', methods=['POST'])
def receive_data():
    """Receive sensor data via HTTP POST (backup method)"""
    try:
        data = request.get_json()
        process_sensor_data(data)
        return jsonify({'status': 'success', 'message': 'Data received'})
    except Exception as e:
        logger.error(f"Error receiving HTTP data: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/mqtt/status')
def mqtt_status():
    """Check MQTT connection status"""
    try:
        # 检查MQTT客户端连接状态
        if mqtt_client.is_connected():
            logger.info("MQTT client is connected")
            return jsonify({
                'status': 'connected',
                'broker': app.config['MQTT_BROKER_URL'],
                'port': app.config['MQTT_BROKER_PORT'],
                'connected': True
            })
        else:
            logger.warning("MQTT client is not connected")
            # 尝试重新连接
            try:
                logger.info("Attempting to reconnect to MQTT broker...")
                mqtt_client.reconnect()
                logger.info("MQTT reconnection attempted")
            except Exception as reconnect_error:
                logger.error(f"MQTT reconnection failed: {reconnect_error}")

            return jsonify({
                'status': 'disconnected',
                'broker': app.config['MQTT_BROKER_URL'],
                'port': app.config['MQTT_BROKER_PORT'],
                'connected': False
            })
    except Exception as e:
        logger.error(f"Error checking MQTT status: {e}")
        return jsonify({
            'status': 'error',
            'error': str(e),
            'broker': app.config['MQTT_BROKER_URL'],
            'port': app.config['MQTT_BROKER_PORT']
        }), 500

@app.route('/api/mqtt/test', methods=['POST'])
def mqtt_publish_test():
    """Test MQTT message publishing"""
    try:
        data = request.get_json()
        topic = data.get('topic', 'test/topic')
        message = data.get('message', 'Test message')

        mqtt_client.publish(topic, message)
        logger.info(f"Published test message to {topic}: {message}")

        return jsonify({
            'status': 'success',
            'topic': topic,
            'message': message,
            'timestamp': datetime.utcnow().isoformat()
        })
    except Exception as e:
        logger.error(f"Error publishing test message: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/servo/control', methods=['POST'])
def servo_control():
    """舵机控制API接口"""
    try:
        data = request.get_json()
        action = data.get('action', '')

        logger.info(f"收到舵机控制请求 - 动作: {action}")

        # MQTT主题和命令配置（与direct_mqtt_test.py保持一致）
        topic = "esp32/esp32_fire_alarm_01/control"

        if action == 'on':
            # 开启舵机：从0度转到180度
            command = {
                "device": "servo",
                "action": "test",
                "angle": 180,
                "timestamp": int(time.time())
            }
            message = json.dumps(command)

            # 发布MQTT消息
            result = mqtt_client.publish(topic, message)

            if result == 0:  # paho-mqtt publish返回0表示成功
                logger.info(f"舵机开启命令已发送: {message}")
                return jsonify({
                    'status': 'success',
                    'action': 'on',
                    'message': '舵机开启命令已发送（0→180度）',
                    'timestamp': datetime.utcnow().isoformat()
                })
            else:
                logger.error(f"舵机开启命令发送失败: {result}")
                return jsonify({'error': f'MQTT发送失败: {result}'}), 500

        elif action == 'off':
            # 关闭舵机：从180度转到90度
            command = {
                "device": "servo",
                "action": "off",
                "timestamp": int(time.time())
            }
            message = json.dumps(command)

            # 发布MQTT消息
            result = mqtt_client.publish(topic, message)

            if result == 0:  # paho-mqtt publish返回0表示成功
                logger.info(f"舵机关闭命令已发送: {message}")
                return jsonify({
                    'status': 'success',
                    'action': 'off',
                    'message': '舵机关闭命令已发送（180→90度）',
                    'timestamp': datetime.utcnow().isoformat()
                })
            else:
                logger.error(f"舵机关闭命令发送失败: {result}")
                return jsonify({'error': f'MQTT发送失败: {result}'}), 500

        else:
            logger.warning(f"未知的舵机控制动作: {action}")
            return jsonify({'error': f'未知的控制动作: {action}'}), 400

    except Exception as e:
        logger.error(f"舵机控制API错误: {e}")
        return jsonify({'error': str(e)}), 500

# ESP32 Fire Alarm System API Routes
@app.route('/api/devices')
def get_devices():
    """Get all device status for fire alarm system"""
    try:
        # 数据超时时间（秒）- 超过这个时间没有新数据认为设备离线
        DATA_TIMEOUT = 300  # 5分钟

        # Only return devices that have actual sensor data
        sensor_devices = db.session.query(SensorData.device_id.distinct()).all()
        device_ids = [device[0] for device in sensor_devices]

        result = []
        # 使用 UTC 时间进行比较（与数据库存储的时间一致）
        current_time = datetime.utcnow()

        logger.info(f"查询设备数据: 找到 {len(device_ids)} 个设备ID")

        for device_id in device_ids:
            # Get device info
            device = DeviceInfo.query.filter_by(device_id=device_id).first()

            # Skip slave devices - they should only appear in /api/slaves
            if device and device.device_type == 'slave':
                continue

            # Get latest sensor data for this device
            latest_data = SensorData.query.filter_by(device_id=device_id)\
                                    .order_by(SensorData.timestamp.desc()).first()

            if latest_data:
                # 检查数据是否超时
                data_age = (current_time - latest_data.timestamp).total_seconds()
                is_online = data_age < DATA_TIMEOUT

                logger.info(f"设备 {device_id}: 数据年龄 {data_age:.0f} 秒, 在线={is_online}")

                # 只有设备在线时才返回数据
                if not is_online:
                    continue

                temperature = latest_data.temperature or 0
                smoke_level = latest_data.smoke_value or 0
                light_level = latest_data.light_level or 0  # 添加光照传感器值

                # Determine status based on sensor values (fire alarm logic)
                flame_value = latest_data.flame_value or 1200  # Default normal flame value
                humidity = latest_data.humidity or 60  # Default normal humidity value

                # Fire alarm logic - 与fire_alarm_oled.py保持一致
                if (flame_value < 500 or       # 火焰传感器值低表示检测到火焰
                    smoke_level < 1000 or      # MQ2烟雾传感器值低表示烟雾浓度高
                    temperature > 40 or        # 温度过高
                    light_level > 130):         # 光照过强
                    status = "警报"
                elif (flame_value < 1000 or     # 火焰传感器值偏低
                      smoke_level < 1300 or    # 烟雾浓度中等
                      temperature > 35 or      # 温度偏高
                      light_level > 120):       # 光照偏强
                    status = "警告"
                else:
                    status = "正常"

                result.append({
                    'device_id': device_id,
                    'location': device.location if device else device_id,
                    'temperature': round(temperature, 1),
                    'humidity': round(latest_data.humidity, 1) if latest_data.humidity else 0,
                    'smoke_level': round(smoke_level, 1),
                    'flame': round(flame_value, 0),
                    'light_level': round(latest_data.light_level, 1) if latest_data.light_level else 0,
                    'status': status,
                    'last_update': to_local_timestamp(latest_data.timestamp),
                    'is_online': True  # 添加在线状态标识
                })

        logger.info(f"返回 {len(result)} 个在线设备")
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error getting devices for fire alarm: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/devices/all')
def get_all_devices():
    """Get all devices (including slaves) for history dashboard"""
    try:
        # Get all devices from DeviceInfo
        devices = DeviceInfo.query.all()

        result = []
        for device in devices:
            result.append({
                'device_id': device.device_id,
                'device_type': device.device_type,
                'location': device.location,
                'status': device.status,
                'last_update': device.last_seen.isoformat() if device.last_seen else None
            })

        return jsonify(result)

    except Exception as e:
        logger.error(f"Error getting all devices: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/slaves/realtime')
def get_slaves_realtime():
    """Get all slaves real-time sensor data"""
    try:
        # 获取所有从机设备
        slave_devices = DeviceInfo.query.filter_by(device_type='slave').all()
        slave_ids = [device.device_id for device in slave_devices]

        result = []

        for slave_id in slave_ids:
            # 获取最新的传感器数据
            latest_data = SensorData.query.filter_by(device_id=slave_id)\
                                    .order_by(SensorData.timestamp.desc()).first()

            if latest_data:
                # 根据传感器值计算状态
                flame_value = latest_data.flame_value or 1200
                smoke_value = latest_data.smoke_value or 1800
                humidity = latest_data.humidity or 60

                # 从机报警逻辑（简化版，只有火焰和烟雾）
                if (flame_value < 500 or smoke_value < 1000):
                    status = "警报"
                elif (flame_value < 1000 or smoke_value < 1300):
                    status = "警告"
                else:
                    status = "正常"

                device = DeviceInfo.query.filter_by(device_id=slave_id).first()

                result.append({
                    'device_id': slave_id,
                    'device_type': 'slave',
                    'location': device.location if device else '未知位置',
                    'status': status,
                    'flame': latest_data.flame_value,
                    'smoke': latest_data.smoke_value,
                    'humidity': latest_data.humidity,
                    'temperature': latest_data.temperature,
                    'light_level': latest_data.light_level,
                    'timestamp': latest_data.timestamp.isoformat(),
                    'last_update': device.last_seen.isoformat() if device and device.last_seen else None
                })

        return jsonify(result)

    except Exception as e:
        logger.error(f"Error getting slaves realtime data: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/slaves/alerts')
def get_slaves_alerts():
    """Get recent alerts from slave devices"""
    try:
        # 获取最近24小时的从机警报
        since_time = datetime.utcnow() - timedelta(hours=24)

        # 获取所有从机ID
        slave_devices = DeviceInfo.query.filter_by(device_type='slave').all()
        slave_ids = [device.device_id for device in slave_devices]

        alerts = []
        for slave_id in slave_ids:
            # 获取该从机的传感器数据
            slave_data = SensorData.query.filter(
                SensorData.device_id == slave_id,
                SensorData.timestamp >= since_time
            ).order_by(SensorData.timestamp.desc()).limit(50).all()

            for data in slave_data:
                if data.alert_status in ['warning', 'alarm']:
                    alerts.append({
                        'device_id': slave_id,
                        'alert_type': data.alert_status,
                        'timestamp': data.timestamp.isoformat(),
                        'data': {
                            'flame': data.flame_value,
                            'smoke': data.smoke_value,
                            'temperature': data.temperature,
                            'humidity': data.humidity,
                            'light_level': data.light_level
                        },
                        'message': f"从机 {slave_id} 检测到{data.alert_status}"
                    })

        return jsonify(alerts)

    except Exception as e:
        logger.error(f"Error getting slaves alerts: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/history')
def get_alarm_history():
    """Get alarm history for fire alarm system"""
    try:
        # Get recent alerts from last 24 hours
        since_time = datetime.utcnow() - timedelta(hours=24)
        alerts = AlertHistory.query.filter(AlertHistory.timestamp >= since_time)\
                                 .order_by(AlertHistory.timestamp.desc()).limit(50).all()

        result = []
        for alert in alerts:
            device = DeviceInfo.query.filter_by(device_id=alert.device_id).first()
            location = device.location if device else alert.device_id

            result.append({
                'timestamp': to_local_timestamp(alert.timestamp),
                'device_id': alert.device_id,
                'location': location,
                'temperature': alert.temperature if hasattr(alert, 'temperature') else 25.0,
                'humidity': alert.humidity if hasattr(alert, 'humidity') else 50.0,
                'smoke_level': alert.smoke_value if hasattr(alert, 'smoke_value') else 0,
                'light_level': alert.light_level if hasattr(alert, 'light_level') else 1000,
                'status': alert.severity,
                'message': f"{location} 检测到{alert.alert_type}！"
            })

        return jsonify(result)
    except Exception as e:
        logger.error(f"Error getting alarm history: {e}")
        return jsonify({'error': str(e)}), 500

# Slave device API endpoints
@app.route('/api/slaves')
def get_slave_devices():
    """Get all slave devices"""
    try:
        # 数据超时时间（秒）- 超过这个时间没有新数据认为设备离线
        DATA_TIMEOUT = 300  # 5分钟

        slaves = DeviceInfo.query.filter_by(device_type='slave').all()
        # 使用 UTC 时间进行比较（与数据库存储的时间一致）
        current_time = datetime.utcnow()

        result = []
        for slave in slaves:
            # Get latest sensor data for this slave
            latest_data = SensorData.query.filter_by(device_id=slave.device_id)\
                                    .order_by(SensorData.timestamp.desc()).first()

            # 检查数据是否超时
            is_online = False
            if latest_data:
                data_age = (current_time - latest_data.timestamp).total_seconds()
                is_online = data_age < DATA_TIMEOUT
                logger.info(f"从机 {slave.device_id}: 数据年龄 {data_age:.0f} 秒, 在线={is_online}")

            # 只返回在线的从机设备
            if not is_online:
                continue

            result.append({
                'device_id': slave.device_id,
                'name': slave.name,
                'location': slave.location,
                'master_id': slave.master_id,
                'status': slave.status,
                'last_seen': to_local_timestamp(slave.last_seen) if slave.last_seen else None,
                'is_online': True,
                'latest_data': {
                    'flame': latest_data.flame_value if latest_data else 0,
                    'smoke': latest_data.smoke_value if latest_data else 0,
                    'temperature': latest_data.temperature if latest_data else 0,
                    'humidity': latest_data.humidity if latest_data else 0,
                    'light_level': latest_data.light_level if latest_data else 0,
                    'alert_status': latest_data.alert_status if latest_data else False,
                    'timestamp': to_local_timestamp(latest_data.timestamp) if latest_data else None
                } if latest_data else None
            })

        logger.info(f"返回 {len(result)} 个在线从机设备")
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error getting slave devices: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/slaves/<slave_id>/data')
def get_slave_data(slave_id):
    """Get recent data for specific slave"""
    try:
        limit = int(request.args.get('limit', 20))

        data = SensorData.query.filter_by(device_id=slave_id)\
                            .order_by(SensorData.timestamp.desc()).limit(limit).all()

        result = []
        for item in data:
            result.append({
                'id': item.id,
                'device_id': item.device_id,
                'device_type': item.device_type,
                'flame': item.flame_value,
                'smoke': item.smoke_value,
                'temperature': item.temperature,
                'humidity': item.humidity,
                'light_level': item.light_level,
                'alert_status': item.alert_status,
                'timestamp': to_local_timestamp(item.timestamp)
            })

        return jsonify(result)
    except Exception as e:
        logger.error(f"Error getting slave data: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/slaves/<slave_id>/status')
def get_slave_status(slave_id):
    """Get specific slave device status"""
    try:
        slave = Slave.query.filter_by(id=slave_id).first()
        if not slave:
            return jsonify({'error': '从机设备不存在'}), 404

        return jsonify({
            'id': slave.id,
            'device_id': slave.device_id,
            'name': slave.name,
            'status': slave.status,
            'last_seen': slave.last_seen.isoformat() if slave.last_seen else None,
            'created_at': slave.created_at.isoformat() if slave.created_at else None
        })
    except Exception as e:
        return jsonify({'error': f'获取从机状态失败: {str(e)}'}), 500

@app.route('/api/sensor/history')
def get_sensor_history():
    """Get sensor data history for miniprogram"""
    try:
        # 获取查询参数
        limit = int(request.args.get('limit', 100))  # 默认获取最近100条记录
        device_id = request.args.get('device_id')  # 可选的设备ID过滤

        # 构建查询
        query = SensorData.query

        if device_id:
            query = query.filter_by(device_id=device_id)

        # 按时间倒序排列，获取最新的数据
        history = query.order_by(SensorData.timestamp.desc()).limit(limit).all()

        result = []
        for record in history:
            result.append({
                'id': record.id,
                'device_id': record.device_id,
                'device_type': record.device_type,
                'flame': record.flame_value,
                'smoke': record.smoke_value,
                'temperature': record.temperature,
                'humidity': record.humidity,
                'light': record.light_level,
                'alert': record.alert_status,
                'timestamp': record.timestamp.isoformat()
            })

        return jsonify(result)

    except Exception as e:
        logger.error(f"Error getting sensor history: {e}")
        return jsonify({'error': str(e)}), 500

def get_slave_status(slave_id):
    """Get current status of specific slave"""
    try:
        device = DeviceInfo.query.filter_by(device_id=slave_id, device_type='slave').first()
        if not device:
            return jsonify({'error': 'Slave not found'}), 404

        # Get latest sensor data
        latest_data = SensorData.query.filter_by(device_id=slave_id)\
                                .order_by(SensorData.timestamp.desc()).first()

        # Calculate current status
        status = 'offline'
        flame_status = 'normal'
        smoke_status = 'normal'
        overall_status = 'normal'

        if device.status == 'online' and latest_data:
            status = 'online'

            # Slave status logic based on flame and smoke sensors
            flame_value = latest_data.flame_value or 1200
            smoke_value = latest_data.smoke_value or 1800

            if flame_value < 500 or smoke_value < 1000:
                overall_status = 'alarm'
                flame_status = 'alarm' if flame_value < 500 else 'normal'
                smoke_status = 'alarm' if smoke_value < 1000 else 'normal'
            elif flame_value < 1000 or smoke_value < 1300:
                overall_status = 'warning'
                flame_status = 'warning' if flame_value < 1000 else 'normal'
                smoke_status = 'warning' if smoke_value < 1300 else 'normal'

        return jsonify({
            'device_id': slave_id,
            'name': device.name,
            'location': device.location,
            'master_id': device.master_id,
            'status': status,
            'overall_status': overall_status,
            'flame_status': flame_status,
            'smoke_status': smoke_status,
            'last_seen': to_local_timestamp(device.last_seen) if device.last_seen else None,
            'latest_data': {
                'flame': latest_data.flame_value if latest_data else 0,
                'smoke': latest_data.smoke_value if latest_data else 0,
                'timestamp': to_local_timestamp(latest_data.timestamp) if latest_data else None
            } if latest_data else None
        })
    except Exception as e:
        logger.error(f"Error getting slave status: {e}")
        return jsonify({'error': str(e)}), 500

# WebSocket events removed for stability - using HTTP polling instead

# Test endpoint for generating test data
@app.route('/test_data')
def test_data():
    """Generate test sensor data"""
    try:
        # Generate test master device data
        test_master_data = {
            'timestamp': int(time.time()),
            'temperature': 26,
            'smoke': 1500,
            'light': 2.5,
            'humidity': 50,
            'status': 'normal',
            'flame': 1500,
            'device_id': 'esp32_fire_alarm_01'
        }

        # Generate test slave device data
        test_slave_data = {
            'slave_name': '测试从机-01',
            'sensors': {
                'flame': {'status': 'normal', 'digital': 1, 'analog': 1500},
                'mq2_smoke': {'status': 'normal', 'digital': 1, 'analog': 4095}
            },
            'slave_id': 'esp32_slave_test_01',
            'slave_location': '测试位置',
            'timestamp': int(time.time()),
            'type': 'sensor_data',
            'overall_status': 'normal',
            'sequence': 999
        }

        # Process test data
        with app.app_context():
            process_sensor_data(test_master_data)
            process_sensor_data(test_slave_data)

        return jsonify({
            'status': 'success',
            'message': 'Test data generated and processed',
            'master_data': test_master_data,
            'slave_data': test_slave_data
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/history/dashboard')
def get_dashboard_history():
    """Get historical data for dashboard with master/slave filtering"""
    try:
        # 获取查询参数
        hours = int(request.args.get('hours', 24))  # 默认24小时
        device_type = request.args.get('device_type', 'all')  # all, master, slave
        device_id = request.args.get('device_id')  # 特定设备ID

        # 计算时间范围
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(hours=hours)

        # 构建查询
        query = SensorData.query.filter(
            SensorData.timestamp >= start_time,
            SensorData.timestamp <= end_time
        )

        # 按设备类型过滤
        if device_type != 'all':
            query = query.filter_by(device_type=device_type)

        # 按设备ID过滤
        if device_id:
            query = query.filter_by(device_id=device_id)

        # 按时间排序
        history = query.order_by(SensorData.timestamp.asc()).all()

        # 按设备分组数据
        devices_data = {}
        for record in history:
            if record.device_id not in devices_data:
                devices_data[record.device_id] = {
                    'device_id': record.device_id,
                    'device_type': record.device_type,
                    'data': []
                }

            devices_data[record.device_id]['data'].append({
                'timestamp': record.timestamp.isoformat(),
                'flame': record.flame_value,
                'smoke': record.smoke_value,
                'temperature': record.temperature,
                'humidity': record.humidity,
                'light': record.light_level,
                'alert': record.alert_status
            })

        # 获取设备信息
        devices_info = {}
        for device_id in devices_data.keys():
            device = DeviceInfo.query.filter_by(device_id=device_id).first()
            if device:
                devices_info[device_id] = {
                    'location': device.location,
                    'status': device.status,
                    'last_update': device.last_seen.isoformat() if device.last_seen else None
                }

        # 组合结果
        result = {
            'time_range': {
                'start': start_time.isoformat(),
                'end': end_time.isoformat(),
                'hours': hours
            },
            'devices': []
        }

        for device_id, device_data in devices_data.items():
            device_info = devices_info.get(device_id, {})
            result['devices'].append({
                'device_id': device_id,
                'device_type': device_data['device_type'],
                'location': device_info.get('location', '未知位置'),
                'status': device_info.get('status', 'offline'),
                'last_update': device_info.get('last_update'),
                'data_points': len(device_data['data']),
                'data': device_data['data']
            })

        return jsonify(result)

    except Exception as e:
        logger.error(f"Error getting dashboard history: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/history/summary')
def get_history_summary():
    """Get historical data summary statistics"""
    try:
        # 获取查询参数
        hours = int(request.args.get('hours', 24))
        device_type = request.args.get('device_type', 'all')

        # 计算时间范围
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(hours=hours)

        # 构建查询
        query = SensorData.query.filter(
            SensorData.timestamp >= start_time,
            SensorData.timestamp <= end_time
        )

        if device_type != 'all':
            query = query.filter_by(device_type=device_type)

        history = query.all()

        if not history:
            return jsonify({
                'total_records': 0,
                'devices': [],
                'statistics': {
                    'avg_temperature': 0,
                    'avg_smoke': 0,
                    'avg_flame': 0,
                    'max_temperature': 0,
                    'alert_count': 0
                }
            })

        # 计算统计信息
        temps = [h.temperature for h in history if h.temperature is not None]
        smokes = [h.smoke_value for h in history if h.smoke_value is not None]
        flames = [h.flame_value for h in history if h.flame_value is not None]
        alerts = [h for h in history if h.alert_status in ['warning', 'alarm']]

        # 按设备分组统计
        device_stats = {}
        for record in history:
            if record.device_id not in device_stats:
                device_stats[record.device_id] = {
                    'device_id': record.device_id,
                    'device_type': record.device_type,
                    'data_count': 0,
                    'alert_count': 0,
                    'avg_temp': 0,
                    'max_temp': 0,
                    'avg_smoke': 0,
                    'last_update': None
                }

            stats = device_stats[record.device_id]
            stats['data_count'] += 1

            if record.alert_status in ['warning', 'alarm']:
                stats['alert_count'] += 1

            if record.temperature:
                stats['avg_temp'] = (stats['avg_temp'] * (stats['data_count'] - 1) + record.temperature) / stats['data_count']
                stats['max_temp'] = max(stats['max_temp'], record.temperature)

            if record.smoke_value:
                stats['avg_smoke'] = (stats['avg_smoke'] * (stats['data_count'] - 1) + record.smoke_value) / stats['data_count']

            # stats['last_update'] stores string, but we need to compare with datetime
            current_last_update_str = stats['last_update']
            if not current_last_update_str or record.timestamp > datetime.fromisoformat(current_last_update_str):
                stats['last_update'] = record.timestamp.isoformat()

        result = {
            'time_range': {
                'start': start_time.isoformat(),
                'end': end_time.isoformat(),
                'hours': hours
            },
            'total_records': len(history),
            'devices': list(device_stats.values()),
            'statistics': {
                'avg_temperature': sum(temps) / len(temps) if temps else 0,
                'avg_smoke': sum(smokes) / len(smokes) if smokes else 0,
                'avg_flame': sum(flames) / len(flames) if flames else 0,
                'max_temperature': max(temps) if temps else 0,
                'alert_count': len(alerts)
            }
        }

        return jsonify(result)

    except Exception as e:
        logger.error(f"Error getting history summary: {e}")
        return jsonify({'error': str(e)}), 500

# ========== 智能分析API端点 ==========

@app.route('/api/intelligence/analysis/<device_id>')
def get_device_intelligence_analysis(device_id):
    """获取设备智能分析数据"""
    try:
        # 获取传感器数据分析
        data_analysis = intelligent_analyzer.get_sensor_data_analysis(device_id, hours=24)

        # 获取设备健康评分
        health_score = intelligent_analyzer.get_device_health_score(device_id)

        # 获取AI维护建议
        ai_suggestions = intelligent_analyzer.get_ai_maintenance_suggestions(device_id, health_score)

        # 获取环境安全指数
        safety_index = intelligent_analyzer.get_environmental_safety_index(device_id)

        return jsonify({
            'device_id': device_id,
            'data_analysis': data_analysis,
            'health_score': health_score,
            'ai_suggestions': ai_suggestions,
            'safety_index': safety_index,
            'timestamp': datetime.now().isoformat()
        })

    except Exception as e:
        logger.error(f"Error getting intelligence analysis for {device_id}: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/intelligence/analysis')
def get_all_devices_intelligence_analysis():
    """获取所有设备的智能分析汇总"""
    try:
        # 获取所有设备
        devices = DeviceInfo.query.all()

        analysis_results = []

        for device in devices:
            try:
                # 获取设备健康评分
                health_score = intelligent_analyzer.get_device_health_score(device.device_id)

                # 获取环境安全指数
                safety_index = intelligent_analyzer.get_environmental_safety_index(device.device_id)

                analysis_results.append({
                    'device_id': device.device_id,
                    'device_type': device.device_type,
                    'location': device.location,
                    'health_score': health_score.get('score', 0),
                    'health_status': health_score.get('status', 'unknown'),
                    'safety_index': safety_index.get('overall_safety_index', 0),
                    'safety_level': safety_index.get('safety_level', 'unknown'),
                    'last_update': device.last_seen.isoformat() if device.last_seen else None
                })

            except Exception as e:
                logger.warning(f"Error analyzing device {device.device_id}: {e}")
                continue

        # 计算整体统计
        if analysis_results:
            avg_health = sum(r['health_score'] for r in analysis_results) / len(analysis_results)
            avg_safety = sum(r['safety_index'] for r in analysis_results) / len(analysis_results)

            # 按健康状态统计
            health_stats = {}
            for status in ['excellent', 'good', 'moderate', 'poor', 'critical']:
                health_stats[status] = len([r for r in analysis_results if r['health_status'] == status])

            # 按安全等级统计
            safety_stats = {}
            for level in ['very_safe', 'safe', 'moderate', 'risky', 'dangerous']:
                safety_stats[level] = len([r for r in analysis_results if r['safety_level'] == level])
        else:
            avg_health = avg_safety = 0
            health_stats = safety_stats = {}

        return jsonify({
            'summary': {
                'total_devices': len(analysis_results),
                'average_health_score': round(avg_health, 1),
                'average_safety_index': round(avg_safety, 1),
                'health_distribution': health_stats,
                'safety_distribution': safety_stats
            },
            'devices': analysis_results,
            'timestamp': datetime.now().isoformat()
        })

    except Exception as e:
        logger.error(f"Error getting all devices intelligence analysis: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/intelligence/trends/<device_id>')
def get_device_trends(device_id):
    """获取设备传感器数据趋势分析"""
    try:
        hours = request.args.get('hours', 48, type=int)

        # 获取趋势分析数据
        analysis = intelligent_analyzer.get_sensor_data_analysis(device_id, hours)

        if 'error' in analysis:
            return jsonify(analysis), 404

        # 计算趋势预测（简单线性预测）
        trends = {}
        for sensor_type, stats in analysis.get('statistics', {}).items():
            if isinstance(stats, dict) and 'trend' in stats:
                trends[sensor_type] = {
                    'current_trend': stats['trend'],
                    'stability': stats.get('stability', 'unknown'),
                    'anomalies_count': len(stats.get('anomalies', [])),
                    'recommendation': intelligent_analyzer._generate_data_recommendations({sensor_type: stats})
                }

        return jsonify({
            'device_id': device_id,
            'analysis_period': f"{hours}小时",
            'trends': trends,
            'statistics': analysis.get('statistics', {}),
            'recommendations': analysis.get('recommendations', []),
            'timestamp': datetime.now().isoformat()
        })

    except Exception as e:
        logger.error(f"Error getting device trends for {device_id}: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/intelligence/ai-suggestions/<device_id>')
def get_ai_suggestions(device_id):
    """获取AI智能维护建议"""
    try:
        # 获取设备健康评分
        health_score = intelligent_analyzer.get_device_health_score(device_id)

        # 获取AI建议
        ai_suggestions = intelligent_analyzer.get_ai_maintenance_suggestions(device_id, health_score)

        return jsonify(ai_suggestions)

    except Exception as e:
        logger.error(f"Error getting AI suggestions for {device_id}: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/intelligence/safety-index')
def get_overall_safety_index():
    """获取整体环境安全指数"""
    try:
        device_id = request.args.get('device_id')

        # 获取环境安全指数
        safety_index = intelligent_analyzer.get_environmental_safety_index(device_id)

        return jsonify(safety_index)

    except Exception as e:
        logger.error(f"Error getting safety index: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/intelligence/health-score/<device_id>')
def get_device_health_score(device_id):
    """获取设备健康评分"""
    try:
        health_score = intelligent_analyzer.get_device_health_score(device_id)
        return jsonify(health_score)

    except Exception as e:
        logger.error(f"Error getting health score for {device_id}: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/intelligence/statistics')
def get_system_statistics():
    """获取系统智能统计信息"""
    try:
        # 获取所有设备
        devices = DeviceInfo.query.all()

        if not devices:
            return jsonify({
                'total_devices': 0,
                'message': '暂无设备数据',
                'timestamp': datetime.now().isoformat()
            })

        # 统计分析
        device_types = {}
        health_scores = []
        safety_indices = []

        for device in devices:
            # 设备类型统计
            device_type = device.device_type or 'unknown'
            device_types[device_type] = device_types.get(device_type, 0) + 1

            # 获取健康评分
            try:
                health_score = intelligent_analyzer.get_device_health_score(device.device_id)
                health_scores.append(health_score.get('score', 0))
            except:
                health_scores.append(0)

            # 获取安全指数
            try:
                safety_index = intelligent_analyzer.get_environmental_safety_index(device.device_id)
                if 'overall_safety_index' in safety_index:
                    safety_indices.append(safety_index['overall_safety_index'])
            except:
                safety_indices.append(0)

        # 计算统计数据
        stats = {
            'total_devices': len(devices),
            'device_types': device_types,
            'health_statistics': {
                'average': round(sum(health_scores) / len(health_scores), 1) if health_scores else 0,
                'max': max(health_scores) if health_scores else 0,
                'min': min(health_scores) if health_scores else 0,
                'excellent_count': len([s for s in health_scores if s >= 90]),
                'good_count': len([s for s in health_scores if 75 <= s < 90]),
                'moderate_count': len([s for s in health_scores if 60 <= s < 75]),
                'poor_count': len([s for s in health_scores if s < 60])
            },
            'safety_statistics': {
                'average': round(sum(safety_indices) / len(safety_indices), 1) if safety_indices else 0,
                'max': max(safety_indices) if safety_indices else 0,
                'min': min(safety_indices) if safety_indices else 0,
                'very_safe_count': len([s for s in safety_indices if s >= 90]),
                'safe_count': len([s for s in safety_indices if 75 <= s < 90]),
                'moderate_count': len([s for s in safety_indices if 60 <= s < 75]),
                'risky_count': len([s for s in safety_indices if 40 <= s < 60]),
                'dangerous_count': len([s for s in safety_indices if s < 40])
            },
            'system_health': 'excellent' if (health_scores and sum(health_scores) / len(health_scores) >= 85) else 'good' if (health_scores and sum(health_scores) / len(health_scores) >= 70) else 'moderate',
            'timestamp': datetime.now().isoformat()
        }

        return jsonify(stats)

    except Exception as e:
        logger.error(f"Error getting system statistics: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/intelligence/recommendations')
def get_system_recommendations():
    """获取系统智能建议"""
    try:
        # 获取所有设备的分析
        devices = DeviceInfo.query.all()

        all_recommendations = []

        for device in devices:
            try:
                # 获取数据分析建议
                data_analysis = intelligent_analyzer.get_sensor_data_analysis(device.device_id, hours=24)
                if 'recommendations' in data_analysis:
                    for rec in data_analysis['recommendations']:
                        rec['device_id'] = device.device_id
                        rec['device_location'] = device.location
                        all_recommendations.append(rec)

                # 获取AI建议
                ai_suggestions = intelligent_analyzer.get_ai_maintenance_suggestions(device.device_id)
                if 'ai_suggestions' in ai_suggestions and 'suggestions' in ai_suggestions['ai_suggestions']:
                    for suggestion in ai_suggestions['ai_suggestions']['suggestions']:
                        suggestion['device_id'] = device.device_id
                        suggestion['device_location'] = device.location
                        suggestion['source'] = 'ai_analysis'
                        all_recommendations.append(suggestion)

            except Exception as e:
                logger.warning(f"Error getting recommendations for device {device.device_id}: {e}")
                continue

        # 按优先级排序
        priority_order = {'high': 1, 'medium': 2, 'low': 3}
        all_recommendations.sort(key=lambda x: priority_order.get(x.get('priority', 'low'), 3))

        # 统计建议类型
        recommendation_types = {}
        for rec in all_recommendations:
            rec_type = rec.get('type', 'general')
            recommendation_types[rec_type] = recommendation_types.get(rec_type, 0) + 1

        return jsonify({
            'recommendations': all_recommendations[:20],  # 最多返回20条建议
            'statistics': {
                'total_recommendations': len(all_recommendations),
                'high_priority_count': len([r for r in all_recommendations if r.get('priority') == 'high']),
                'medium_priority_count': len([r for r in all_recommendations if r.get('priority') == 'medium']),
                'low_priority_count': len([r for r in all_recommendations if r.get('priority') == 'low']),
                'recommendation_types': recommendation_types
            },
            'timestamp': datetime.now().isoformat()
        })

    except Exception as e:
        logger.error(f"Error getting system recommendations: {e}")
        return jsonify({'error': str(e)}), 500

# ========== AI决策系统API ==========

@app.route('/api/ai-decision/statistics')
def get_ai_decision_statistics():
    """获取AI决策统计信息"""
    try:
        hours = request.args.get('hours', 24, type=int)

        # 获取AI决策引擎统计
        ai_stats = ai_decision_engine.get_decision_statistics(hours)

        # 获取设备列表和各自的传感器健康度
        devices = DeviceInfo.query.all()
        device_health = {}

        for device in devices:
            try:
                health_score = ai_decision_engine.analyze_sensor_health(device.device_id)
                device_health[device.device_id] = {
                    'name': device.name,
                    'location': device.location,
                    'health_score': round(health_score, 2),
                    'health_status': 'good' if health_score >= 0.8 else 'warning' if health_score >= 0.6 else 'critical'
                }
            except Exception as e:
                logger.warning(f"Error analyzing health for device {device.device_id}: {e}")
                device_health[device.device_id] = {
                    'name': device.name,
                    'location': device.location,
                    'health_score': 0.5,
                    'health_status': 'unknown'
                }

        # 计算总体健康度
        if device_health:
            overall_health = np.mean([info['health_score'] for info in device_health.values()])
        else:
            overall_health = 0.5

        return jsonify({
            'ai_decision_stats': ai_stats,
            'device_health': device_health,
            'system_health': {
                'overall_score': round(overall_health, 2),
                'status': 'healthy' if overall_health >= 0.8 else 'warning' if overall_health >= 0.6 else 'critical',
                'total_devices': len(device_health),
                'healthy_devices': len([info for info in device_health.values() if info['health_score'] >= 0.8])
            },
            'decision_weights': ai_decision_engine.decision_weights,
            'threshold_config': {
                'high_confidence_threshold': 0.7,
                'low_confidence_threshold': 0.4,
                'sensor_health_threshold': ai_decision_engine.sensor_health_threshold
            },
            'timestamp': datetime.now().isoformat()
        })

    except Exception as e:
        logger.error(f"Error getting AI decision statistics: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/ai-decision/config', methods=['GET', 'POST'])
def ai_decision_config():
    """获取或更新AI决策配置"""
    try:
        if request.method == 'GET':
            return jsonify({
                'decision_weights': ai_decision_engine.decision_weights,
                'sensor_health_threshold': ai_decision_engine.sensor_health_threshold,
                'data_window_size': ai_decision_engine.window_size
            })

        elif request.method == 'POST':
            config_data = request.get_json()

            # 更新决策权重
            if 'decision_weights' in config_data:
                new_weights = config_data['decision_weights']
                # 验证权重总和为1.0
                total_weight = sum(new_weights.values())
                if abs(total_weight - 1.0) > 0.01:
                    return jsonify({'error': '权重总和必须等于1.0'}), 400

                ai_decision_engine.decision_weights.update(new_weights)

            # 更新传感器健康度阈值
            if 'sensor_health_threshold' in config_data:
                threshold = config_data['sensor_health_threshold']
                if 0 <= threshold <= 1:
                    ai_decision_engine.sensor_health_threshold = threshold

            # 更新数据窗口大小
            if 'data_window_size' in config_data:
                window_size = config_data['data_window_size']
                if window_size > 0:
                    ai_decision_engine.window_size = window_size

            logger.info("AI决策配置已更新")
            return jsonify({
                'message': '配置更新成功',
                'current_config': {
                    'decision_weights': ai_decision_engine.decision_weights,
                    'sensor_health_threshold': ai_decision_engine.sensor_health_threshold,
                    'data_window_size': ai_decision_engine.window_size
                }
            })

    except Exception as e:
        logger.error(f"Error handling AI decision config: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/ai-decision/analyze/<device_id>')
def analyze_device_ai_decision(device_id):
    """分析特定设备的AI决策历史"""
    try:
        # 获取设备最近的传感器数据
        recent_data = ai_decision_engine.get_recent_data(device_id, seconds=60)

        # 获取设备环境画像
        device_profile = ai_decision_engine.device_profiles.get(device_id, {})

        # 获取最近的AI决策
        recent_decisions = [d for d in ai_decision_engine.alarm_history
                          if d['device_id'] == device_id][-10:]

        # 分析传感器健康度
        sensor_health = ai_decision_engine.analyze_sensor_health(device_id)

        # 模拟AI决策过程
        if recent_data:
            current_data = recent_data[-1]
            # 临时设置硬件结果为正常来触发分析
            mock_hardware_result = 'normal'
            mock_decision = ai_decision_engine.make_decision(device_id, current_data, mock_hardware_result)
        else:
            mock_decision = None

        return jsonify({
            'device_id': device_id,
            'analysis_time': datetime.now().isoformat(),
            'sensor_health': round(sensor_health, 3),
            'health_status': 'good' if sensor_health >= 0.8 else 'warning' if sensor_health >= 0.6 else 'critical',
            'device_profile': {
                'flame_baseline': round(device_profile.get('flame_baseline', 0), 2),
                'smoke_baseline': round(device_profile.get('smoke_baseline', 0), 2),
                'temp_baseline': round(device_profile.get('temp_baseline', 25), 2),
                'humidity_baseline': round(device_profile.get('humidity_baseline', 50), 2),
                'light_baseline': round(device_profile.get('light_baseline', 10), 2)
            },
            'recent_data_count': len(recent_data),
            'recent_decisions_count': len(recent_decisions),
            'mock_analysis': mock_decision,
            'decision_engine_status': 'active',
            'data_quality': 'sufficient' if len(recent_data) >= 5 else 'insufficient'
        })

    except Exception as e:
        logger.error(f"Error analyzing device AI decision for {device_id}: {e}")
        return jsonify({'error': str(e)}), 500

# ========== 智能分析WebSocket事件 ==========

@socketio.on('request_intelligence_update')
def handle_intelligence_update_request(data):
    """处理智能分析更新请求"""
    try:
        device_id = data.get('device_id')

        if device_id:
            # 获取特定设备的智能分析
            analysis = intelligent_analyzer.get_sensor_data_analysis(device_id, hours=24)
            health_score = intelligent_analyzer.get_device_health_score(device_id)

            socketio.emit('intelligence_update', {
                'device_id': device_id,
                'analysis': analysis,
                'health_score': health_score,
                'timestamp': datetime.now().isoformat()
            })
        else:
            # 获取所有设备的汇总分析
            all_analysis = intelligent_analyzer.get_all_devices_intelligence_analysis()
            socketio.emit('intelligence_update', all_analysis)

    except Exception as e:
        logger.error(f"Error handling intelligence update request: {e}")
        socketio.emit('intelligence_error', {
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        })

# Scheduled cleanup of expired data
def cleanup_old_data():
    """Clean up data older than 30 days"""
    while True:
        try:
            with app.app_context():
                cutoff_time = datetime.utcnow() - timedelta(days=30)
                old_data = SensorData.query.filter(SensorData.timestamp < cutoff_time).delete()
                db.session.commit()
                logger.info(f"Cleaned up {old_data} expired records")
        except Exception as e:
            logger.error(f"Error cleaning up data: {e}")
        time.sleep(86400)  # Execute once daily

# Start cleanup thread
cleanup_thread = threading.Thread(target=cleanup_old_data, daemon=True)
cleanup_thread.start()

if __name__ == '__main__':
    logger.info("Starting ESP32 Dormitory Fire Alarm System Web Server...")
    logger.info("Access URL: http://localhost:5000")
    logger.info(f"MQTT Broker: {app.config['MQTT_BROKER_URL']}:{app.config['MQTT_BROKER_PORT']}")
    logger.info("Please check MQTT connection status in the logs...")

    # 启动Flask-SocketIO服务器
    host = os.environ.get('FIRE_ALARM_HOST', '0.0.0.0')
    port = int(os.environ.get('FIRE_ALARM_PORT', '5001'))

    logger.info(f"Access URL: http://127.0.0.1:{port}")

    # In PyInstaller bundles, disable reloader to avoid path issues
    use_reloader = not getattr(sys, 'frozen', False)
    socketio.run(app, host=host, port=port, debug=use_reloader, allow_unsafe_werkzeug=True)
