# Gemini Project Context: Intelligent Fire Warning System

## Project Overview
This project is an **Intelligent Fire Warning System** designed for dormitory safety. It integrates hardware sensors (ESP32), a backend server (Flask), real-time communication (MQTT/WebSocket), and multiple user interfaces (Web Dashboard, WeChat Mini Program).

The system uses a **Master-Slave architecture** for ESP32 devices, where a master device aggregates data from slave devices via UDP and communicates with the server via MQTT.

## Directory Structure & Key Files

### 1. Backend & Web Interface (`web/`)
*   **Path**: `C:\手动D\行业实践\web`
*   **Framework**: Flask
*   **Key Files**:
    *   `app.py`: Main application entry point. Handles HTTP routes, MQTT subscription, WebSocket events, and database interactions.
    *   `requirements.txt`: Python dependencies.
    *   `templates/`: HTML templates for the dashboard.
    *   `static/`: CSS and JavaScript files.
*   **Database**: SQLite (`instance/fire_alarm.db` - likely location).

### 2. Embedded Firmware (`传感器结合/` & `驱动/`)
*   **Path**: `C:\手动D\行业实践\传感器结合`
*   **Platform**: ESP32 (MicroPython)
*   **Key Files**:
    *   `main.py`: **Master** device firmware. Handles sensors (Flame, MQ-2, DHT11, etc.), OLED, Servo, UDP Server, and MQTT.
    *   `esp32_slave_simple.py`: **Slave** device firmware. Simplified sensor logic and UDP client.
    *   `master_slave_config.py`: Configuration for network and thresholds.
    *   `mqtt_monitor.py` / `test_esp32_mqtt.py`: Tools for testing MQTT connectivity.

### 3. Infrastructure (`mosquitto/`)
*   **Path**: `C:\手动D\行业实践\mosquitto`
*   **Component**: Mosquitto MQTT Broker (Windows).
*   **Usage**: Contains executables and configuration (`mosquitto.conf`) to run the local MQTT broker.

### 4. WeChat Mini Program (`miniprogram-1/`)
*   **Path**: `C:\手动D\行业实践\miniprogram-1`
*   **Component**: Mobile client for the system.

## Development & Usage

### 1. Web Backend
**Setup & Run:**
```bash
cd web
pip install -r requirements.txt
python app.py
```
*   **Access**: `http://localhost:5000`
*   **Function**: Provides a 5-layer architecture view and a detailed dashboard.

### 2. MQTT Broker
**Setup & Run (Windows):**
```bash
cd mosquitto
.\mosquitto.exe -c mosquitto.conf -v
```
*   **Port**: 1883 (TCP), 8083 (WebSocket).
*   **Test Subscription**: `.\mosquitto_sub.exe -t "#" -v`

### 3. ESP32 Development
*   **Tool**: Thonny IDE recommended for MicroPython.
*   **Workflow**: Edit `main.py` or slave scripts, upload to ESP32.
*   **Testing**: Use `python 传感器结合/fire_alarm_simulation_simple.py` to simulate sensor data if hardware is unavailable.

## Architecture Highlights

*   **Communication**:
    *   **Sensors -> ESP32**: GPIO/ADC/I2C.
    *   **Slave -> Master**: UDP (Port 8888).
    *   **Master -> Server**: MQTT (Topics: `esp32/{id}/data/json`, `esp32/{id}/alert/#`).
    *   **Server -> Web Client**: WebSocket (`flask-socketio`).
*   **Logic**:
    *   **3-Level Alarm**: Normal -> Warning -> Alarm.
    *   **Servo Control**: Activates on confirmed Alarm state (to open door/window or spray water).
    *   **Multi-Sensor Fusion**: Uses Flame, Smoke, Temp, Humidity, Light, and Sound data.

## Important Notes
*   **Language**: Codebase contains Chinese comments and documentation.
*   **Timezone**: UTC+8 (Beijing Time).
*   **Network**: Master and Slave ESP32s must be on the same WiFi network for UDP discovery.
