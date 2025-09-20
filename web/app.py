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
from flask_socketio import SocketIO
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
import paho.mqtt.client as mqtt
import sqlite3
import json
import time
import os
from datetime import datetime, timedelta, timezone
import threading
import logging

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

# Flask application initialization
app = Flask(__name__)
app.config['SECRET_KEY'] = 'esp32_fire_alarm_system_2024'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///fire_alarm.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# MQTT configuration
app.config['MQTT_BROKER_URL'] = '192.168.24.32'
app.config['MQTT_BROKER_PORT'] = 1883
app.config['MQTT_USERNAME'] = ''
app.config['MQTT_PASSWORD'] = ''
app.config['MQTT_KEEPALIVE'] = 60
app.config['MQTT_TLS_ENABLED'] = False

# Initialize extensions
db = SQLAlchemy(app)
socketio = SocketIO(app, cors_allowed_origins="*")
CORS(app)

# MQTT client setup
mqtt_client = mqtt.Client()

def on_connect(client, userdata, flags, rc):
    """MQTT连接回调"""
    logger.info(f"MQTT连接成功，返回码: {rc}")
    logger.info(f"Connected to broker: {app.config['MQTT_BROKER_URL']}:{app.config['MQTT_BROKER_PORT']}")
    # 订阅主题
    client.subscribe('esp32/+/data/json')
    client.subscribe('esp32/+/alert/#')
    client.subscribe('esp32/+/status/#')
    logger.info("MQTT主题订阅: esp32/+/data/json, esp32/+/alert/#, esp32/+/status/#")

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
    last_seen = db.Column(db.DateTime)
    status = db.Column(db.String(20), default='online')
    config = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# Create database tables
with app.app_context():
    db.create_all()

# MQTT连接已通过paho-mqtt直接处理

def process_sensor_data(data):
    """Process sensor data"""
    try:
        # Save to database
        sensor_data = SensorData(
            device_id=data.get('device_id', 'unknown'),
            flame_value=data.get('flame', 0),
            smoke_value=data.get('smoke', 0),
            temperature=data.get('temperature'),
            humidity=data.get('humidity'),
            light_level=data.get('light'),  # 光照传感器数据
            alert_status=data.get('alert', False)
        )
        db.session.add(sensor_data)
        db.session.commit()
        
        # Update device status
        device = DeviceInfo.query.filter_by(device_id=data.get('device_id')).first()
        if device:
            device.last_seen = datetime.utcnow()
            device.status = 'online'
        else:
            # Create new device record
            device = DeviceInfo(
                device_id=data.get('device_id'),
                name=f"ESP32-{data.get('device_id', 'unknown')}",
                location='Dormitory',
                last_seen=datetime.utcnow(),
                status='online'
            )
            db.session.add(device)
        db.session.commit()
        
        # Real-time push to frontend via WebSocket (for old UI)
        socketio.emit('sensor_data', data)
        
        # Send device update to 5-layer architecture UI
        send_device_update_to_ui(data.get('device_id'))
        
        logger.info(f"Sensor data saved and pushed: {data.get('device_id')}")
        
    except Exception as e:
        logger.error(f"Error processing sensor data: {e}")
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
        # Save alert record
        alert = AlertHistory(
            device_id=alert_data.get('device_id'),
            alert_type=alert_data.get('alert_type', 'unknown'),
            severity=alert_data.get('severity', 'medium'),
            flame_value=alert_data.get('sensor_values', {}).get('flame'),
            smoke_value=alert_data.get('sensor_values', {}).get('smoke'),
            temperature=alert_data.get('sensor_values', {}).get('temperature'),
            humidity=alert_data.get('sensor_values', {}).get('humidity'),
            light_level=alert_data.get('sensor_values', {}).get('light'),  # 光照传感器数据
            location=alert_data.get('location', 'Unknown location')
        )
        db.session.add(alert)
        db.session.commit()
        
        # Push alert information to frontend
        socketio.emit('alert_data', alert_data)
        logger.warning(f"Alert record created: {alert_data.get('device_id')} - {alert_data.get('alert_type')}")
        
    except Exception as e:
        logger.error(f"Error processing alert data: {e}")
        db.session.rollback()

# Flask routes
@app.route('/')
def index():
    """Homepage - ESP32 fire alarm system with 5-layer architecture"""
    return render_template('index.html')

@app.route('/dashboard')
def dashboard():
    """Dashboard page - detailed data visualization"""
    return render_template('dashboard.html')

@app.route('/monitor')
def monitor():
    """MQTT real-time monitoring page"""
    return render_template('monitor.html')

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

# ESP32 Fire Alarm System API Routes
@app.route('/api/devices')
def get_devices():
    """Get all device status for fire alarm system"""
    try:
        # Only return devices that have actual sensor data
        sensor_devices = db.session.query(SensorData.device_id.distinct()).all()
        device_ids = [device[0] for device in sensor_devices]
        
        result = []
        
        for device_id in device_ids:
            # Get device info
            device = DeviceInfo.query.filter_by(device_id=device_id).first()
            
            # Get latest sensor data for this device
            latest_data = SensorData.query.filter_by(device_id=device_id)\
                                    .order_by(SensorData.timestamp.desc()).first()
            
            if latest_data:
                temperature = latest_data.temperature or 0
                smoke_level = latest_data.smoke_value or 0
                
                # Determine status based on sensor values (fire alarm logic)
                flame_value = latest_data.flame_value or 1200  # Default normal flame value
                humidity = latest_data.humidity or 60  # Default normal humidity value
                
                # Fire alarm logic with all 5 sensors
                if (flame_value < 1000 or      # Low flame indicates fire
                    smoke_level > 100 or       # High smoke
                    temperature > 40 or        # High temperature
                    humidity < 20 or           # Very low humidity (fire risk)
                    humidity > 90):           # Very high humidity (electrical risk)
                    status = "警报"
                elif (flame_value < 1100 or     # Low flame warning
                      smoke_level > 50 or      # Moderate smoke
                      temperature > 35 or      # High temperature warning
                      humidity <= 30 or        # Low humidity warning (包含等于30)
                      humidity > 80):          # High humidity warning
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
                    'last_update': to_local_timestamp(device.last_seen if device else None)
                })
        
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error getting devices for fire alarm: {e}")
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

# WebSocket events
@socketio.on('connect')
def handle_connect():
    """WebSocket connection event"""
    logger.info('Client connected')
    socketio.emit('connection_status', {'status': 'connected'})
    # Send initial device data to connected client
    try:
        with app.app_context():
            devices_data = get_devices().get_json()
            socketio.emit('devices_update', devices_data)
    except Exception as e:
        logger.error(f"Error sending initial device data: {e}")

@socketio.on('disconnect')
def handle_disconnect():
    """WebSocket disconnection event"""
    logger.info('Client disconnected')

@socketio.on('request_device_update')
def handle_device_update_request():
    """Handle request for device status update"""
    try:
        with app.app_context():
            devices_data = get_devices().get_json()
            socketio.emit('devices_update', devices_data)
    except Exception as e:
        logger.error(f"Error handling device update request: {e}")

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

    # 启动服务器，使用端口5001
    socketio.run(app, host='0.0.0.0', port=5000, debug=True, allow_unsafe_werkzeug=True)