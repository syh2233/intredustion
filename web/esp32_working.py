#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ESP32 Fire Alarm System - Working Version
Fixed DHT22 and OLED issues
"""

import machine
import time
import json
import network
from machine import Pin, ADC, PWM
import sys
import socket
import struct
try:
    import utime
    time_module = utime
except ImportError:
    time_module = time

# Sensor pin configuration
DHT_PIN = 32
FLAME_PIN = 34
SMOKE_PIN = 35
LIGHT_PIN = 33
SOUND_PIN = 25
SERVO_PIN = 26
FAN_PIN = 19
BUZZER_PIN = 27
OLED_SDA_PIN = 23
OLED_SCL_PIN = 18

# WiFi configuration
WIFI_SSID = "syh2031"
WIFI_PASSWORD = "12345678"

# MQTT server configuration - 优先使用本地服务
MQTT_SERVERS = [
    {"server": "192.168.24.32", "port": 1883, "name": "Computer Mosquitto"}, # 电脑的真实IP
    {"server": "192.168.24.1", "port": 1883, "name": "Router"}, # 路由器IP
    {"server": "test.mosquitto.org", "port": 1883, "name": "Public Mosquitto"}, # 公共服务器
]

def connect_wifi():
    """Connect to WiFi network"""
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)

    if not wlan.isconnected():
        print(f"Connecting to WiFi: {WIFI_SSID}")
        wlan.connect(WIFI_SSID, WIFI_PASSWORD)

        # Wait for connection
        timeout = 0
        while not wlan.isconnected() and timeout < 30:
            time.sleep(1)
            timeout += 1
            print(f".", end="")

        print()

        if wlan.isconnected():
            print("WiFi connected!")
            print(f"IP address: {wlan.ifconfig()[0]}")
            return True
        else:
            print("WiFi connection failed!")
            return False
    else:
        print("Already connected to WiFi")
        print(f"IP address: {wlan.ifconfig()[0]}")
        return True

# Initialize sensors
print("Initializing sensors...")

# Initialize DHT22 with error handling
dht_available = False
dht_sensor = None
try:
    import dht
    dht_sensor = dht.DHT22(machine.Pin(DHT_PIN))
    print("DHT22 sensor initialized")
    dht_available = True
except Exception as e:
    print(f"DHT22 init failed: {e}")
    dht_sensor = None
    dht_available = False

# Test DHT22 sensor immediately
if dht_available and dht_sensor:
    try:
        dht_sensor.measure()
        temp_test = dht_sensor.temperature()
        humid_test = dht_sensor.humidity()
        print(f"DHT22 test successful: {temp_test}°C, {humid_test}%")
    except Exception as e:
        print(f"DHT22 test failed: {e}")
        dht_available = False
        dht_sensor = None

# Initialize ADC with proper attenuation for 0-3.3V range
try:
    flame_adc = ADC(Pin(FLAME_PIN))
    flame_adc.atten(ADC.ATTN_11DB)  # Full range: 0-3.3V
except:
    print("Warning: Flame ADC init failed, using digital mode")
    flame_adc = Pin(FLAME_PIN, Pin.IN)

try:
    smoke_adc = ADC(Pin(SMOKE_PIN))
    smoke_adc.atten(ADC.ATTN_11DB)  # Full range: 0-3.3V
except:
    print("Warning: Smoke ADC init failed, using digital mode")
    smoke_adc = Pin(SMOKE_PIN, Pin.IN)

try:
    light_adc = ADC(Pin(LIGHT_PIN))
    light_adc.atten(ADC.ATTN_11DB)  # Full range: 0-3.3V
except:
    print("Warning: Light ADC init failed, using digital mode")
    light_adc = Pin(LIGHT_PIN, Pin.IN)

try:
    sound_adc = ADC(Pin(SOUND_PIN))
    sound_adc.atten(ADC.ATTN_11DB)  # Full range: 0-3.3V
except:
    print("Warning: Sound ADC init failed, using digital mode")
    sound_adc = Pin(SOUND_PIN, Pin.IN)
fan_pwm = PWM(Pin(FAN_PIN), freq=1000, duty=0)
buzzer_pin = Pin(BUZZER_PIN, Pin.OUT)
servo_pwm = PWM(Pin(SERVO_PIN), freq=50, duty=0)

# Initialize OLED
oled_available = False
oled = None
try:
    i2c = machine.SoftI2C(sda=machine.Pin(OLED_SDA_PIN), scl=machine.Pin(OLED_SCL_PIN))
    devices = i2c.scan()
    if 0x3C in devices:
        try:
            import ssd1306 as ssd1306
            oled = ssd1306.SSD1306_I2C(128, 64, i2c)
            print("OLED initialized")
            oled_available = True
        except:
            print("OLED driver import failed")
    else:
        print("OLED device not found")
except Exception as e:
    print(f"OLED init failed: {e}")

# MQTT client class
class SimpleMQTTClient:
    def __init__(self, client_id, server, port):
        self.client_id = client_id
        self.server = server
        self.port = port
        self.sock = None
        self.connected = False

    def connect(self):
        try:
            print(f"Connecting to MQTT: {self.server}:{self.port}")

            # Create socket connection
            self.sock = socket.socket()
            self.sock.settimeout(10)
            addr = socket.getaddrinfo(self.server, self.port)[0][-1]
            self.sock.connect(addr)
            print("TCP connected")

            # Build MQTT CONNECT message
            protocol_name = b"MQTT"
            protocol_level = 4  # MQTT 3.1.1
            flags = 0x02  # Clean session
            keep_alive = 60

            # Variable header
            var_header = bytearray()
            # Protocol name length field (MSB + LSB)
            var_header.append(0)  # MSB of protocol name length
            var_header.append(len(protocol_name))  # LSB of protocol name length
            var_header.extend(protocol_name)
            var_header.append(protocol_level)
            var_header.append(flags)
            var_header.append(keep_alive >> 8)
            var_header.append(keep_alive & 0xFF)

            # Payload
            payload = bytearray()
            client_id_bytes = self.client_id.encode()
            payload.append(len(client_id_bytes) >> 8)
            payload.append(len(client_id_bytes) & 0xFF)
            payload.extend(client_id_bytes)

            # Remaining length
            remaining_length = len(var_header) + len(payload)

            # Complete message
            connect_msg = bytearray()
            connect_msg.append(0x10)  # CONNECT

            if remaining_length < 128:
                connect_msg.append(remaining_length)
            else:
                connect_msg.append((remaining_length & 0x7F) | 0x80)
                connect_msg.append(remaining_length >> 7)

            connect_msg.extend(var_header)
            connect_msg.extend(payload)

            # Send connection message
            self.sock.send(connect_msg)

            # Wait for CONNACK
            response = self.sock.recv(1024)
            print(f"CONNACK response: {response}")

            if len(response) >= 4:
                # Parse CONNACK message
                msg_type = response[0]
                msg_len = response[1]
                protocol_ack = response[2]
                return_code = response[3]

                print(f"MQTT Response: Type={msg_type}, Length={msg_len}, Ack={protocol_ack}, Return={return_code}")

                if msg_type == 0x20 and return_code == 0x00:
                    self.connected = True
                    print("MQTT connected successfully")
                    return True
                else:
                    raise Exception(f"MQTT connection rejected, return code: {return_code}")
            else:
                raise Exception(f"Invalid CONNACK response: {response}")

        except Exception as e:
            print(f"MQTT connection failed: {e}")
            if self.sock:
                self.sock.close()
            self.connected = False
            return False

    def publish(self, topic, message):
        if not self.connected:
            return False

        try:
            topic_bytes = topic.encode()
            message_bytes = message.encode()

            # Calculate remaining length
            topic_length = len(topic_bytes)
            message_length = len(message_bytes)
            remaining_length = 2 + topic_length + message_length

            # Check if message is too long
            if remaining_length > 127:
                print(f"Warning: Message too long ({remaining_length} bytes), truncating...")
                # Truncate message
                max_message_length = 127 - 2 - topic_length
                message_bytes = message_bytes[:max_message_length]
                message_length = len(message_bytes)
                remaining_length = 2 + topic_length + message_length

            # Build PUBLISH message
            publish_msg = bytearray()
            publish_msg.append(0x30)  # PUBLISH QoS 0

            # Add remaining length
            publish_msg.append(remaining_length)

            # Add topic length
            publish_msg.append(topic_length >> 8)
            publish_msg.append(topic_length & 0xFF)

            # Add topic name
            publish_msg.extend(topic_bytes)

            # Add message content
            publish_msg.extend(message_bytes)

            self.sock.send(publish_msg)
            return True

        except Exception as e:
            print(f"Publish failed: {e}")
            return False

    def disconnect(self):
        if self.sock and self.connected:
            try:
                self.sock.send(b"\xE0\x00")  # DISCONNECT
                self.sock.close()
            except:
                pass
            finally:
                self.connected = False

# Connect to WiFi first
print("\nConnecting to WiFi...")
wifi_connected = connect_wifi()

# Test MQTT server connections only if WiFi is connected
print("\nTesting MQTT server connections...")
mqtt_client = None
mqtt_server_name = "Local Mode"

if wifi_connected:
    for config in MQTT_SERVERS:
        try:
            client_id = f"ESP32-FIRE-{int(time_module.time())}"
            client = SimpleMQTTClient(client_id, config['server'], config['port'])
            print(f"Trying {config['name']}: {config['server']}:{config['port']}")

            if client.connect():
                mqtt_client = client
                mqtt_server_name = config['name']
                print(f"Connected to: {config['name']}")
                break
            else:
                print(f"{config['name']} connection failed")

        except Exception as e:
            print(f"{config['name']} connection error: {e}")
else:
    print("WiFi not connected, skipping MQTT connection")

if not mqtt_client:
    print("All MQTT servers failed, using local mode")

# Alarm thresholds - 调整为更合适的值
FLAME_THRESHOLD = 800   # 火焰检测阈值降低
SMOKE_THRESHOLD = 1500  # 烟雾检测阈值提高
TEMP_THRESHOLD = 45     # 温度阈值提高
HUMIDITY_THRESHOLD = 85  # 湿度阈值提高

# Warning thresholds
FLAME_WARN_THRESHOLD = 1000  # 火焰警告阈值
SMOKE_WARN_THRESHOLD = 1200   # 烟雾警告阈值
TEMP_WARN_THRESHOLD = 40      # 温度警告阈值
HUMIDITY_WARN_THRESHOLD = 75 # 湿度警告阈值

# Environment thresholds
LIGHT_DARK_THRESHOLD = 500
SOUND_LOUD_THRESHOLD = 2000

# System states
SYSTEM_STATUS_NORMAL = "normal"
SYSTEM_STATUS_WARNING = "warning"
SYSTEM_STATUS_ALARM = "alarm"

current_status = SYSTEM_STATUS_NORMAL
status_cooldown = 0

def read_all_sensors():
    """Read all sensor data"""
    try:
        # Read DHT22 only if available
        if dht_available and dht_sensor:
            try:
                dht_sensor.measure()
                temperature = dht_sensor.temperature()
                humidity = dht_sensor.humidity()
            except Exception as e:
                print(f"DHT22 read error: {e}")
                temperature = 25.0
                humidity = 60.0
        else:
            # Simulate temperature/humidity if DHT22 not available
            temperature = 25.0
            humidity = 60.0
            print("Using simulated temperature/humidity data")

        # Read flame sensor with error handling
        flame_samples = []
        for i in range(3):
            try:
                if hasattr(flame_adc, 'read'):
                    sample = flame_adc.read()
                    if sample is not None:
                        flame_samples.append(sample)
                else:
                    sample = flame_adc.value()
                    if sample is not None:
                        flame_samples.append(sample)
                time.sleep(0.01)
            except Exception as e:
                print(f"Flame sensor read error (attempt {i+1}): {e}")
                continue

        if flame_samples:
            flame_value = sum(flame_samples) // len(flame_samples)
        else:
            flame_value = 2000  # Default safe value
            print("Flame sensor failed, using default value")

        # Read smoke sensor with error handling
        smoke_samples = []
        for i in range(3):
            try:
                if hasattr(smoke_adc, 'read'):
                    sample = smoke_adc.read()
                    if sample is not None:
                        smoke_samples.append(sample)
                else:
                    sample = smoke_adc.value()
                    if sample is not None:
                        smoke_samples.append(sample)
                time.sleep(0.01)
            except Exception as e:
                print(f"Smoke sensor read error (attempt {i+1}): {e}")
                continue

        if smoke_samples:
            smoke_value = sum(smoke_samples) // len(smoke_samples)
        else:
            smoke_value = 500  # Default safe value
            print("Smoke sensor failed, using default value")

        # Read light sensor with error handling
        light_samples = []
        for i in range(3):
            try:
                if hasattr(light_adc, 'read'):
                    sample = light_adc.read()
                    if sample is not None:
                        light_samples.append(sample)
                else:
                    sample = light_adc.value()
                    if sample is not None:
                        light_samples.append(sample)
                time.sleep(0.01)
            except Exception as e:
                print(f"Light sensor read error (attempt {i+1}): {e}")
                continue

        if light_samples:
            light_value = sum(light_samples) // len(light_samples)
        else:
            light_value = 1000  # Default safe value
            print("Light sensor failed, using default value")

        # Read sound sensor with error handling
        sound_samples = []
        for i in range(5):
            try:
                if hasattr(sound_adc, 'read'):
                    sample = sound_adc.read()
                    if sample is not None:
                        sound_samples.append(sample)
                else:
                    sample = sound_adc.value()
                    if sample is not None:
                        sound_samples.append(sample)
                time.sleep(0.01)
            except Exception as e:
                print(f"Sound sensor read error (attempt {i+1}): {e}")
                continue

        if sound_samples:
            sound_value = max(sound_samples)
        else:
            sound_value = 100  # Default safe value
            print("Sound sensor failed, using default value")

        if temperature is None or humidity is None:
            return None

        return {
            'temperature': temperature,
            'humidity': humidity,
            'flame': flame_value,
            'smoke': smoke_value,
            'light': light_value,
            'sound': sound_value
        }

    except Exception as e:
        print(f"Sensor read failed: {e}")
        return None

def check_system_status(sensor_data):
    """Check system status"""
    if sensor_data is None:
        return SYSTEM_STATUS_NORMAL, "Invalid sensor data"

    temp = sensor_data['temperature']
    humidity = sensor_data['humidity']
    flame = sensor_data['flame']
    smoke = sensor_data['smoke']

    alarm_reasons = []
    if flame < FLAME_THRESHOLD:
        alarm_reasons.append("Flame detected")
    if smoke > SMOKE_THRESHOLD:
        alarm_reasons.append("Smoke detected")
    if temp > TEMP_THRESHOLD:
        alarm_reasons.append("High temperature")
    if humidity > HUMIDITY_THRESHOLD:
        alarm_reasons.append("High humidity")

    if len(alarm_reasons) > 0:
        return SYSTEM_STATUS_ALARM, ", ".join(alarm_reasons)

    warning_reasons = []
    if flame < FLAME_WARN_THRESHOLD:
        warning_reasons.append("Low flame")
    if smoke > SMOKE_WARN_THRESHOLD:
        warning_reasons.append("High smoke")
    if temp > TEMP_WARN_THRESHOLD:
        warning_reasons.append("High temp")
    if humidity > HUMIDITY_WARN_THRESHOLD:
        warning_reasons.append("High humidity")

    if len(warning_reasons) > 0:
        return SYSTEM_STATUS_WARNING, ", ".join(warning_reasons)

    return SYSTEM_STATUS_NORMAL, "Environment normal"

def control_servo(angle):
    """Control servo angle"""
    try:
        duty = int(26 + (angle / 180) * 103)
        servo_pwm.duty(duty)
    except Exception as e:
        print(f"Servo control failed: {e}")

def control_buzzer(system_status, sound_level):
    """Control buzzer"""
    try:
        if system_status == SYSTEM_STATUS_ALARM:
            buzzer_pin.value(1)
            time.sleep(0.1)
            buzzer_pin.value(0)
        elif system_status == SYSTEM_STATUS_WARNING or sound_level > SOUND_LOUD_THRESHOLD:
            buzzer_pin.value(1)
            time.sleep(0.3)
            buzzer_pin.value(0)
        else:
            buzzer_pin.value(0)
    except Exception as e:
        print(f"Buzzer control failed: {e}")

def control_fan(temperature, system_status):
    """Control fan speed"""
    try:
        if system_status == SYSTEM_STATUS_ALARM:
            fan_pwm.duty(1023)
        elif system_status == SYSTEM_STATUS_WARNING or temperature > 30:
            fan_pwm.duty(512)
        else:
            fan_pwm.duty(0)
    except Exception as e:
        print(f"Fan control failed: {e}")

def update_oled_display(sensor_data, system_status, status_reason):
    """Update OLED display"""
    if not oled_available or oled is None:
        return

    try:
        oled.fill(0)

        if system_status == SYSTEM_STATUS_ALARM:
            oled.text("FIRE ALARM", 0, 0, 1)
            oled.text(status_reason[:12], 0, 16, 1)
            oled.text("T:" + str(int(sensor_data['temperature'])) + "C", 0, 32, 1)
            oled.text("S:" + str(sensor_data['smoke']), 64, 32, 1)
        elif system_status == SYSTEM_STATUS_WARNING:
            oled.text("WARNING", 0, 0, 1)
            oled.text(status_reason[:12], 0, 16, 1)
            oled.text("T:" + str(int(sensor_data['temperature'])) + "C", 0, 32, 1)
            oled.text("H:" + str(int(sensor_data['humidity'])) + "%", 64, 32, 1)
        else:
            oled.text("NORMAL", 0, 0, 1)
            oled.text("T:" + str(int(sensor_data['temperature'])) + "C", 0, 16, 1)
            oled.text("H:" + str(int(sensor_data['humidity'])) + "%", 64, 16, 1)
            oled.text("MQTT:OK", 0, 32, 1)

        oled.show()

    except Exception as e:
        print(f"OLED display failed: {e}")

def send_mqtt_data(sensor_data, system_status, status_reason):
    """Send MQTT data"""
    if mqtt_client is None:
        return

    try:
        data = {
            "device_id": mqtt_client.client_id[:20],
            "timestamp": time_module.time(),
            "data": {
                "temperature": round(sensor_data['temperature'], 1),
                "humidity": round(sensor_data['humidity'], 1),
                "flame": sensor_data['flame'],
                "smoke": sensor_data['smoke'],
                "light": sensor_data['light'],
                "sound": sensor_data['sound']
            },
            "status": {
                "system_status": system_status,
                "status_reason": status_reason,
                "mqtt_server": mqtt_server_name
            },
            "location": "Dormitory A301"
        }

        payload = json.dumps(data)
        topic = f"esp32/fire_alarm/data"
        if mqtt_client.publish(topic, payload):
            print("MQTT data sent")

        if system_status == SYSTEM_STATUS_ALARM:
            alert_topic = f"esp32/fire_alarm/alert"
            mqtt_client.publish(alert_topic, payload)

    except Exception as e:
        print(f"MQTT send failed: {e}")

def print_status_message(sensor_data, system_status, status_reason):
    """Print status message"""
    status_symbols = {
        SYSTEM_STATUS_NORMAL: "OK",
        SYSTEM_STATUS_WARNING: "WARN",
        SYSTEM_STATUS_ALARM: "ALARM"
    }

    symbol = status_symbols.get(system_status, "?")
    # 使用utime.localtime获取时间，而不是strftime
    try:
        local_time = time_module.localtime()
        time_str = f"{local_time[3]:02d}:{local_time[4]:02d}:{local_time[5]:02d}"
    except:
        time_str = time_module.ticks_ms() // 1000  # 使用时间戳作为备选
    temp_str = str(round(sensor_data['temperature'], 1))
    humid_str = str(round(sensor_data['humidity'], 1))
    flame_str = str(sensor_data['flame'])
    smoke_str = str(sensor_data['smoke'])

    print("[" + symbol + "] " + time_str + " [" + mqtt_server_name + "] " + system_status.upper())
    print("Reason: " + status_reason)
    print("Temp: " + temp_str + "C, Humidity: " + humid_str + "%")
    print("Flame: " + flame_str + ", Smoke: " + smoke_str)
    print("----------------------------------------")

def main():
    """Main function"""
    print("ESP32 Fire Alarm System - Working Version")
    print("========================================")
    print(f"Board: {sys.implementation.name} {sys.implementation.version}")
    print(f"WiFi SSID: {WIFI_SSID}")
    print(f"WiFi Status: {'Connected' if wifi_connected else 'Not Connected'}")
    print(f"MQTT Status: {mqtt_server_name}")

    if wifi_connected:
        wlan = network.WLAN(network.STA_IF)
        print(f"IP Address: {wlan.ifconfig()[0]}")

    print(f"DHT22 Sensor: {'OK' if dht_available else 'Failed'}")
    print(f"OLED Display: {'OK' if oled_available else 'Failed'}")

    if mqtt_client:
        print(f"✅ Connected to MQTT: {mqtt_client.server}:{mqtt_client.port}")
        print(f"Monitor command: mosquitto_sub -h {mqtt_client.server} -t \"esp32/fire_alarm/data\" -v")
    else:
        if not wifi_connected:
            print("❌ WiFi not connected, check network settings")
        else:
            print("⚠️ WiFi connected but MQTT failed, running in local mode")

    print("========================================")
    print("Starting main loop...")
    print("Press Ctrl+C to stop")
    print("========================================")

    global current_status, status_cooldown

    # Main loop
    while True:
        try:
            sensor_data = read_all_sensors()

            if sensor_data is not None:
                new_status, status_reason = check_system_status(sensor_data)

                if new_status != current_status and status_cooldown == 0:
                    if new_status == SYSTEM_STATUS_ALARM:
                        print("Fire alarm triggered: " + status_reason)
                        control_servo(180)
                        status_cooldown = 10
                    elif new_status == SYSTEM_STATUS_WARNING:
                        print("Environment warning: " + status_reason)
                        control_servo(90)
                    elif current_status == SYSTEM_STATUS_ALARM:
                        print("Fire alarm cleared")
                        control_servo(0)
                    elif current_status == SYSTEM_STATUS_WARNING:
                        print("Environment warning cleared")
                        control_servo(0)

                    current_status = new_status

                control_fan(sensor_data['temperature'], current_status)
                control_buzzer(current_status, sensor_data['sound'])

                if sensor_data['light'] < LIGHT_DARK_THRESHOLD:
                    control_servo(45)

                update_oled_display(sensor_data, current_status, status_reason)
                send_mqtt_data(sensor_data, current_status, status_reason)
                print_status_message(sensor_data, current_status, status_reason)

            else:
                print("Sensor read failed, skipping this cycle")

            if status_cooldown > 0:
                status_cooldown -= 1

            time.sleep(3)

        except KeyboardInterrupt:
            print("\nProgram interrupted by user")
            break
        except Exception as e:
            print("Main loop error: " + str(e))
            time.sleep(5)

    # Clean up resources
    try:
        fan_pwm.duty(0)
        buzzer_pin.value(0)
        servo_pwm.duty(0)
        if mqtt_client:
            mqtt_client.disconnect()
        print("Device stopped")
    except:
        pass

    print("Program ended")

if __name__ == "__main__":
    main()