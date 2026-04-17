#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
智能分析模块 - ESP32火灾报警系统特色功能
==========================================

功能特色:
1. 传感器数据统计分析
2. AI设备管理建议
3. 设备健康度评估
4. 预测性维护
5. 环境质量评估
6. 异常模式检测
"""

from ai import new
import sqlite3
import json
import numpy as np
from datetime import datetime, timedelta
import statistics
import math
import logging
import os

logger = logging.getLogger(__name__)


def _default_db_path():
    data_dir = os.environ.get('FIRE_ALARM_DATA_DIR')
    if data_dir:
        return os.path.join(data_dir, 'fire_alarm.db')
    return os.path.join('instance', 'fire_alarm.db')


class IntelligentAnalyzer:
    """智能分析器"""

    def __init__(self, db_path=None):
        self.db_path = db_path or _default_db_path()
        self.device_health_cache = {}

    def get_sensor_data_analysis(self, device_id=None, hours=24):
        """获取传感器数据分析 - 使用每个设备的前20条数据"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            if device_id:
                # 查询指定设备的前20条数据
                cursor.execute("""
                    SELECT device_id, flame_value, smoke_value, temperature, humidity, light_level, timestamp
                    FROM sensor_data
                    WHERE device_id = ?
                    ORDER BY timestamp DESC
                    LIMIT 20
                """, (device_id,))
            else:
                # 查询所有设备的数据，每个设备取前20条
                cursor.execute("""
                    SELECT device_id, flame_value, smoke_value, temperature, humidity, light_level, timestamp
                    FROM sensor_data
                    ORDER BY device_id, timestamp DESC
                """)

            data = cursor.fetchall()
            conn.close()

            if not data:
                return {"error": "没有足够的数据进行分析"}

            # 如果是查询所有设备，需要按设备分组，每个设备取前20条
            if not device_id:
                device_data = {}
                for row in data:
                    device_id_row = row[0]
                    if device_id_row not in device_data:
                        device_data[device_id_row] = []
                    if len(device_data[device_id_row]) < 20:  # 每个设备最多20条
                        device_data[device_id_row].append(row)

                # 合并所有设备的数据
                data = []
                for device_rows in device_data.values():
                    data.extend(device_rows)

            # 转换为字典格式
            sensor_readings = {
                'flame': [],  # 注意：数据库中是flame_value，但分析中保持为flame
                'smoke': [],  # 注意：数据库中是smoke_value，但分析中保持为smoke
                'temperature': [],
                'humidity': [],
                'light_level': [],
                'timestamps': []
            }

            for row in data:
                if row[1] is not None: sensor_readings['flame'].append(row[1])  # flame_value -> flame
                if row[2] is not None: sensor_readings['smoke'].append(row[2])  # smoke_value -> smoke
                if row[3] is not None: sensor_readings['temperature'].append(row[3])
                if row[4] is not None: sensor_readings['humidity'].append(row[4])
                if row[5] is not None: sensor_readings['light_level'].append(row[5])
                sensor_readings['timestamps'].append(row[6])

            # 执行统计分析
            analysis = self._perform_statistical_analysis(sensor_readings)

            return {
                "device_id": device_id or "all",
                "analysis_period": "每个设备前20条数据",
                "data_points": len(data),
                "statistics": analysis,
                "recommendations": self._generate_data_recommendations(analysis),
                "analysis_timestamp": datetime.now().isoformat()
            }

        except Exception as e:
            logger.error(f"传感器数据分析错误: {e}")
            return {"error": f"分析失败: {str(e)}"}

    def _perform_statistical_analysis(self, readings):
        """执行统计分析"""
        analysis = {}

        for sensor_type, values in readings.items():
            if sensor_type == 'timestamps' or not values:
                continue

            try:
                # 基础统计
                analysis[sensor_type] = {
                    'current': values[0] if values else None,
                    'average': statistics.mean(values),
                    'median': statistics.median(values),
                    'min': min(values),
                    'max': max(values),
                    'std_dev': statistics.stdev(values) if len(values) > 1 else 0,
                    'trend': self._calculate_trend(values),
                    'stability': self._calculate_stability(values),
                    'anomalies': self._detect_anomalies(values)
                }

                # 计算百分位数
                if len(values) > 4:
                    analysis[sensor_type]['percentiles'] = {
                        'p25': np.percentile(values, 25),
                        'p75': np.percentile(values, 75),
                        'p90': np.percentile(values, 90),
                        'p95': np.percentile(values, 95)
                    }

            except Exception as e:
                logger.warning(f"传感器 {sensor_type} 统计分析失败: {e}")
                analysis[sensor_type] = {"error": str(e)}

        return analysis

    def _calculate_trend(self, values):
        """计算趋势"""
        if len(values) < 3:
            return "insufficient_data"

        # 简单线性回归计算趋势
        x = list(range(len(values)))
        n = len(values)

        sum_x = sum(x)
        sum_y = sum(values)
        sum_xy = sum(x[i] * values[i] for i in range(n))
        sum_x2 = sum(x[i] ** 2 for i in range(n))

        # 计算斜率
        slope = (n * sum_xy - sum_x * sum_y) / (n * sum_x2 - sum_x ** 2)

        # 判断趋势
        if abs(slope) < 0.1:
            return "stable"
        elif slope > 0:
            return "increasing"
        else:
            return "decreasing"

    def _calculate_stability(self, values):
        """计算稳定性"""
        if len(values) < 2:
            return "unknown"

        # 使用变异系数评估稳定性
        mean_val = statistics.mean(values)
        if mean_val == 0:
            return "unknown"

        std_dev = statistics.stdev(values) if len(values) > 1 else 0
        cv = (std_dev / abs(mean_val)) * 100

        if cv < 10:
            return "very_stable"
        elif cv < 25:
            return "stable"
        elif cv < 50:
            return "moderate"
        else:
            return "unstable"

    def _detect_anomalies(self, values):
        """检测异常值"""
        if len(values) < 4:
            return []

        try:
            # 使用IQR方法检测异常值
            q1 = np.percentile(values, 25)
            q3 = np.percentile(values, 75)
            iqr = q3 - q1

            lower_bound = q1 - 1.5 * iqr
            upper_bound = q3 + 1.5 * iqr

            anomalies = []
            for i, value in enumerate(values):
                if value < lower_bound or value > upper_bound:
                    anomalies.append({
                        'index': i,
                        'value': value,
                        'type': 'low' if value < lower_bound else 'high'
                    })

            return anomalies
        except:
            return []

    def _generate_data_recommendations(self, analysis):
        """基于数据分析生成建议"""
        recommendations = []

        # 温度相关建议
        if 'temperature' in analysis:
            temp_stats = analysis['temperature']
            if temp_stats.get('average', 0) > 30:
                recommendations.append({
                    'type': 'temperature',
                    'priority': 'high',
                    'message': '平均温度偏高，建议检查通风设备和散热系统',
                    'action': '检查空调或风扇运行状态'
                })

            if temp_stats.get('trend') == 'increasing':
                recommendations.append({
                    'type': 'temperature',
                    'priority': 'medium',
                    'message': '温度呈上升趋势，建议持续监控',
                    'action': '增加温度监控频率'
                })

        # 湿度相关建议
        if 'humidity' in analysis:
            humidity_stats = analysis['humidity']
            if humidity_stats.get('average', 0) > 70:
                recommendations.append({
                    'type': 'humidity',
                    'priority': 'medium',
                    'message': '湿度偏高，可能导致设备腐蚀',
                    'action': '考虑增加除湿设备'
                })

        # 火焰传感器建议
        if 'flame' in analysis:
            flame_stats = analysis['flame']
            if flame_stats.get('stability') == 'unstable':
                recommendations.append({
                    'type': 'sensor',
                    'priority': 'high',
                    'message': '火焰传感器读数不稳定，可能需要校准',
                    'action': '检查传感器连接或进行校准'
                })

        return recommendations

    def get_device_health_score(self, device_id):
        """获取设备健康评分"""
        try:
            # 检查缓存
            cache_key = f"{device_id}_health"
            if cache_key in self.device_health_cache:
                cache_time = self.device_health_cache[cache_key]['timestamp']
                if datetime.now().timestamp() - cache_time < 300:  # 5分钟缓存
                    return self.device_health_cache[cache_key]['score']

            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # 获取设备的前20条数据
            cursor.execute("""
                SELECT flame_value, smoke_value, temperature, humidity, light_level, timestamp
                FROM sensor_data
                WHERE device_id = ?
                ORDER BY timestamp DESC
                LIMIT 20
            """, (device_id,))

            data = cursor.fetchall()
            conn.close()

            if len(data) < 5:
                return {"score": 85, "status": "insufficient_data", "factors": []}

            # 计算各项健康指标
            health_factors = {
                'data_frequency': self._check_data_frequency(data),
                'sensor_stability': self._check_sensor_stability(data),
                'communication_reliability': self._check_communication_reliability(device_id),
                'environmental_normality': self._check_environmental_normality(data)
            }

            # 计算总分
            total_score = sum(factors['score'] for factors in health_factors.values()) / len(health_factors)

            health_score = {
                'score': round(total_score, 1),
                'status': self._get_health_status(total_score),
                'factors': health_factors,
                'device_id': device_id,
                'timestamp': datetime.now().isoformat()
            }

            # 缓存结果
            self.device_health_cache[cache_key] = {
                'score': health_score,
                'timestamp': datetime.now().timestamp()
            }

            return health_score

        except Exception as e:
            logger.error(f"设备健康评分计算错误: {e}")
            return {"score": 50, "status": "error", "error": str(e)}

    def _check_data_frequency(self, data):
        """检查数据频率"""
        if len(data) < 20:
            return {'score': 70, 'status': 'insufficient', 'message': '数据点不足'}

        # 计算数据间隔
        timestamps = [row[5] for row in data if row[5]]
        if len(timestamps) < 2:
            return {'score': 60, 'status': 'poor', 'message': '时间戳数据异常'}

        # 计算平均间隔
        intervals = []
        for i in range(1, len(timestamps)):
            try:
                t1 = datetime.fromisoformat(timestamps[i])
                t2 = datetime.fromisoformat(timestamps[i-1])
                interval = (t2 - t1).total_seconds()
                intervals.append(interval)
            except:
                continue

        if not intervals:
            return {'score': 60, 'status': 'poor', 'message': '时间格式错误'}

        avg_interval = sum(intervals) / len(intervals)

        # 理想间隔是2-5秒
        if 2 <= avg_interval <= 10:
            return {'score': 95, 'status': 'excellent', 'message': '数据传输频率正常'}
        elif 10 < avg_interval <= 30:
            return {'score': 80, 'status': 'good', 'message': '数据传输频率略慢'}
        else:
            return {'score': 60, 'status': 'poor', 'message': '数据传输频率异常'}

    def _check_sensor_stability(self, data):
        """检查传感器稳定性"""
        stability_scores = []

        # 检查每个传感器的稳定性
        sensor_indices = {'flame': 0, 'smoke': 1, 'temperature': 2, 'humidity': 3, 'light_level': 4}

        for sensor_name, index in sensor_indices.items():
            values = [row[index] for row in data if row[index] is not None]

            if len(values) < 5:
                stability_scores.append(70)
                continue

            try:
                # 计算变异系数
                mean_val = statistics.mean(values)
                if mean_val != 0:
                    std_dev = statistics.stdev(values) if len(values) > 1 else 0
                    cv = (std_dev / abs(mean_val)) * 100

                    if cv < 15:
                        stability_scores.append(95)
                    elif cv < 30:
                        stability_scores.append(85)
                    else:
                        stability_scores.append(65)
                else:
                    stability_scores.append(80)
            except:
                stability_scores.append(75)

        avg_stability = sum(stability_scores) / len(stability_scores)

        if avg_stability >= 90:
            return {'score': avg_stability, 'status': 'excellent', 'message': '所有传感器读数稳定'}
        elif avg_stability >= 75:
            return {'score': avg_stability, 'status': 'good', 'message': '传感器基本稳定'}
        else:
            return {'score': avg_stability, 'status': 'poor', 'message': '部分传感器不稳定，建议检查'}

    def _check_communication_reliability(self, device_id):
        """检查通信可靠性"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # 检查最近24小时的数据点数量
            time_threshold = datetime.now() - timedelta(hours=24)
            cursor.execute("""
                SELECT COUNT(*) FROM sensor_data
                WHERE device_id = ? AND timestamp > ?
            """, (device_id, time_threshold))

            count = cursor.fetchone()[0]
            conn.close()

            # 理想情况下24小时应有4320个数据点（每10秒一个）
            expected_count = 8640  # 每10秒一个
            actual_ratio = count / expected_count

            if actual_ratio >= 0.9:
                return {'score': 95, 'status': 'excellent', 'message': '通信稳定可靠'}
            elif actual_ratio >= 0.7:
                return {'score': 80, 'status': 'good', 'message': '通信基本稳定'}
            elif actual_ratio >= 0.5:
                return {'score': 65, 'status': 'moderate', 'message': '通信偶有中断'}
            else:
                return {'score': 40, 'status': 'poor', 'message': '通信频繁中断，需要检查'}

        except Exception as e:
            return {'score': 50, 'status': 'error', 'message': f'通信检查失败: {str(e)}'}

    def _check_environmental_normality(self, data):
        """检查环境正常性"""
        if len(data) < 10:
            return {'score': 80, 'status': 'insufficient', 'message': '数据不足'}

        # 检查温度和湿度是否在正常范围
        temperatures = [row[2] for row in data if row[2] is not None]
        humidities = [row[3] for row in data if row[3] is not None]

        score = 100
        issues = []

        if temperatures:
            avg_temp = statistics.mean(temperatures)
            if avg_temp > 35:
                score -= 15
                issues.append('温度偏高')
            elif avg_temp < 10:
                score -= 10
                issues.append('温度偏低')

        if humidities:
            avg_humidity = statistics.mean(humidities)
            if avg_humidity > 80:
                score -= 10
                issues.append('湿度过高')
            elif avg_humidity < 20:
                score -= 5
                issues.append('湿度过低')

        if score >= 90:
            status = 'excellent'
            message = '环境条件良好'
        elif score >= 75:
            status = 'good'
            message = '环境条件基本正常'
        else:
            status = 'moderate'
            message = f'环境条件需关注: {", ".join(issues)}'

        return {'score': score, 'status': status, 'message': message}

    def _get_health_status(self, score):
        """根据分数获取健康状态"""
        if score >= 90:
            return 'excellent'
        elif score >= 75:
            return 'good'
        elif score >= 60:
            return 'moderate'
        elif score >= 40:
            return 'poor'
        else:
            return 'critical'

    def get_ai_maintenance_suggestions(self, device_id, health_score=None):
        """获取AI维护建议"""
        try:
            # 获取设备健康评分
            if not health_score:
                health_score = self.get_device_health_score(device_id)

            # 获取最近的传感器数据分析
            data_analysis = self.get_sensor_data_analysis(device_id, hours=48)

            # 先返回默认建议，然后异步调用AI
            default_suggestions = self._get_default_suggestions(health_score, data_analysis)

            # 尝试异步调用AI（带超时）
            import threading
            import time

            ai_result = {}

            def call_ai_async():
                try:
                    # 构建AI提示词
                    system_prompt = """你是一个专业的ESP32火灾报警系统维护专家。请基于提供的设备健康评分和传感器数据分析，为用户提供具体、实用的维护建议。

要求：
1. 建议要具体可操作
2. 按优先级排序（高优先级、中优先级、低优先级）
3. 包含预防性维护建议
4. 考虑成本效益
5. 用简洁明了的中文回答
6. 每条建议包含：具体行动、预估耗时、成本等级、理由说明

请按以下格式返回，用中文自然语言描述：

【高优先级建议】
1. [具体建议内容]
   - 预估耗时：X分钟
   - 成本等级：X/5
   - 理由：[具体说明]

【中优先级建议】
2. [具体建议内容]
   - 预估耗时：X分钟
   - 成本等级：X/5
   - 理由：[具体说明]

【低优先级建议】
3. [具体建议内容]
   - 预估耗时：X分钟
   - 成本等级：X/5
   - 理由：[具体说明]"""

                    user_prompt = f"""
设备ID: {device_id}
健康评分: {health_score.get('score', 'N/A')} 分
健康状态: {health_score.get('status', 'N/A')}

传感器数据分析:
{json.dumps(data_analysis.get('statistics', {}), ensure_ascii=False, indent=2)}

健康因素详情:
{json.dumps(health_score.get('factors', {}), ensure_ascii=False, indent=2)}

请根据这些信息提供专业的维护建议。
"""

                    # 调用AI接口
                    ai_response = new(system_prompt, user_prompt)
                    suggestions = self._parse_ai_suggestions(ai_response)
                    ai_result['suggestions'] = suggestions
                    ai_result['success'] = True

                except Exception as e:
                    logger.warning(f"AI调用失败: {e}")
                    ai_result['success'] = False
                    ai_result['error'] = str(e)

            # 启动AI调用线程
            ai_thread = threading.Thread(target=call_ai_async)
            ai_thread.daemon = True
            ai_thread.start()

            return {
                "device_id": device_id,
                "health_score": health_score.get('score', 'N/A'),
                "ai_suggestions": {
                    "suggestions": default_suggestions,
                    "source": "default_analysis"
                },
                "analysis_timestamp": datetime.now().isoformat(),
                "data_summary": {
                    "health_status": health_score.get('status', 'unknown'),
                    "data_points": data_analysis.get('data_points', 0),
                    "analysis_period": data_analysis.get('analysis_period', 'unknown')
                }
            }

        except Exception as e:
            logger.error(f"AI维护建议生成错误: {e}")
            return {
                "device_id": device_id,
                "error": f"建议生成失败: {str(e)}",
                "ai_suggestions": {
                    "suggestions": [
                        {
                            "category": "basic_maintenance",
                            "priority": "medium",
                            "suggestion": "请检查设备连接和传感器状态",
                            "estimated_time": 15,
                            "cost_level": 1,
                            "reasoning": "基础维护建议"
                        }
                    ],
                    "source": "fallback"
                }
            }

    def _get_default_suggestions(self, health_score, data_analysis):
        """生成默认的智能建议"""
        suggestions = []
        score = health_score.get('score', 50)
        status = health_score.get('status', 'unknown')

        # 根据健康评分生成建议
        if score < 60:
            suggestions.extend([
                {
                    "category": "health_maintenance",
                    "priority": "high",
                    "suggestion": "设备健康评分偏低，建议立即进行全面检查",
                    "estimated_time": 30,
                    "cost_level": 2,
                    "reasoning": f"当前健康评分{score}分，低于安全阈值"
                },
                {
                    "category": "sensor_check",
                    "priority": "high",
                    "suggestion": "检查火焰和烟雾传感器连接和校准",
                    "estimated_time": 20,
                    "cost_level": 1,
                    "reasoning": "传感器异常是健康评分低的主要原因"
                }
            ])
        elif score < 80:
            suggestions.extend([
                {
                    "category": "preventive_maintenance",
                    "priority": "medium",
                    "suggestion": "设备健康评分中等，建议进行预防性维护",
                    "estimated_time": 25,
                    "cost_level": 2,
                    "reasoning": f"当前健康评分{score}分，需要关注设备状态"
                }
            ])
        else:
            suggestions.extend([
                {
                    "category": "routine_maintenance",
                    "priority": "low",
                    "suggestion": "设备状态良好，建议定期维护检查",
                    "estimated_time": 15,
                    "cost_level": 1,
                    "reasoning": f"当前健康评分{score}分，设备运行正常"
                }
            ])

        # 添加通用建议
        suggestions.extend([
            {
                "category": "data_monitoring",
                "priority": "medium",
                "suggestion": "持续监控传感器数据趋势",
                "estimated_time": 10,
                "cost_level": 1,
                "reasoning": "定期监控有助于及时发现潜在问题"
            },
            {
                "category": "environment_check",
                "priority": "low",
                "suggestion": "检查设备周围环境条件",
                "estimated_time": 15,
                "cost_level": 1,
                "reasoning": "良好的环境有助于设备稳定运行"
            }
        ])

        return suggestions[:6]  # 最多返回6条建议

    def _parse_ai_suggestions(self, ai_response):
        """解析AI返回的自然语言建议为结构化格式"""
        suggestions = []

        try:
            # 按优先级分组解析
            priority_patterns = [
                ("【高优先级建议】", "high"),
                ("【中优先级建议】", "medium"),
                ("【低优先级建议】", "low"),
                ("【预防性维护建议】", "medium")
            ]

            lines = ai_response.split('\n')
            current_suggestion = {}

            for line in lines:
                line = line.strip()

                # 检查是否是新的建议开始
                new_suggestion = False
                for pattern, priority in priority_patterns:
                    if pattern in line:
                        # 保存上一个建议
                        if current_suggestion:
                            suggestions.append(current_suggestion)

                        # 开始新建议
                        current_suggestion = {
                            "priority": priority,
                            "category": "ai_maintenance",
                            "suggestion": "",
                            "estimated_time": 30,
                            "cost_level": 2,
                            "reasoning": ""
                        }
                        new_suggestion = True
                        break

                if not new_suggestion and current_suggestion:
                    # 解析建议内容
                    if line.startswith(('1.', '2.', '3.', '4.', '5.', '6.', '7.', '8.', '9.')):
                        # 建议主要内容
                        content = line[2:].strip()
                        current_suggestion["suggestion"] = content
                    elif line.startswith('- 预估耗时：'):
                        # 解析耗时
                        time_str = line.replace('- 预估耗时：', '').strip()
                        try:
                            time_num = int(''.join(filter(str.isdigit, time_str)))
                            current_suggestion["estimated_time"] = min(time_num, 120)  # 最大120分钟
                        except:
                            current_suggestion["estimated_time"] = 30
                    elif line.startswith('- 成本等级：'):
                        # 解析成本等级
                        cost_str = line.replace('- 成本等级：', '').strip()
                        try:
                            cost_num = int(cost_str.split('/')[0])
                            current_suggestion["cost_level"] = min(max(cost_num, 1), 5)  # 1-5范围
                        except:
                            current_suggestion["cost_level"] = 2
                    elif line.startswith('- 理由：'):
                        # 解析理由
                        current_suggestion["reasoning"] = line.replace('- 理由：', '').strip()
                    elif current_suggestion.get("suggestion") and not line.startswith('-'):
                        # 续行内容，添加到建议中
                        current_suggestion["suggestion"] += " " + line

            # 添加最后一个建议
            if current_suggestion:
                suggestions.append(current_suggestion)

            # 如果没有解析到建议，创建一个默认建议
            if not suggestions:
                suggestions = [{
                    "priority": "medium",
                    "category": "ai_analysis",
                    "suggestion": ai_response[:200] + "..." if len(ai_response) > 200 else ai_response,
                    "estimated_time": 30,
                    "cost_level": 2,
                    "reasoning": "AI智能分析结果"
                }]

        except Exception as e:
            logger.warning(f"AI建议解析失败，使用原始响应: {e}")
            suggestions = [{
                "priority": "medium",
                "category": "ai_analysis",
                "suggestion": ai_response,
                "estimated_time": 30,
                "cost_level": 2,
                "reasoning": "AI智能分析结果"
            }]

        return suggestions

    def get_environmental_safety_index(self, device_id=None):
        """计算环境安全指数"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            if device_id:
                # 获取指定设备的前20条数据
                cursor.execute("""
                    SELECT flame_value, smoke_value, temperature, humidity, light_level, timestamp
                    FROM sensor_data
                    WHERE device_id = ?
                    ORDER BY timestamp DESC
                    LIMIT 20
                """, (device_id,))
            else:
                # 获取所有设备的数据，每个设备取前20条，需要包含设备ID
                cursor.execute("""
                    SELECT device_id, flame_value, smoke_value, temperature, humidity, light_level, timestamp
                    FROM sensor_data
                    ORDER BY device_id, timestamp DESC
                """)

            data = cursor.fetchall()
            conn.close()

            if len(data) < 5:
                return {"error": "数据不足，无法计算安全指数"}

            # 如果是查询所有设备，需要按设备分组，每个设备取前20条
            if not device_id:
                device_data = {}
                for row in data:
                    device_id_row = row[0]
                    if device_id_row not in device_data:
                        device_data[device_id_row] = []
                    if len(device_data[device_id_row]) < 20:  # 每个设备最多20条
                        device_data[device_id_row].append(row[1:])  # 去掉设备ID，只保留传感器数据

                # 合并所有设备的数据用于环境安全指数计算
                data = []
                for device_rows in device_data.values():
                    data.extend(device_rows)

            # 计算各项安全指标
            safety_factors = {
                'fire_risk': self._calculate_fire_risk(data),
                'temperature_safety': self._calculate_temperature_safety(data),
                'air_quality': self._calculate_air_quality(data),
                'lighting_safety': self._calculate_lighting_safety(data)
            }

            # 计算综合安全指数
            weights = {'fire_risk': 0.4, 'temperature_safety': 0.25, 'air_quality': 0.2, 'lighting_safety': 0.15}
            total_score = sum(safety_factors[factor] * weights[factor] for factor in weights)

            return {
                "device_id": device_id or "all",
                "overall_safety_index": round(total_score, 1),
                "safety_level": self._get_safety_level(total_score),
                "factors": safety_factors,
                "recommendations": self._generate_safety_recommendations(safety_factors),
                "data_points": len(data),
                "analysis_period": "6小时",
                "timestamp": datetime.now().isoformat()
            }

        except Exception as e:
            logger.error(f"环境安全指数计算错误: {e}")
            return {"error": f"计算失败: {str(e)}"}

    def _calculate_fire_risk(self, data):
        """计算火灾风险指数"""
        flame_values = [row[0] for row in data if row[0] is not None]
        smoke_values = [row[1] for row in data if row[1] is not None]
        temp_values = [row[2] for row in data if row[2] is not None]

        risk_score = 100  # 从100分开始扣分

        # 火焰传感器风险评估（值越低风险越高）
        if flame_values:
            avg_flame = statistics.mean(flame_values)
            if avg_flame < 500:
                risk_score -= 40
            elif avg_flame < 1000:
                risk_score -= 20

        # 烟雾传感器风险评估
        if smoke_values:
            avg_smoke = statistics.mean(smoke_values)
            if avg_smoke < 1000:
                risk_score -= 30
            elif avg_smoke < 1500:
                risk_score -= 15

        # 温度风险评估
        if temp_values:
            avg_temp = statistics.mean(temp_values)
            if avg_temp > 40:
                risk_score -= 30
            elif avg_temp > 35:
                risk_score -= 15

        return max(0, min(100, risk_score))

    def _calculate_temperature_safety(self, data):
        """计算温度安全指数"""
        temp_values = [row[2] for row in data if row[2] is not None]

        if not temp_values:
            return 80

        avg_temp = statistics.mean(temp_values)
        safety_score = 100

        # 根据温度范围评分
        if 18 <= avg_temp <= 28:
            safety_score = 100
        elif 15 <= avg_temp <= 32:
            safety_score = 85
        elif 10 <= avg_temp <= 35:
            safety_score = 70
        elif 5 <= avg_temp <= 40:
            safety_score = 50
        else:
            safety_score = 30

        # 考虑温度稳定性
        if len(temp_values) > 1:
            temp_std = statistics.stdev(temp_values)
            if temp_std > 10:
                safety_score -= 15
            elif temp_std > 5:
                safety_score -= 5

        return max(0, safety_score)

    def _calculate_air_quality(self, data):
        """计算空气质量指数"""
        smoke_values = [row[1] for row in data if row[1] is not None]

        if not smoke_values:
            return 85

        # 简化的空气质量评估（主要基于烟雾传感器）
        avg_smoke = statistics.mean(smoke_values)

        # MQ2传感器值越高表示空气质量越好
        if avg_smoke > 2000:
            return 95
        elif avg_smoke > 1500:
            return 85
        elif avg_smoke > 1000:
            return 70
        elif avg_smoke > 500:
            return 50
        else:
            return 30

    def _calculate_lighting_safety(self, data):
        """计算光照安全指数"""
        light_values = [row[4] for row in data if row[4] is not None]

        if not light_values:
            return 80

        avg_light = statistics.mean(light_values)

        # 光照强度适中得分较高
        if 10 <= avg_light <= 50:
            return 95
        elif 5 <= avg_light <= 80:
            return 85
        elif avg_light > 100:
            return 70  # 光照过强可能影响传感器
        else:
            return 60

        return max(0, min(100, avg_light))

    def _get_safety_level(self, score):
        """根据分数获取安全等级"""
        if score >= 90:
            return 'very_safe'
        elif score >= 75:
            return 'safe'
        elif score >= 60:
            return 'moderate'
        elif score >= 40:
            return 'risky'
        else:
            return 'dangerous'

    def _generate_safety_recommendations(self, factors):
        """生成安全建议"""
        recommendations = []

        if factors['fire_risk'] < 70:
            recommendations.append({
                'type': 'fire_prevention',
                'priority': 'high',
                'message': '火灾风险偏高，请检查火源和易燃物品',
                'action': '加强火灾预防措施'
            })

        if factors['temperature_safety'] < 70:
            recommendations.append({
                'type': 'temperature_control',
                'priority': 'medium',
                'message': '温度条件需要改善',
                'action': '调节空调或通风设备'
            })

        if factors['air_quality'] < 70:
            recommendations.append({
                'type': 'ventilation',
                'priority': 'medium',
                'message': '空气质量需要改善',
                'action': '增加通风或检查污染源'
            })

        if factors['lighting_safety'] < 70:
            recommendations.append({
                'type': 'lighting_adjustment',
                'priority': 'low',
                'message': '光照条件需要调整',
                'action': '调整照明设备'
            })

        return recommendations

    def get_all_devices_intelligence_analysis(self):
        """获取所有设备的汇总智能分析数据"""
        try:
            # 获取所有设备的数据分析
            all_analysis = self.get_sensor_data_analysis(device_id=None, hours=24)

            # 获取所有设备的健康度评分
            all_health_scores = {}
            device_ids = set()

            # 从分析数据中提取设备ID
            if 'devices' in all_analysis:
                for device_data in all_analysis['devices']:
                    device_ids.add(device_data['device_id'])

            # 如果没有设备数据，尝试从数据库获取设备列表
            if not device_ids:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                cursor.execute("SELECT DISTINCT device_id FROM sensor_data ORDER BY device_id")
                device_ids = [row[0] for row in cursor.fetchall()]
                conn.close()

            # 获取每个设备的健康度评分
            for device_id in device_ids:
                try:
                    health_score = self.get_device_health_score(device_id)
                    all_health_scores[device_id] = health_score
                except Exception as e:
                    logger.warning(f"获取设备 {device_id} 健康度评分失败: {e}")
                    # 设置默认健康度评分
                    all_health_scores[device_id] = {
                        'overall_score': 85.0,
                        'status': '良好',
                        'factors': {
                            'data_completeness': 90.0,
                            'sensor_stability': 85.0,
                            'operational_consistency': 80.0
                        }
                    }

            # 获取汇总的AI建议（使用所有设备的数据）
            try:
                ai_suggestions = self.get_ai_maintenance_suggestions(device_id=None)
            except Exception as e:
                logger.warning(f"获取汇总AI建议失败: {e}")
                ai_suggestions = {
                    'overall_status': '正常',
                    'priority_issues': [],
                    'recommendations': [
                        {
                            'category': '系统维护',
                            'suggestion': '定期检查所有设备运行状态',
                            'priority': 'medium'
                        }
                    ],
                    'next_maintenance': datetime.now() + timedelta(days=7)
                }

            # 获取环境安全指数（基于所有设备）
            try:
                safety_index = self.get_environmental_safety_index(device_id=None)
            except Exception as e:
                logger.warning(f"获取环境安全指数失败: {e}")
                safety_index = {
                    'overall_index': 85.0,
                    'status': '安全',
                    'factors': {
                        'temperature_safety': 90.0,
                        'humidity_safety': 85.0,
                        'air_quality': 80.0,
                        'lighting_safety': 85.0
                    },
                    'recommendations': [
                        {
                            'type': 'monitoring',
                            'priority': 'low',
                            'message': '继续监控环境状况',
                            'action': '保持正常运行'
                        }
                    ]
                }

            # 汇总返回所有设备的智能分析数据
            return {
                'all_analysis': all_analysis,
                'all_health_scores': all_health_scores,
                'ai_suggestions': ai_suggestions,
                'safety_index': safety_index,
                'total_devices': len(device_ids),
                'timestamp': datetime.now().isoformat(),
                'summary': {
                    'status': '运行正常' if len(device_ids) > 0 else '无设备',
                    'overall_health': sum(score.get('overall_score', 85) for score in all_health_scores.values()) / len(all_health_scores) if all_health_scores else 85.0,
                    'devices_online': len(device_ids),
                    'alerts_count': 0  # 可以从分析数据中计算
                }
            }

        except Exception as e:
            logger.error(f"获取所有设备智能分析失败: {e}")
            # 返回默认数据
            return {
                'all_analysis': {
                    'summary': {
                        'avg_temperature': 25.0,
                        'avg_humidity': 60.0,
                        'avg_flame': 1500.0,
                        'avg_smoke': 2000.0,
                        'data_points': 0
                    },
                    'devices': []
                },
                'all_health_scores': {},
                'ai_suggestions': {
                    'overall_status': '数据分析中',
                    'priority_issues': [],
                    'recommendations': [
                        {
                            'category': '数据采集',
                            'suggestion': '正在等待设备数据上传',
                            'priority': 'low'
                        }
                    ],
                    'next_maintenance': datetime.now() + timedelta(days=7)
                },
                'safety_index': {
                    'overall_index': 85.0,
                    'status': '安全',
                    'factors': {},
                    'recommendations': []
                },
                'total_devices': 0,
                'timestamp': datetime.now().isoformat(),
                'summary': {
                    'status': '等待数据',
                    'overall_health': 85.0,
                    'devices_online': 0,
                    'alerts_count': 0
                },
                'error': str(e)
            }

# 全局分析器实例
intelligent_analyzer = IntelligentAnalyzer()