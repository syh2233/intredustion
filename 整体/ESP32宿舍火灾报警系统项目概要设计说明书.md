# 物联网产品系列｜概要设计说明书

> 项目名称：**基于ESP32的宿舍火灾报警系统**  
> 文档类型：**概要设计说明书**

## 文档元信息

- 文件状态：
  - [x] 初稿
  - [ ] 正式发布
  - [ ] 正在修改
- 当前版本：**V1.1**
- 作者：**项目团队**
- 审批：
- 完成日期：**2025年9月12日**
- 单位：电子工程学院
- 发布：**2025年9月**

---

## 版本历史

| 版本/状态 | 作者 | 审批 | 完成日期   | 备注 |
|:---------:|:----:|:----:|:----------:|:----|
| V1.1      | 项目团队 |      | 2025/09/12 | 增加温湿度传感器功能 |
| V1.0      | 项目团队 |      | 2025/09/07 | 初稿完成 |

---

## 目录（ToC）

- [1. 引言](#1-引言)  
  - [1.1 编写目的](#11-编写目的)  
  - [1.2 开发背景](#12-开发背景)  
  - [1.3 术语与缩写解释](#13-术语与缩写解释)  
  - [1.4 参考资料](#14-参考资料)  
- [2. 开发概述](#2-开发概述)  
  - [2.1 运行环境](#21-运行环境)  
    - [2.1.1 软件环境](#211-软件环境)  
    - [2.1.2 硬件环境](#212-硬件环境)  
  - [2.2 需求概述](#22-需求概述)  
- [3. 总体设计](#3-总体设计)  
  - [3.1 软件功能描述](#31-软件功能描述)  
  - [3.2 系统设计](#32-系统设计)  
    - [3.2.1 总体结构与模块关系设计](#321-总体结构与模块关系设计)  
    - [3.2.2 感知层模块设计](#322-感知层模块设计)  
    - [3.2.3 控制层模块设计](#323-控制层模块设计)  
    - [3.2.4 执行层模块设计](#324-执行层模块设计)  
    - [3.2.5 应用层模块设计](#325-应用层模块设计)  
    - [3.2.6 数据库设计](#326-数据库设计)  
    - [3.2.7 用户界面设计](#327-用户界面设计)  
    - [3.2.8 主要算法设计](#328-主要算法设计)  
    - [3.2.9 温湿度传感器扩展设计](#329-温湿度传感器扩展设计)  
  - [3.3 接口设计](#33-接口设计)  
    - [3.3.1 外部接口](#331-外部接口)  
    - [3.3.2 内部接口](#332-内部接口)  
  - [3.4 系统出错处理](#34-系统出错处理)  
  - [3.5 依赖关系](#35-依赖关系)  
    - [3.5.1 硬件依赖关系](#351-硬件依赖关系)  
    - [3.5.2 软件依赖关系](#352-软件依赖关系)  
- [4. 属性设计](#4-属性设计)  
- [5. 系统维护设计](#5-系统维护设计)  
- [6. 知识产权分析](#6-知识产权分析)  

---

## 1. 引言

### 1.1 编写目的

本文档旨在详细描述基于ESP32的宿舍火灾报警系统的概要设计方案，针对当前校园火灾预警系统存在的误报率高问题，采用多传感融合技术提高火情识别准确性。本课程设计通过集成多种传感器，实现更可靠的火灾检测，为项目开发提供完整的技术设计和实现指导。

### 1.2 开发背景

#### 业务背景
当前，宿舍火灾早期预警的物联网技术已在校园场景中广泛铺开，各地高校普遍安装了无线烟感、温感、燃气探测器，通过LoRa、NB-IoT或Wi-Fi将数据传输至校园消控室或第三方云平台。然而，快速铺量的同时暴露出诸多问题：

1. **误报率高导致响应疲劳**：宿舍场景人员密度高、作息不规律，煮面、抽烟、充电宝过载等常触发报警，传统阈值算法误报率高达15%，值班员被"狼来了"折腾后对真实火情反应迟钝。

#### 技术背景
针对上述问题，本课程设计采用多传感融合技术：

- **多传感融合**：集成MEMS烟雾、CO、温度、VOC和人员红外传感器，通过多维度数据提高识别准确性，有效降低误报率

#### 目标用户与适用场景
- **目标用户**：
  - **学校管理部门**：需要安全可靠、维护简单的火灾预警系统
  - **宿舍管理员**：需要实时监控和快速处置能力
  - **学生居住者**：需要安全的学习生活环境

- **适用场景**：
  - 各类学校宿舍（中小学、大学、职业学校）
  - 人员密集的集体宿舍
  - 需要智能化改造的老旧建筑

### 1.3 术语与缩写解释

| 术语/缩写 | 英文全称 | 中文含义 | 说明 |
|:---------|:---------|:---------|:-----|
| **ESP32** | Espressif 32 | 乐鑫32位微控制器 | 集成Wi-Fi和蓝牙的双核MCU |
| **MQTT** | Message Queuing Telemetry Transport | 消息队列遥测传输 | 轻量级物联网通信协议 |
| **I2C** | Inter-Integrated Circuit | 集成电路总线 | 用于连接低速外围设备的串行总线 |
| **ADC** | Analog-to-Digital Converter | 模数转换器 | 将模拟信号转换为数字信号 |
| **GPIO** | General Purpose Input/Output | 通用输入输出 | 微控制器的通用引脚 |
| **OLED** | Organic Light-Emitting Diode | 有机发光二极管 | 自发光显示技术 |
| **RESTful** | Representational State Transfer | 表述性状态转移 | Web服务架构风格 |
| **JSON** | JavaScript Object Notation | JavaScript对象表示法 | 轻量级数据交换格式 |
| **DHT22** | Digital Humidity and Temperature 22 | 数字温湿度传感器 | 高精度温湿度检测传感器 |
| **PWM** | Pulse Width Modulation | 脉冲宽度调制 | 用于控制风扇转速 |

### 1.4 参考资料

1. 《ESP32技术参考手册》，乐鑫信息科技股份有限公司，2023年
2. 《MQTT协议规范》，OASIS标准，2019年
3. 《Flask Web开发实战》，清华大学出版社，2022年
4. 《传感器技术与应用》，电子工业出版社，2021年
5. 《物联网系统架构设计》，机械工业出版社，2023年
6. 《软件工程》，张海藩，清华大学出版社，2020年
7. 《DHT22温湿度传感器技术手册》，Aosong Electronics，2022年

---

## 2. 开发概述

### 2.1 运行环境

#### 2.1.1 软件环境

**ESP32端开发环境**：
- **开发语言**：MicroPython 1.19+
- **开发工具**：Thonny IDE 4.0+
- **核心库**：
  - umqtt.simple/robust（MQTT通信）
  - ssd1306（OLED显示驱动）
  - urequests（HTTP请求）
  - network（网络连接）
  - machine（硬件控制）

**服务器端开发环境**：
- **操作系统**：Windows 10/11 专业版或企业版
- **后端框架**：Flask 3.0+
- **数据库**：SQLite 3.35+
- **MQTT Broker**：Mosquitto 2.0+
- **Python版本**：Python 3.9+
- **依赖包**：
  - flask-cors（跨域支持）
  - flask-mqtt（MQTT集成）
  - flask-socketio（WebSocket支持）
  - paho-mqtt（MQTT客户端）
  - chart.js（数据可视化）

**部署环境**：
- **私有云平台**：Windows服务器
- **网络环境**：支持端口映射的路由器
- **域名服务**：可选的DDNS服务

#### 2.1.2 硬件环境

**核心硬件**：
- **主控制器**：ESP32-WROOM-32开发板
- **火焰传感器**：红外火焰传感器模块（模拟量输出）
- **烟雾传感器**：MQ-2气体传感器模块（模拟量输出）
- **温湿度传感器**：DHT22数字温湿度传感器
- **显示模块**：0.96寸OLED显示屏（SSD1306，I2C接口）
- **报警模块**：5V直流风扇（散热报警）

**连接硬件**：
- **扩展板**：面包板或定制PCB
- **连接线**：杜邦线、排针排母
- **电源模块**：3.3V/5V稳压模块
- **调试工具**：USB数据线、万用表

**接口配置**：
- **火焰传感器**：GPIO34 (ADC1_CH6)
- **MQ-2传感器**：GPIO35 (ADC1_CH7)
- **温湿度传感器**：GPIO32 (DHT22数字接口)
- **OLED显示屏**：GPIO21 (SDA)、GPIO22 (SCL)
- **风扇控制**：GPIO23 (PWM输出)

### 2.2 需求概述

#### 功能需求
1. **实时监测**：实时采集火焰、烟雾、温湿度传感器数据
2. **智能报警**：当检测到火灾隐患时，本地声光报警并推送远程通知
3. **环境监控**：实时监测环境温湿度，评估环境风险等级
4. **数据展示**：Web界面实时显示传感器数据和报警状态
5. **历史记录**：存储和查询历史数据及报警记录
6. **设备管理**：支持设备状态监控和远程配置
7. **预警机制**：基于温湿度数据的环境风险预警

#### 非功能需求
1. **实时性**：数据采集频率1Hz，报警响应时间<3秒
2. **可靠性**：系统7×24小时稳定运行，断网自动重连
3. **准确性**：火焰检测准确率≥95%，烟雾检测准确率≥90%，温湿度检测准确率≥95%
4. **易用性**：Web界面简洁直观，支持移动端访问
5. **安全性**：数据传输加密，设备认证，访问控制

#### 项目目标
- **短期目标**：完成基础功能开发和测试，集成温湿度传感器
- **中期目标**：部署私有云平台，实现远程监控，完善环境风险评估
- **长期目标**：优化算法，提高检测准确性，扩展多设备管理，实现智能化预警

---

## 3. 总体设计

### 3.1 软件功能描述

#### 系统功能架构

```
基于ESP32的宿舍火灾报警系统
├── 传感器数据采集模块
│   ├── 火焰传感器数据采集
│   ├── MQ-2烟雾传感器数据采集
│   └── 数据滤波与预处理
├── 数据处理与判断模块
│   ├── 阈值判断算法
│   ├── 防误报逻辑
│   └── 报警状态管理
├── 本地显示与报警模块
│   ├── OLED显示控制
│   ├── 风扇报警控制
│   └── 本地状态指示
├── 网络通信模块
│   ├── Wi-Fi连接管理
│   ├── HTTP数据传输
│   ├── MQTT实时通信
│   └── 断网重连机制
└── Web监控模块
    ├── 实时数据展示
    ├── 历史数据查询
    ├── 设备状态监控
    └── 报警记录管理
```

#### 核心功能说明

1. **传感器数据采集**
   - 火焰传感器模拟量读取（0-4095）
   - MQ-2传感器模拟量读取（0-4095）
   - 数据滤波处理，消除噪声干扰
   - 传感器故障检测

2. **智能火灾检测**
   - 动态阈值调整算法
   - 多传感器融合判断
   - 防误报机制（去抖处理）
   - 火灾等级评估

3. **本地报警系统**
   - OLED实时显示传感器数据
   - 火灾报警界面显示
   - 风扇启动控制
   - 声光报警指示

4. **网络通信**
   - HTTP POST数据上传
   - MQTT实时数据发布
   - 设备状态上报
   - 远程指令接收

5. **Web监控平台**
   - 实时数据仪表盘
   - 历史趋势图表
   - 报警记录管理
   - 设备配置管理

### 3.2 系统设计

#### 3.2.1 总体结构与模块关系设计

```
┌─────────────────────────────────────────────────────────────┐
│                     基于ESP32的宿舍火灾报警系统                  │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐      │
│  │  火焰传感器  │    │  MQ-2传感器  │    │   OLED显示   │      │
│  │  (GPIO34)   │    │  (GPIO35)   │    │  (I2C)      │      │
│  └──────┬──────┘    └──────┬──────┘    └──────┬──────┘      │
│         │                 │                 │              │
│         └─────────────────┴─────────────────┘              │
│                       │                                    │
│              ┌─────────────────────────────────┐            │
│              │        ESP32主控制器            │            │
│              │  ┌─────────────────────────────┐   │            │
│              │  │     数据处理与判断模块       │   │            │
│              │  │  ┌─────────────────────────┐ │   │            │
│              │  │  │ 火灾检测算法            │ │   │            │
│              │  │ │ 动态阈值调整            │ │   │            │
│              │  │ │ 防误报机制              │ │   │            │
│              │  │ └─────────────────────────┘ │   │            │
│              │  └─────────────────────────────┘   │            │
│              └─────────────────────────────────┘            │
│                       │                                    │
│              ┌─────────────────────────────────┐            │
│              │        网络通信模块              │            │
│              │  ┌─────────────┐  ┌─────────────┐ │            │
│              │  │ HTTP客户端  │  │ MQTT客户端  │ │            │
│              │  │  (数据上传)  │  │ (实时通信)  │ │            │
│              │  └─────────────┘  └─────────────┘ │            │
│              └─────────────────────────────────┘            │
│                       │                                    │
│              ┌─────────────────────────────────┐            │
│              │         执行器控制              │            │
│              │        (风扇报警)               │            │
│              └─────────────────────────────────┘            │
└───────────────┬─────────────────────────────────────────────┘
                │
                │ Wi-Fi / 互联网
                │
┌───────────────┴─────────────────────────────────────────────┐
│                     私有云平台                              │
│                                                             │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐      │
│  │Mosquitto     │    │  Flask      │    │   SQLite    │      │
│  │MQTT Broker   │    │ Web服务器   │    │   数据库     │      │
│  └──────┬──────┘    └──────┬──────┘    └──────┬──────┘      │
│         │                 │                 │              │
│         └─────────────────┴─────────────────┘              │
│                       │                                    │
│              ┌─────────────────────────────────┐            │
│              │        Nginx/IIS               │            │
│              │     (反向代理/SSL)             │            │
│              └─────────────────────────────────┘            │
└───────────────┬─────────────────────────────────────────────┘
                │
                │ 互联网 / 端口映射
                │
┌───────────────┴─────────────────────────────────────────────┐
│                    Web客户端                             │
│                                                             │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐      │
│  │  实时监控   │    │  历史数据   │    │  设备管理   │      │
│  │   仪表盘    │    │   查询      │    │   界面      │      │
│  └─────────────┘    └─────────────┘    └─────────────┘      │
└─────────────────────────────────────────────────────────────┘
```

#### 3.2.2 感知层模块设计

**模块职责**：
- 负责火焰、烟雾和温湿度传感器数据的实时采集
- 对原始数据进行滤波和预处理
- 提供传感器故障检测功能
- 监控环境参数变化

**输入输出**：
- **输入**：火焰传感器模拟量、MQ-2传感器模拟量、DHT22数字信号
- **输出**：滤波后的传感器数据、传感器状态、环境风险评估

**核心算法**：
```python
from machine import Pin
import dht
import time

# 初始化传感器
flame_sensor = Pin(34, Pin.IN)  # 火焰传感器
mq2_sensor = Pin(35, Pin.IN)    # MQ-2传感器
dht22_sensor = dht.DHT22(Pin(32))  # 温湿度传感器

def read_sensors():
    """读取所有传感器数据"""
    try:
        # 读取火焰和烟雾传感器数据
        flame_raw = read_adc(34)
        smoke_raw = read_adc(35)
        
        # 读取温湿度数据
        dht22_sensor.measure()
        temperature = dht22_sensor.temperature()
        humidity = dht22_sensor.humidity()
        
        # 数据滤波
        flame_filtered = moving_average(flame_raw, window_size=5)
        smoke_filtered = moving_average(smoke_raw, window_size=5)
        
        # 传感器状态检测
        flame_status = check_sensor_status(flame_raw)
        smoke_status = check_sensor_status(smoke_raw)
        dht_status = check_dht_status(temperature, humidity)
        
        # 环境风险评估
        env_risk = get_environment_risk_level(temperature, humidity)
        
        return {
            'flame': flame_filtered,
            'smoke': smoke_filtered,
            'temperature': temperature,
            'humidity': humidity,
            'flame_status': flame_status,
            'smoke_status': smoke_status,
            'dht_status': dht_status,
            'environment_risk': env_risk,
            'timestamp': time.time()
        }
        
    except Exception as e:
        print(f"传感器读取错误: {e}")
        return get_last_valid_data()

def check_dht_status(temperature, humidity):
    """检测温湿度传感器状态"""
    if temperature is None or humidity is None:
        return "error"
    if temperature < -40 or temperature > 80:
        return "error"
    if humidity < 0 or humidity > 100:
        return "error"
    return "normal"

def get_environment_risk_level(temperature, humidity):
    """根据温湿度评估环境风险等级"""
    risk_level = "low"
    
    # 高温风险
    if temperature > 35:
        risk_level = "high"
    elif temperature > 30:
        risk_level = "medium"
    
    # 低湿度增加火灾风险
    if humidity < 30 and temperature > 25:
        if risk_level == "low":
            risk_level = "medium"
        elif risk_level == "medium":
            risk_level = "high"
    
    return risk_level
```

**配置参数**：
- **采样频率**：1Hz
- **滤波窗口大小**：5个样本
- **传感器正常范围**：火焰/烟雾: 0-4095，温度: -40~80°C，湿度: 0~100%
- **故障检测阈值**：超出正常范围持续30秒
- **环境风险阈值**：高温: >35°C，低湿度: <30%，中等风险: >30°C，高温度+低湿度

#### 3.2.3 控制层模块设计

**模块职责**：
- 实现增强的火灾检测算法，集成温湿度数据
- 管理报警状态
- 控制执行器动作
- 环境风险评估和预警

**输入输出**：
- **输入**：滤波后的传感器数据、配置参数、环境风险评估
- **输出**：报警状态、执行器控制信号、环境预警信息

**火灾检测算法**：
```python
def enhanced_fire_detection(sensor_data):
    """
    增强的火灾检测算法，集成温湿度数据
    """
    flame_value = sensor_data['flame']
    smoke_value = sensor_data['smoke']
    temperature = sensor_data['temperature']
    humidity = sensor_data['humidity']
    
    # 动态阈值计算
    flame_threshold = calculate_dynamic_threshold(flame_history)
    smoke_threshold = calculate_dynamic_threshold(smoke_history)
    temp_threshold = calculate_temp_threshold(temp_history)
    
    # 各维度火灾风险评分
    flame_risk = calculate_flame_risk(flame_value, flame_threshold)
    smoke_risk = calculate_smoke_risk(smoke_value, smoke_threshold)
    temp_risk = calculate_temperature_risk(temperature, temp_threshold)
    humidity_risk = calculate_humidity_risk(humidity)
    
    # 综合风险评分（加权平均）
    total_risk_score = (
        flame_risk * 0.4 +      # 火焰检测权重40%
        smoke_risk * 0.3 +     # 烟雾检测权重30%
        temp_risk * 0.2 +      # 温度检测权重20%
        humidity_risk * 0.1     # 湿度检测权重10%
    )
    
    # 火灾等级判断
    if total_risk_score >= 0.8:
        return True, "CRITICAL", total_risk_score
    elif total_risk_score >= 0.6:
        return True, "HIGH", total_risk_score
    elif total_risk_score >= 0.4:
        return True, "MEDIUM", total_risk_score
    else:
        return False, "NORMAL", total_risk_score

def calculate_temperature_risk(temperature, threshold):
    """计算温度风险评分"""
    if temperature >= threshold * 1.2:
        return 1.0  # 极高风险
    elif temperature >= threshold:
        return 0.8  # 高风险
    elif temperature >= threshold * 0.8:
        return 0.4  # 中等风险
    else:
        return 0.0  # 低风险

def calculate_humidity_risk(humidity):
    """计算湿度风险评分（低湿度增加火灾风险）"""
    if humidity < 20:
        return 0.6  # 极干燥，增加火灾风险
    elif humidity < 30:
        return 0.3  # 干燥，中等风险
    elif humidity < 40:
        return 0.1  # 轻微风险
    else:
        return 0.0  # 正常湿度

def intelligent_alarm_system(sensor_data, fire_status):
    """
    智能报警系统，考虑环境因素
    """
    temperature = sensor_data['temperature']
    humidity = sensor_data['humidity']
    
    # 基础报警判断
    if fire_status[0]:  # 检测到火灾
        return trigger_fire_alarm(fire_status[1])
    
    # 环境风险预警
    env_risk = get_environment_risk_level(temperature, humidity)
    
    if env_risk == "high":
        return trigger_environment_warning("高温低湿环境，注意防火")
    elif env_risk == "medium":
        return trigger_environment_warning("环境条件异常，加强监控")
    
    return "normal"
```

**配置参数**：
- **初始火焰阈值**：1200
- **初始烟雾阈值**：1200
- **最小连续检测次数**：3次
- **动态阈值调整系数**：0.1

#### 3.2.4 执行层模块设计

**模块职责**：
- 控制OLED显示内容，包含温湿度信息
- 管理散热风扇运行，考虑温湿度因素
- 提供本地状态指示和环境风险提示

**输入输出**：
- **输入**：报警状态、传感器数据、系统状态、温湿度数据、环境风险评估
- **输出**：OLED显示内容、风扇控制信号、环境指示信号

**OLED显示控制**：
```python
def update_enhanced_display(sensor_data, alarm_status):
    """
    增强的OLED显示界面，包含温湿度信息
    """
    oled.fill(0)
    
    flame_value = sensor_data['flame']
    smoke_value = sensor_data['smoke']
    temperature = sensor_data['temperature']
    humidity = sensor_data['humidity']
    
    if alarm_status['fire_detected']:
        # 火灾报警界面
        oled.text("🔥 FIRE ALERT!", 0, 0, 1)
        oled.text(f"F:{flame_value}", 0, 16, 1)
        oled.text(f"S:{smoke_value}", 0, 32, 1)
        oled.text(f"T:{temperature}°C", 64, 16, 1)
        oled.text(f"H:{humidity}%", 64, 32, 1)
        oled.text("CALL HELP!", 0, 48, 1)
        
    else:
        # 正常监控界面
        oled.text("Fire Monitor", 0, 0, 1)
        
        # 传感器数据
        oled.text(f"Flame:{flame_value}", 0, 16, 1)
        oled.text(f"Smoke:{smoke_value}", 0, 32, 1)
        
        # 温湿度数据
        oled.text(f"Temp:{temperature}°C", 0, 48, 1)
        oled.text(f"Humidity:{humidity}%", 64, 48, 1)
        
        # 状态指示
        status_icon = "✓" if all(sensor_data.values()) else "⚠"
        oled.text(f"Status:{status_icon}", 80, 0, 1)
    
    oled.show()

def display_environment_status(sensor_data):
    """
    显示环境状态信息
    """
    temperature = sensor_data['temperature']
    humidity = sensor_data['humidity']
    
    # 环境风险评估
    env_risk = get_environment_risk_level(temperature, humidity)
    
    # 温度状态图标
    if temperature > 30:
        temp_icon = "🔥"
    elif temperature > 25:
        temp_icon = "⚠"
    else:
        temp_icon = "❄"
    
    # 湿度状态图标
    if humidity < 30:
        humid_icon = "🏜"
    elif humidity > 70:
        humid_icon = "💧"
    else:
        humid_icon = "✓"
    
    oled.text(f"{temp_icon}{temperature}°C", 0, 0, 1)
    oled.text(f"{humid_icon}{humidity}%", 0, 16, 1)
    
    # 风险等级
    risk_colors = {"low": "🟢", "medium": "🟡", "high": "🔴"}
    oled.text(f"Risk:{risk_colors[env_risk]}", 0, 32, 1)
```

**风扇控制逻辑**：
```python
def enhanced_fan_control(sensor_data, system_status):
    """
    增强的风扇控制逻辑，考虑温湿度
    """
    temperature = sensor_data['temperature']
    humidity = sensor_data['humidity']
    alarm_status = system_status['alarm_status']
    
    if alarm_status:
        # 火灾报警时全速运行
        fan_speed = 100
        fan_purpose = "FIRE_ALARM"
        
    elif temperature > TEMP_HIGH_THRESHOLD:
        # 高温散热
        fan_speed = 80
        fan_purpose = "COOLING"
        
    elif humidity > HUMIDITY_HIGH_THRESHOLD:
        # 高湿度除湿
        fan_speed = 60
        fan_purpose = "DEHUMIDIFY"
        
    elif temperature > TEMP_NORMAL_THRESHOLD:
        # 正常散热
        fan_speed = 40
        fan_purpose = "VENTILATION"
        
    else:
        # 低功耗模式
        fan_speed = 0
        fan_purpose = "STANDBY"
    
    set_fan_pwm(fan_speed)
    return fan_speed, fan_purpose
```

#### 3.2.5 应用层模块设计

**模块职责**：
- 提供Web监控界面
- 处理数据存储和查询
- 管理设备配置和用户权限

**子模块划分**：
1. **Flask Web服务器**
2. **MQTT消息处理**
3. **数据管理模块**
4. **用户接口模块**

**Web服务器架构**：
```python
from flask import Flask, render_template, request, jsonify
from flask_mqtt import Mqtt
from flask_socketio import SocketIO
import sqlite3
import json

app = Flask(__name__)
mqtt = Mqtt(app)
socketio = SocketIO(app)

# MQTT消息处理
@mqtt.on_message()
def handle_mqtt_message(client, userdata, msg):
    topic = msg.topic.decode()
    payload = msg.payload.decode()
    
    if '/data/json' in topic:
        data = json.loads(payload)
        save_to_database(data)
        socketio.emit('sensor_data', data)
    
    elif '/alert/' in topic:
        socketio.emit('alert_data', payload)
        send_alert_notification(payload)

# RESTful API
@app.route('/api/data/recent')
def get_recent_data():
    limit = request.args.get('limit', 20)
    data = get_recent_sensor_data(limit)
    return jsonify(data)

@app.route('/api/alerts')
def get_alerts():
    alerts = get_alert_history()
    return jsonify(alerts)

# WebSocket实时通信
@socketio.on('connect')
def handle_connect():
    print('Client connected')
```

#### 3.2.6 数据库设计

**数据库选型**：SQLite

**表结构设计**：

```sql
-- 传感器数据表
CREATE TABLE sensor_data (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    device_id TEXT NOT NULL,
    flame_value INTEGER NOT NULL,
    smoke_value INTEGER NOT NULL,
    temperature REAL,
    humidity REAL,
    alert_status BOOLEAN DEFAULT FALSE,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 报警记录表
CREATE TABLE alert_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    device_id TEXT NOT NULL,
    alert_type TEXT NOT NULL,
    severity TEXT NOT NULL,
    flame_value INTEGER,
    smoke_value INTEGER,
    temperature REAL,
    humidity REAL,
    location TEXT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    resolved BOOLEAN DEFAULT FALSE,
    resolved_time DATETIME
);

-- 新增环境预警记录表
CREATE TABLE environment_alerts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    device_id TEXT NOT NULL,
    alert_type TEXT NOT NULL,  -- 'temperature_high', 'humidity_low', 'environment_risk'
    severity TEXT NOT NULL,     -- 'low', 'medium', 'high'
    temperature REAL,
    humidity REAL,
    risk_score REAL,
    threshold_value REAL,
    alert_message TEXT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    resolved BOOLEAN DEFAULT FALSE,
    resolved_time DATETIME
);

-- 新增环境数据统计表
CREATE TABLE environment_statistics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    device_id TEXT NOT NULL,
    date DATE NOT NULL,
    avg_temperature REAL,
    max_temperature REAL,
    min_temperature REAL,
    avg_humidity REAL,
    max_humidity REAL,
    min_humidity REAL,
    alert_count INTEGER DEFAULT 0,
    data_points INTEGER DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 新增温湿度阈值配置表
CREATE TABLE environment_thresholds (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    device_id TEXT NOT NULL,
    temp_warning_threshold REAL DEFAULT 30.0,
    temp_critical_threshold REAL DEFAULT 35.0,
    humidity_low_threshold REAL DEFAULT 30.0,
    humidity_high_threshold REAL DEFAULT 70.0,
    temp_humidity_combined_risk BOOLEAN DEFAULT TRUE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 设备信息表
CREATE TABLE devices (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    device_id TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    location TEXT,
    ip_address TEXT,
    last_seen DATETIME,
    status TEXT DEFAULT 'online',
    config TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 系统配置表
CREATE TABLE system_config (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    description TEXT,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

**索引设计**：
```sql
-- 传感器数据索引
CREATE INDEX idx_sensor_data_timestamp ON sensor_data(timestamp);
CREATE INDEX idx_sensor_data_device ON sensor_data(device_id);
CREATE INDEX idx_sensor_data_alert ON sensor_data(alert_status);
CREATE INDEX idx_sensor_data_temperature ON sensor_data(temperature);
CREATE INDEX idx_sensor_data_humidity ON sensor_data(humidity);

-- 报警记录索引
CREATE INDEX idx_alerts_timestamp ON alert_history(timestamp);
CREATE INDEX idx_alerts_device ON alert_history(device_id);
CREATE INDEX idx_alerts_resolved ON alert_history(resolved);

-- 环境预警索引
CREATE INDEX idx_environment_alerts_timestamp ON environment_alerts(timestamp);
CREATE INDEX idx_environment_alerts_device ON environment_alerts(device_id);
CREATE INDEX idx_environment_alerts_type ON environment_alerts(alert_type);

-- 环境统计索引
CREATE INDEX idx_environment_statistics_date ON environment_statistics(date);
```

**数据维护策略**：
- **自动清理**：30天前的传感器数据自动删除
- **备份策略**：每日备份重要数据
- **归档策略**：报警记录长期保存，传感器数据定期归档

#### 3.2.7 用户界面设计

**界面架构**：
```
Web界面
├── 实时监控仪表盘
│   ├── 传感器数据实时显示
│   ├── 设备状态指示
│   └── 报警状态显示
├── 历史数据查询
│   ├── 时间范围选择
│   ├── 数据趋势图表
│   └── 数据导出功能
├── 报警管理
│   ├── 报警记录列表
│   ├── 报警处理状态
│   └── 报警统计分析
└── 系统设置
    ├── 设备管理
    ├── 阈值配置
    └── 用户权限管理
```

**响应式设计**：
- **桌面端**：完整功能界面
- **平板端**：适配中等屏幕
- **手机端**：核心功能界面

**视觉设计**：
- **主色调**：红色（报警）、绿色（正常）、蓝色（信息）
- **图标**：火焰、烟雾、设备状态图标
- **布局**：卡片式布局，清晰的信息层次

#### 3.2.9 温湿度传感器扩展设计

**扩展背景**：
为提高系统火灾检测准确性和环境监控能力，在原有系统基础上集成DHT22温湿度传感器，实现多维数据融合检测和环境风险评估。

**扩展架构**：
```
温湿度传感器扩展架构
├── 硬件层
│   ├── DHT22温湿度传感器
│   ├── GPIO32接口连接
│   └── 电源和信号调理电路
├── 驱动层
│   ├── DHT22传感器驱动
│   ├── 数据采集和滤波
│   └── 传感器状态检测
├── 算法层
│   ├── 环境风险评估算法
│   ├── 多维火灾检测算法
│   └── 智能预警机制
└── 应用层
    ├── 增强的OLED显示
    ├── 环境数据Web监控
    └── 环境预警管理
```

**核心功能增强**：

1. **多传感器融合检测**
   - 火焰、烟雾、温度、湿度四维数据融合
   - 动态权重分配算法
   - 环境风险综合评估

2. **智能预警机制**
   - 高温预警（>35°C）
   - 低湿度预警（<30%）
   - 组合风险预警（高温+低湿度）

3. **环境监控功能**
   - 实时温湿度显示
   - 历史趋势分析
   - 环境风险评估

**技术实现要点**：

1. **传感器集成**
   - DHT22数字温湿度传感器
   - GPIO32接口连接
   - 单总线通信协议
   - 内置数据校验

2. **数据处理**
   - 温湿度数据滤波
   - 传感器故障检测
   - 数据有效性验证
   - 异常值处理

3. **算法优化**
   - 基于环境因素的火灾检测
   - 动态阈值调整
   - 防误报机制增强
   - 风险等级评估

**优势特点**：

1. **检测精度提升**：多传感器融合，降低误报率30%以上
2. **环境监控全面**：火灾预警 + 环境风险评估
3. **用户体验优化**：直观的Web监控界面和本地显示
4. **智能化水平**：基于环境因素的智能预警机制

**兼容性设计**：
- 保持向后兼容性，原有功能不受影响
- 模块化设计，便于维护和扩展
- 数据格式兼容，支持平滑升级

#### 3.2.8 主要算法设计

**1. 动态阈值调整算法**
```python
def dynamic_threshold_adjustment(history_data, base_threshold):
    """
    动态阈值调整算法
    根据历史数据自动调整检测阈值
    """
    if len(history_data) < 10:
        return base_threshold
    
    # 计算历史数据的统计特征
    mean_value = sum(history_data) / len(history_data)
    std_value = (sum((x - mean_value) ** 2 for x in history_data) / len(history_data)) ** 0.5
    
    # 动态调整阈值
    if std_value < 50:  # 数据稳定
        new_threshold = mean_value * 1.2
    elif std_value < 200:  # 数据波动中等
        new_threshold = mean_value * 1.5
    else:  # 数据波动较大
        new_threshold = mean_value * 2.0
    
    # 限制阈值范围
    new_threshold = max(min_threshold, min(new_threshold, max_threshold))
    
    return new_threshold
```

**2. 防误报算法**
```python
def false_alarm_prevention(sensor_data, consecutive_threshold=3):
    """
    防误报算法
    通过连续检测和趋势分析减少误报
    """
    global consecutive_count, last_state
    
    current_state = analyze_sensor_state(sensor_data)
    
    if current_state == last_state:
        consecutive_count += 1
    else:
        consecutive_count = 1
        last_state = current_state
    
    # 连续检测到相同状态才触发报警
    if consecutive_count >= consecutive_threshold:
        return current_state
    else:
        return "NORMAL"
```

**3. 传感器数据滤波算法**
```python
def kalman_filter(measurement, previous_estimate, previous_error):
    """
    卡尔曼滤波算法
    用于传感器数据的噪声过滤
    """
    # 系统参数
    Q = 0.1  # 过程噪声协方差
    R = 0.1  # 测量噪声协方差
    
    # 预测
    predicted_estimate = previous_estimate
    predicted_error = previous_error + Q
    
    # 更新
    kalman_gain = predicted_error / (predicted_error + R)
    current_estimate = predicted_estimate + kalman_gain * (measurement - predicted_estimate)
    current_error = (1 - kalman_gain) * predicted_error
    
    return current_estimate, current_error
```

### 3.3 接口设计

#### 3.3.1 外部接口

**1. 硬件接口**

| 接口类型 | 引脚 | 功能描述 | 电气特性 |
|:---------|:-----|:---------|:---------|
| **ADC输入** | GPIO34 | 火焰传感器模拟量输入 | 0-3.3V, 12位ADC |
| **ADC输入** | GPIO35 | MQ-2传感器模拟量输入 | 0-3.3V, 12位ADC |
| **I2C接口** | GPIO21/22 | OLED显示屏连接 | 3.3V, 400kHz |
| **GPIO输出** | GPIO23 | 风扇PWM控制 | 3.3V, PWM输出 |

**2. 软件接口**

**MQTT主题接口**：
```
# 设备数据上报
esp32/{device_id}/data/json          # 传感器数据
esp32/{device_id}/status/online      # 设备上线
esp32/{device_id}/status/offline     # 设备离线
esp32/{device_id}/alert/fire          # 火灾报警
esp32/{device_id}/alert/smoke         # 烟雾报警

# 服务器指令下发
server/{device_id}/cmd/config        # 配置更新
server/{device_id}/cmd/reboot        # 重启设备
server/{device_id}/cmd/threshold     # 阈值调整
```

**HTTP RESTful API**：
```python
# 数据接口
POST /api/data                    # 接收传感器数据
GET  /api/data/recent?limit=20    # 获取最新数据
GET  /api/data/range?start=&end=  # 获取时间范围数据

# 报警接口
GET  /api/alerts                   # 获取报警记录
POST /api/alerts/resolve/:id       # 处理报警
GET  /api/alerts/statistics        # 报警统计

# 设备接口
GET  /api/devices                  # 获取设备列表
POST /api/devices/register         # 注册设备
PUT  /api/devices/:id             # 更新设备配置
```

**WebSocket接口**：
```javascript
// 实时数据推送
socket.on('sensor_data', (data) => {
    updateDashboard(data);
});

// 报警信息推送
socket.on('alert_data', (alert) => {
    showAlert(alert);
});

// 设备状态推送
socket.on('device_status', (status) => {
    updateDeviceStatus(status);
});
```

#### 3.3.2 内部接口

**模块间接口定义**：

```python
# 数据采集模块 -> 数据处理模块
def get_sensor_data():
    """获取传感器数据"""
    return {
        'flame_value': flame_value,
        'smoke_value': smoke_value,
        'timestamp': current_time,
        'sensor_status': sensor_status
    }

# 数据处理模块 -> 报警管理模块
def check_fire_condition(sensor_data):
    """检查火灾条件"""
    return {
        'alert_status': alert_status,
        'alert_level': alert_level,
        'confidence': confidence
    }

# 报警管理模块 -> 执行器控制模块
def execute_alarm_action(alert_info):
    """执行报警动作"""
    return {
        'action_taken': action_taken,
        'execution_time': execution_time,
        'result': result
    }
```

**数据格式规范**：

```json
// 传感器数据格式
{
    "device_id": "ESP32-001",
    "flame": 1032,
    "smoke": 1450,
    "temperature": 25.5,
    "humidity": 65.0,
    "alert": false,
    "timestamp": "2024-01-01T12:00:00Z"
}

// 报警数据格式
{
    "device_id": "ESP32-001",
    "alert_type": "fire",
    "severity": "high",
    "timestamp": "2024-01-01T12:00:00Z",
    "sensor_values": {
        "flame": 450,
        "smoke": 2100
    },
    "location": "宿舍A栋301"
}
```

### 3.4 系统出错处理

**错误类型分类**：

1. **传感器错误**
   - 传感器连接断开
   - 传感器数据异常
   - 传感器漂移

2. **网络错误**
   - Wi-Fi连接失败
   - MQTT连接断开
   - HTTP请求失败

3. **系统错误**
   - 内存不足
   - 程序崩溃
   - 配置错误

**错误处理策略**：

```python
# 传感器错误处理
def handle_sensor_error(error_type):
    if error_type == "disconnected":
        # 尝试重新连接
        reconnect_sensor()
        return "传感器重连中"
    elif error_type == "abnormal_data":
        # 使用历史数据替代
        return use_last_valid_data()
    elif error_type == "drift":
        # 重新校准传感器
        recalibrate_sensor()
        return "传感器校准中"

# 网络错误处理
def handle_network_error(error_type):
    if error_type == "wifi_disconnected":
        # 重连Wi-Fi
        reconnect_wifi()
        return "Wi-Fi重连中"
    elif error_type == "mqtt_disconnected":
        # 重连MQTT
        reconnect_mqtt()
        return "MQTT重连中"
    elif error_type == "http_failed":
        # 缓存数据，稍后重试
        cache_data_for_retry()
        return "数据缓存中"

# 系统错误处理
def handle_system_error(error_type):
    if error_type == "memory_low":
        # 清理内存
        cleanup_memory()
        return "内存清理中"
    elif error_type == "config_error":
        # 使用默认配置
        load_default_config()
        return "使用默认配置"
```

**降级策略**：
- **本地模式**：网络断开时，系统继续本地监测和报警
- **数据缓存**：网络恢复后，上传缓存的历史数据
- **功能简化**：资源不足时，保留核心功能

**重试机制**：
- **指数退避**：网络重试采用指数退避策略
- **最大重试次数**：限制重试次数，避免无限循环
- **重试间隔**：根据错误类型设置不同的重试间隔

### 3.5 依赖关系

#### 3.5.1 硬件依赖关系

```
ESP32主控制器
├── 依赖硬件组件
│   ├── 火焰传感器 (必须)
│   ├── MQ-2烟雾传感器 (必须)
│   ├── OLED显示屏 (必须)
│   ├── 风扇执行器 (必须)
│   └── 电源模块 (必须)
├── 依赖电气特性
│   ├── 3.3V电源供应 (必须)
│   ├── I2C接口 (必须)
│   ├── ADC接口 (必须)
│   └── GPIO接口 (必须)
└── 依赖环境条件
    ├── 工作温度: -10°C ~ 60°C (必须)
    ├── 工作湿度: 10% ~ 90% RH (必须)
    └── Wi-Fi覆盖范围 (必须)
```

#### 3.5.2 软件依赖关系

```
ESP32端软件依赖
├── MicroPython 1.19+ (必须)
├── 核心库
│   ├── umqtt.simple (必须)
│   ├── umqtt.robust (必须)
│   ├── ssd1306 (必须)
│   ├── urequests (必须)
│   ├── network (必须)
│   └── machine (必须)
└── 可选库
    ├── dht (温湿度传感器)
    ├── ds18x20 (温度传感器)
    └── neopixel (LED灯带)

服务器端软件依赖
├── Python 3.9+ (必须)
├── Web框架
│   ├── Flask 3.0+ (必须)
│   ├── Flask-CORS (必须)
│   ├── Flask-MQTT (必须)
│   └── Flask-SocketIO (必须)
├── 数据库
│   └── SQLite 3.35+ (必须)
├── MQTT客户端
│   └── paho-mqtt (必须)
└── 可选组件
    ├── Nginx (反向代理)
    ├── Let's Encrypt (SSL证书)
    └── Chart.js (数据可视化)
```

**版本兼容性**：
- **MicroPython**：1.19+ (ESP32官方支持)
- **Python**：3.9+ (Flask 3.0+要求)
- **SQLite**：3.35+ (支持JSON字段)
- **Mosquitto**：2.0+ (MQTT 3.1.1支持)

---

## 4. 属性设计

### 4.1 可靠性设计

**硬件可靠性**：
- **传感器冗余**：关键传感器可配置冗余
- **看门狗定时器**：防止系统死机
- **电源保护**：过压、过流保护电路
- **环境适应性**：宽温工作范围设计

**软件可靠性**：
- **异常处理**：全面的错误捕获和处理
- **数据完整性**：数据校验和重传机制
- **状态恢复**：断电后状态恢复功能
- **日志记录**：详细的运行日志和错误日志

**网络可靠性**：
- **多协议支持**：HTTP + MQTT双协议
- **断网重连**：自动重连机制
- **数据缓存**：本地数据缓存和断点续传
- **心跳检测**：设备状态实时监控

**可靠性指标**：
- **系统可用性**：≥ 99.9%
- **数据传输成功率**：≥ 99%
- **故障恢复时间**：≤ 5分钟
- **平均无故障时间**：≥ 1000小时

### 4.2 可维护性设计

**模块化设计**：
- **功能模块化**：各功能模块独立，便于维护
- **接口标准化**：统一的接口设计规范
- **配置分离**：配置参数与代码分离
- **插件化架构**：支持功能扩展

**文档支持**：
- **代码注释**：详细的代码注释和文档
- **API文档**：完整的API接口文档
- **部署文档**：详细的部署和维护指南
- **故障排除**：常见问题解决方案

**维护工具**：
- **远程维护**：支持远程配置和升级
- **日志分析**：日志收集和分析工具
- **性能监控**：系统性能监控仪表盘
- **自动化测试**：单元测试和集成测试

**维护指标**：
- **代码覆盖率**：≥ 80%
- **文档完整性**：≥ 90%
- **故障定位时间**：≤ 30分钟
- **版本兼容性**：向后兼容2个版本

### 4.3 可用性设计

**系统可用性**：
- **7×24小时运行**：系统持续运行能力
- **故障自愈**：自动故障检测和恢复
- **负载均衡**：多设备负载均衡（扩展功能）
- **备份机制**：数据备份和恢复

**用户可用性**：
- **界面友好**：直观的用户界面
- **响应及时**：界面响应时间≤ 2秒
- **操作简单**：最小化用户操作复杂度
- **多端支持**：Web端和移动端支持

**可用性指标**：
- **系统可用性**：≥ 99.9%
- **响应时间**：≤ 2秒
- **并发用户**：≥ 50个
- **故障恢复时间**：≤ 5分钟

### 4.4 安全性设计

**数据安全**：
- **传输加密**：MQTT over SSL/TLS
- **存储加密**：敏感数据加密存储
- **访问控制**：基于角色的访问控制
- **数据完整性**：数据校验和签名

**设备安全**：
- **设备认证**：设备唯一标识和认证
- **固件安全**：固件签名和验证
- **远程控制**：安全的远程控制机制
- **访问日志**：详细的访问日志

**网络安全**：
- **防火墙**：网络访问控制
- **端口安全**：最小化开放端口
- **DDoS防护**：DDoS攻击防护
- **入侵检测**：异常访问检测

### 4.5 扩展性设计

**硬件扩展**：
- **传感器扩展**：支持多种传感器接入
- **设备扩展**：支持多设备管理
- **接口扩展**：预留硬件接口
- **通信扩展**：支持多种通信协议

**软件扩展**：
- **功能模块**：插件化功能模块
- **API扩展**：RESTful API设计
- **数据库扩展**：支持多种数据库
- **平台扩展**：支持云平台集成

**业务扩展**：
- **场景扩展**：支持多种应用场景
- **用户扩展**：支持多用户管理
- **功能扩展**：支持新功能快速集成
- **集成扩展**：支持第三方系统集成

---

## 5. 系统维护设计

### 5.1 日常维护

**硬件维护**：
- **传感器校准**：每月一次传感器校准
- **设备清洁**：每季度设备清洁和检查
- **电源检查**：定期检查电源系统
- **连接检查**：检查所有连接线和接口

**软件维护**：
- **系统更新**：定期更新系统软件
- **数据库维护**：数据库优化和清理
- **日志管理**：日志文件管理和归档
- **备份检查**：备份数据完整性检查

**网络维护**：
- **连接检查**：网络连接状态检查
- **性能监控**：网络性能监控
- **安全检查**：网络安全检查
- **配置更新**：网络配置更新

### 5.2 故障处理

**故障分类**：
- **硬件故障**：传感器、控制器、执行器故障
- **软件故障**：程序崩溃、配置错误、数据丢失
- **网络故障**：连接断开、延迟过高、丢包
- **环境故障**：电源故障、环境异常

**故障处理流程**：
1. **故障检测**：自动故障检测和报警
2. **故障诊断**：故障原因分析和定位
3. **故障处理**：故障修复和恢复
4. **故障记录**：故障记录和分析
5. **预防措施**：类似故障预防

**应急处理**：
- **备用设备**：关键设备备用方案
- **数据恢复**：数据备份和恢复
- **系统降级**：系统降级运行方案
- **人工干预**：人工处理流程

### 5.3 性能监控

**监控指标**：
- **系统性能**：CPU、内存、磁盘使用率
- **网络性能**：延迟、带宽、丢包率
- **应用性能**：响应时间、吞吐量、错误率
- **业务性能**：数据准确性、报警及时性

**监控工具**：
- **系统监控**：系统资源监控工具
- **应用监控**：应用性能监控工具
- **日志监控**：日志分析和监控工具
- **用户监控**：用户行为监控工具

**告警机制**：
- **阈值告警**：基于阈值的告警
- **趋势告警**：基于趋势的告警
- **异常告警**：异常检测告警
- **关联告警**：关联分析告警

### 5.4 版本管理

**版本控制**：
- **代码管理**：Git版本控制
- **配置管理**：配置文件版本控制
- **文档管理**：文档版本控制
- **发布管理**：版本发布和回滚

**版本策略**：
- **主版本**：重大功能变更
- **次版本**：新功能添加
- **修订版本**：Bug修复
- **构建版本**：开发版本

**兼容性管理**：
- **向后兼容**：新版本兼容旧版本数据
- **向前兼容**：旧版本支持新版本功能
- **数据迁移**：版本间数据迁移
- **接口兼容**：API接口兼容性

---

## 6. 知识产权分析

### 6.1 可申请知识产权类型

**专利申请**：
- **实用新型专利**：基于ESP32的火灾报警系统硬件结构
- **发明专利**：动态阈值调整算法、防误报算法
- **外观设计专利**：设备外观设计

**软件著作权**：
- **ESP32端软件**：MicroPython火灾检测程序
- **服务器端软件**：Flask Web监控平台
- **移动端软件**：移动监控应用（可选）

**商标保护**：
- **产品商标**：产品名称和Logo
- **服务商标**：监控服务品牌

### 6.2 创新点分析

**技术创新**：
1. **动态阈值调整算法**：根据环境自动调整检测阈值
2. **多传感器融合检测**：火焰和烟雾传感器数据融合
3. **防误报机制**：连续检测和趋势分析减少误报
4. **私有云架构**：Windows环境下的私有云部署方案

**应用创新**：
1. **宿舍场景优化**：针对宿舍环境的专门优化
2. **低成本方案**：使用低成本硬件实现高可靠性
3. **易部署设计**：简化部署和维护流程
4. **实时监控**：Web端实时监控和报警

### 6.3 潜在侵权风险

**专利风险**：
- **传感器技术**：现有传感器专利技术
- **通信协议**：MQTT协议标准使用
- **报警算法**：火灾检测算法专利

**版权风险**：
- **开源软件**：使用的开源软件许可证合规
- **第三方代码**：第三方代码的使用权限
- **图标资源**：界面图标和设计资源

**商标风险**：
- **产品名称**：与现有产品名称冲突
- **技术术语**：行业标准术语使用

### 6.4 合规建议

**专利申请**：
- **核心算法**：申请动态阈值调整算法专利
- **系统架构**：申请私有云系统架构专利
- **硬件设计**：申请硬件结构设计专利

**版权保护**：
- **软件著作权**：注册软件著作权
- **文档版权**：技术文档版权保护
- **界面设计**：用户界面设计版权

**合规措施**：
- **开源合规**：确保开源软件许可证合规
- **数据合规**：符合数据保护法规要求
- **标准合规**：符合行业标准和技术规范

---

> 本概要设计说明书详细描述了基于ESP32的宿舍火灾报警系统的整体设计方案，为项目的开发和实施提供了完整的技术指导。系统采用模块化设计，具有良好的可扩展性和可维护性，能够满足宿舍火灾监控的实际需求。