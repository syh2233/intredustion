#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI辅助报警决策系统 - ESP32火灾报警系统智能中间层
=================================================

功能:
1. 多维度数据分析降低误报率
2. 历史数据模式识别
3. 环境因素综合考虑
4. 时间序列分析
5. 多传感器融合验证
6. AI智能决策干预
"""

import sqlite3
import json
import numpy as np
import time
from datetime import datetime, timedelta
from collections import deque
import logging
import os
from ai import new

logger = logging.getLogger(__name__)


def _default_db_path():
    data_dir = os.environ.get('FIRE_ALARM_DATA_DIR')
    if data_dir:
        return os.path.join(data_dir, 'fire_alarm.db')
    return os.path.join('instance', 'fire_alarm.db')


class AIAlarmDecisionEngine:
    """AI辅助报警决策引擎"""

    def __init__(self, db_path=None, window_size=30):
        self.db_path = db_path or _default_db_path()
        self.window_size = window_size  # 数据窗口大小（秒）
        self.data_history = deque(maxlen=100)  # 最近100条数据
        self.alarm_history = deque(maxlen=50)   # 最近50次报警决策
        self.device_profiles = {}  # 设备环境画像
        self.patterns = {
            'fire_patterns': [],
            'false_alarm_patterns': []
        }

        # AI决策权重配置
        self.decision_weights = {
            'hardware_threshold': 0.4,      # 硬件阈值权重
            'pattern_matching': 0.25,       # 模式匹配权重
            'historical_analysis': 0.15,    # 历史分析权重
            'environmental_context': 0.10,  # 环境上下文权重
            'ai_prediction': 0.10          # AI预测权重
        }

        # 传感器健康度阈值
        self.sensor_health_threshold = 0.7

    def add_sensor_data(self, device_id, sensor_data):
        """添加传感器数据到历史缓存"""
        timestamp = time.time()
        data_entry = {
            'device_id': device_id,
            'timestamp': timestamp,
            'data': sensor_data.copy(),
            'processed': False
        }
        self.data_history.append(data_entry)

        # 更新设备环境画像
        self._update_device_profile(device_id, sensor_data)

    def _update_device_profile(self, device_id, sensor_data):
        """更新设备环境画像"""
        if device_id not in self.device_profiles:
            self.device_profiles[device_id] = {
                'flame_baseline': None,
                'smoke_baseline': None,
                'temp_baseline': None,
                'humidity_baseline': None,
                'light_baseline': None,
                'flame_variance': 0,
                'smoke_variance': 0,
                'temp_variance': 0,
                'light_variance': 0,
                'last_update': time.time()
            }

        profile = self.device_profiles[device_id]

        # 更新基准值（使用滑动平均）
        alpha = 0.1  # 学习率

        # 获取传感器值，如果为None则设为0，防止TypeError
        flame_val = sensor_data.get('flame_value')
        if flame_val is None: flame_val = 0
        
        smoke_val = sensor_data.get('smoke_value')
        if smoke_val is None: smoke_val = 0
        
        temp_val = sensor_data.get('temperature')
        if temp_val is None: temp_val = 25
        
        humid_val = sensor_data.get('humidity')
        if humid_val is None: humid_val = 50
        
        light_val = sensor_data.get('light_level')
        if light_val is None: light_val = 10

        if profile['flame_baseline'] is None:
            # 首次初始化
            profile['flame_baseline'] = flame_val
            profile['smoke_baseline'] = smoke_val
            profile['temp_baseline'] = temp_val
            profile['humidity_baseline'] = humid_val
            profile['light_baseline'] = light_val
        else:
            # 滑动平均更新
            profile['flame_baseline'] = alpha * flame_val + (1 - alpha) * profile['flame_baseline']
            profile['smoke_baseline'] = alpha * smoke_val + (1 - alpha) * profile['smoke_baseline']
            profile['temp_baseline'] = alpha * temp_val + (1 - alpha) * profile['temp_baseline']
            profile['humidity_baseline'] = alpha * humid_val + (1 - alpha) * profile['humidity_baseline']
            profile['light_baseline'] = alpha * light_val + (1 - alpha) * profile['light_baseline']

        profile['last_update'] = time.time()

    def get_recent_data(self, device_id, seconds=30):
        """获取指定设备最近N秒的数据"""
        current_time = time.time()
        cutoff_time = current_time - seconds

        recent_data = []
        for entry in self.data_history:
            if entry['device_id'] == device_id and entry['timestamp'] >= cutoff_time:
                recent_data.append(entry['data'])

        return recent_data

    def analyze_sensor_health(self, device_id):
        """分析传感器健康度"""
        recent_data = self.get_recent_data(device_id, 60)  # 最近1分钟数据

        if len(recent_data) < 5:
            return 0.8  # 数据不足，给中等健康度

        health_scores = {}

        # 分析每个传感器的稳定性和合理性
        for sensor in ['flame_value', 'smoke_value', 'temperature', 'humidity', 'light_level']:
            values = [d.get(sensor) for d in recent_data if d.get(sensor) is not None]

            if len(values) < 3:
                health_scores[sensor] = 0.5
                continue

            # 计算变异系数（标准差/均值）
            mean_val = np.mean(values)
            std_val = np.std(values)

            if mean_val == 0:
                cv = 0
            else:
                cv = std_val / abs(mean_val)

            # 基于变异系数评估健康度
            if cv < 0.1:  # 非常稳定
                health_scores[sensor] = 1.0
            elif cv < 0.3:  # 正常波动
                health_scores[sensor] = 0.8
            elif cv < 0.5:  # 波动较大
                health_scores[sensor] = 0.6
            else:  # 波动过大，可能故障
                health_scores[sensor] = 0.3

        # 检查数据合理性
        for data in recent_data[-5:]:  # 检查最近5条数据
            temp = data.get('temperature', 25)
            humidity = data.get('humidity', 50)

            # 温度和湿度合理性检查
            if temp < -10 or temp > 60:
                health_scores['temperature'] = min(health_scores.get('temperature', 1.0), 0.3)
            if humidity < 0 or humidity > 100:
                health_scores['humidity'] = min(health_scores.get('humidity', 1.0), 0.3)

        # 计算总体健康度
        overall_health = np.mean(list(health_scores.values()))
        return overall_health

    def detect_patterns(self, device_id, current_data):
        """检测数据模式"""
        recent_data = self.get_recent_data(device_id, 30)

        if len(recent_data) < 5:
            return {'fire_probability': 0.5, 'false_alarm_probability': 0.5}

        # 火灾模式特征
        fire_indicators = {
            'flame_rising': False,
            'smoke_rising': False,
            'temp_rising': False,
            'consistency': False
        }

        # 误报模式特征
        false_alarm_indicators = {
            'flame_spike': False,
            'smoke_spike': False,
            'temp_normal': False,
            'inconsistency': False
        }

        # 提取时间序列
        flame_values = [d.get('flame_value', 2000) for d in recent_data if d.get('flame_value') is not None]
        smoke_values = [d.get('smoke_value', 2000) for d in recent_data if d.get('smoke_value') is not None]
        temp_values = [d.get('temperature', 25) for d in recent_data if d.get('temperature') is not None]

        # 分析趋势
        if len(flame_values) >= 3:
            flame_trend = np.polyfit(range(len(flame_values)), flame_values, 1)[0]
            fire_indicators['flame_rising'] = flame_trend < -50  # 火焰值下降趋势
            false_alarm_indicators['flame_spike'] = flame_values[-1] < 500 and flame_values[-2] > 1500  # 突然下降

        if len(smoke_values) >= 3:
            smoke_trend = np.polyfit(range(len(smoke_values)), smoke_values, 1)[0]
            fire_indicators['smoke_rising'] = smoke_trend < -100  # 烟雾值下降趋势
            false_alarm_indicators['smoke_spike'] = smoke_values[-1] < 1000 and smoke_values[-2] > 1800

        if len(temp_values) >= 3:
            temp_trend = np.polyfit(range(len(temp_values)), temp_values, 1)[0]
            fire_indicators['temp_rising'] = temp_trend > 0.5  # 温度上升趋势
            false_alarm_indicators['temp_normal'] = temp_values[-1] < 35  # 温度正常

        # 一致性检查
        fire_signals = sum([
            fire_indicators['flame_rising'],
            fire_indicators['smoke_rising'],
            fire_indicators['temp_rising']
        ])
        fire_indicators['consistency'] = fire_signals >= 2

        # 计算概率
        fire_probability = sum(fire_indicators.values()) / len(fire_indicators)
        false_alarm_probability = sum(false_alarm_indicators.values()) / len(false_alarm_indicators)

        return {
            'fire_probability': fire_probability,
            'false_alarm_probability': false_alarm_probability,
            'fire_indicators': fire_indicators,
            'false_alarm_indicators': false_alarm_indicators
        }

    def analyze_environmental_context(self, device_id, current_data):
        """分析环境上下文"""
        current_hour = datetime.now().hour

        # 时间因子（深夜火灾风险略高）
        time_factor = 1.0
        if 0 <= current_hour <= 6:  # 深夜
            time_factor = 1.2
        elif 12 <= current_hour <= 14:  # 午餐时间
            time_factor = 1.1

        # 季节因子（冬季取暖火灾风险高）
        month = datetime.now().month
        season_factor = 1.0
        if month in [12, 1, 2]:  # 冬季
            season_factor = 1.3
        elif month in [6, 7, 8]:  # 夏季
            season_factor = 0.9

        # 设备历史报警频率
        recent_alarms = self._get_recent_alarms(device_id, hours=24)
        alarm_frequency = len(recent_alarms) / 24.0  # 每小时报警次数

        frequency_factor = min(1.0, 1.0 - alarm_frequency * 0.1)  # 报警频繁时降低信任度

        # 传感器健康度影响
        sensor_health = self.analyze_sensor_health(device_id)
        health_factor = sensor_health

        return {
            'time_factor': time_factor,
            'season_factor': season_factor,
            'frequency_factor': frequency_factor,
            'health_factor': health_factor,
            'overall_factor': (time_factor + season_factor + frequency_factor + health_factor) / 4
        }

    def _get_recent_alarms(self, device_id, hours=24):
        """获取最近的报警记录"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cutoff_time = datetime.now() - timedelta(hours=hours)

            cursor.execute("""
                SELECT severity, timestamp FROM alert_history
                WHERE device_id = ? AND timestamp > ?
                ORDER BY timestamp DESC
            """, (device_id, cutoff_time))

            alarms = cursor.fetchall()
            conn.close()

            return alarms
        except Exception as e:
            logger.error(f"获取报警历史失败: {e}")
            return []

    def ai_prediction(self, device_id, current_data, pattern_analysis):
        """使用AI模型进行预测"""
        try:
            # 构建AI提示
            prompt_context = f"""
你是一个火灾报警系统的AI分析师，负责降低误报率。请分析以下传感器数据：

当前传感器数据:
- 火焰传感器值: {current_data.get('flame_value', 'N/A')}
- 烟雾传感器值: {current_data.get('smoke_value', 'N/A')}
- 温度: {current_data.get('temperature', 'N/A')}°C
- 湿度: {current_data.get('humidity', 'N/A')}%
- 光照强度: {current_data.get('light_level', 'N/A')}

模式分析结果:
- 火灾概率: {pattern_analysis.get('fire_probability', 0):.2%}
- 误报概率: {pattern_analysis.get('false_alarm_probability', 0):.2%}

请判断这次报警的真实性，返回一个0-1之间的置信度分数：
- 0.0-0.3: 很可能是误报
- 0.3-0.7: 不确定，需要更多观察
- 0.7-1.0: 很可能是真实火灾

只返回数字，不要其他解释。
"""

            # 调用AI
            ai_response = new("你是火灾报警AI分析师，只返回0-1之间的置信度分数", prompt_context)

            # 解析AI响应
            try:
                confidence = float(ai_response.strip())
                confidence = max(0.0, min(1.0, confidence))  # 确保在0-1范围内
                return confidence
            except ValueError:
                logger.warning(f"AI响应解析失败: {ai_response}")
                return 0.5  # 默认中等置信度

        except Exception as e:
            logger.error(f"AI预测失败: {e}")
            return 0.5  # AI失败时返回中等置信度

    def make_decision(self, device_id, current_data, hardware_result):
        """AI辅助决策函数

        Args:
            device_id: 设备ID
            current_data: 当前传感器数据
            hardware_result: 硬件阈值判断结果 ('normal', 'warning', 'alarm')

        Returns:
            dict: 包含最终决策和详细分析
        """

        # 添加数据到历史
        self.add_sensor_data(device_id, current_data)

        # 如果硬件判断为正常，直接返回
        if hardware_result == 'normal':
            decision = {
                'final_result': 'normal',
                'confidence': 0.9,
                'intervention': False,
                'reasoning': '硬件阈值判断正常，无需AI干预'
            }
            self.alarm_history.append({
                'timestamp': time.time(),
                'device_id': device_id,
                'hardware_result': hardware_result,
                'final_result': decision['final_result'],
                'intervention': False
            })
            return decision

        # 获取各维度分析结果
        pattern_analysis = self.detect_patterns(device_id, current_data)
        environmental_context = self.analyze_environmental_context(device_id, current_data)
        sensor_health = self.analyze_sensor_health(device_id)

        # AI预测
        ai_confidence = self.ai_prediction(device_id, current_data, pattern_analysis)

        # 计算各维度得分
        hardware_score = 0.8 if hardware_result == 'alarm' else 0.6
        pattern_score = 1 - pattern_analysis['false_alarm_probability']
        historical_score = environmental_context['frequency_factor']
        environmental_score = environmental_context['overall_factor']
        ai_score = ai_confidence

        # 加权计算最终置信度
        final_confidence = (
            hardware_score * self.decision_weights['hardware_threshold'] +
            pattern_score * self.decision_weights['pattern_matching'] +
            historical_score * self.decision_weights['historical_analysis'] +
            environmental_score * self.decision_weights['environmental_context'] +
            ai_score * self.decision_weights['ai_prediction']
        )

        # 决策逻辑
        threshold_high = 0.7  # 高置信度阈值
        threshold_low = 0.4   # 低置信度阈值

        if sensor_health < self.sensor_health_threshold:
            # 传感器不健康，降低报警置信度
            final_confidence *= 0.6
            decision = {
                'final_result': 'warning' if hardware_result == 'alarm' else 'normal',
                'confidence': final_confidence,
                'intervention': True,
                'reasoning': f'传感器健康度低({sensor_health:.2f})，降级处理',
                'sensor_health': sensor_health
            }
        elif final_confidence >= threshold_high:
            # 高置信度，维持报警
            decision = {
                'final_result': hardware_result,
                'confidence': final_confidence,
                'intervention': hardware_result == 'alarm' and final_confidence < 0.9,
                'reasoning': f'AI分析确认({final_confidence:.2f} >= {threshold_high})，维持{hardware_result}级别'
            }
        elif final_confidence <= threshold_low:
            # 低置信度，降级或取消报警
            if hardware_result == 'alarm':
                final_result = 'warning'
            elif hardware_result == 'warning':
                final_result = 'normal'
            else:
                final_result = 'normal'

            decision = {
                'final_result': final_result,
                'confidence': final_confidence,
                'intervention': True,
                'reasoning': f'AI分析置信度低({final_confidence:.2f} <= {threshold_low})，降级为{final_result}'
            }
        else:
            # 中等置信度，保持原级别但记录
            decision = {
                'final_result': hardware_result,
                'confidence': final_confidence,
                'intervention': False,
                'reasoning': f'AI分析中等置信度({final_confidence:.2f})，保持原判断'
            }

        # 添加详细分析信息
        decision.update({
            'device_id': device_id,
            'hardware_result': hardware_result,
            'analysis_details': {
                'hardware_score': hardware_score,
                'pattern_score': pattern_score,
                'historical_score': historical_score,
                'environmental_score': environmental_score,
                'ai_score': ai_score,
                'pattern_analysis': pattern_analysis,
                'environmental_context': environmental_context,
                'sensor_health': sensor_health
            }
        })

        # 记录决策历史
        self.alarm_history.append({
            'timestamp': time.time(),
            'device_id': device_id,
            'hardware_result': hardware_result,
            'final_result': decision['final_result'],
            'confidence': final_confidence,
            'intervention': decision['intervention']
        })

        logger.info(f"AI决策完成 - 设备:{device_id}, 硬件:{hardware_result} -> 最终:{decision['final_result']}, 置信度:{final_confidence:.2f}, 干预:{decision['intervention']}")

        return decision

    def get_decision_statistics(self, hours=24):
        """获取决策统计信息"""
        current_time = time.time()
        cutoff_time = current_time - hours * 3600

        recent_decisions = [
            d for d in self.alarm_history
            if d['timestamp'] >= cutoff_time
        ]

        if not recent_decisions:
            return {
                'total_decisions': 0,
                'intervention_rate': 0,
                'accuracy_metrics': {}
            }

        total_decisions = len(recent_decisions)
        interventions = sum(1 for d in recent_decisions if d['intervention'])

        return {
            'total_decisions': total_decisions,
            'intervention_rate': interventions / total_decisions,
            'intervention_count': interventions,
            'average_confidence': np.mean([d.get('confidence', 0.5) for d in recent_decisions]),
            'recent_decisions': recent_decisions[-10:]  # 最近10次决策
        }

# 全局AI决策引擎实例
ai_decision_engine = AIAlarmDecisionEngine()

def ai_assisted_alarm_decision(device_id, sensor_data, hardware_result):
    """AI辅助报警决策接口函数

    Args:
        device_id: 设备ID
        sensor_data: 传感器数据字典
        hardware_result: 硬件阈值判断结果

    Returns:
        dict: AI决策结果
    """
    return ai_decision_engine.make_decision(device_id, sensor_data, hardware_result)