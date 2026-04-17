// 引入 echarts
import * as echarts from '../../components/ec-canvas/echarts';

Page({
  data: {
    // 基础配置
    backendUrl: "https://icstop1syh.cpolar.top",
    currentDeviceId: "all", // 当前选择的设备ID，"all"表示汇总模式

    // 设备选择器
    deviceList: [
      { id: 'all', label: '所有设备汇总分析', type: 'summary' }
    ],
    selectedDeviceIndex: 0,

    // 设备健康度评估
    deviceHealth: {
      score: 0,
      status: "unknown",
      statusText: "未知",
      factors: []
    },

    // 健康度分布（汇总模式）
    healthDistribution: {
      excellent: 0,
      excellentCount: 0,
      good: 0,
      goodCount: 0,
      moderate: 0,
      moderateCount: 0
    },

    // 环境安全指数
    safetyIndex: {
      score: 0,
      level: "unknown",
      levelText: "未知",
      factors: []
    },

    // 安全指数分布（汇总模式）
    safetyDistribution: {
      verySafe: 0,
      verySafeCount: 0,
      safe: 0,
      safeCount: 0,
      moderate: 0,
      moderateCount: 0
    },

    // 数据统计概览
    statistics: {
      flame: { avg: 0, min: 0, max: 0, trend: "stable" },
      smoke: { avg: 0, min: 0, max: 0, trend: "stable" },
      temperature: { avg: 0, min: 0, max: 0, trend: "stable" },
      humidity: { avg: 0, min: 0, max: 0, trend: "stable" },
      lightLevel: { avg: 0, min: 0, max: 0, trend: "stable" }
    },

    // 趋势数据
    trendsData: null,

    // 趋势图表配置
    trendsChart: {
      onInit: null
    },

    // AI智能建议
    aiSuggestions: [],

    // 加载状态
    loading: {
      health: false,
      safety: false,
      statistics: false,
      trends: false,
      ai: false
    },

    // 错误信息
    errors: {
      health: "",
      safety: "",
      statistics: "",
      trends: "",
      ai: ""
    },

    // 最后更新时间
    lastUpdate: "",

    // 系统统计卡片数据（汇总模式）
    systemStats: {
      totalDevices: 0,
      avgHealthScore: 0,
      avgSafetyIndex: 0,
      warningsToday: 0
    }
  },

  onLoad() {
    console.log('智能分析页面加载...');
    this.setData({
      backendUrl: getApp().globalData?.backendUrl || "https://icstop1syh.cpolar.top",
      lastUpdate: this.formatTime(new Date())
    });

    // 初始化趋势图表
    this.initTrendsChart();

    this.loadDeviceList();
    this.loadAllData();
  },

  onShow() {
    // 页面显示时刷新数据
    this.refreshData();
  },

  onHide() {
    // 页面隐藏时停止数据加载，避免后台累积请求
    console.log('智能分析页面隐藏，停止数据加载');
  },

  onUnload() {
    console.log('智能分析页面卸载');
  },

  onPullDownRefresh() {
    // 下拉刷新
    this.refreshData();
    wx.stopPullDownRefresh();
  },

  // 初始化趋势图表
  initTrendsChart() {
    this.setData({
      'trendsChart.onInit': (canvas, width, height, dpr) => {
        // 保存 chart 实例，���后续更新使用
        this.trendsChartInstance = echarts.init(canvas, null, {
          width: width,
          height: height,
          devicePixelRatio: dpr
        });
        return this.trendsChartInstance;
      }
    });
  },

  // 更新趋势图表
  updateTrendsChart(trends) {
    const that = this;

    // 如果已经有 chart 实例，直接更新
    if (this.trendsChartInstance) {
      that.updateChartData(this.trendsChartInstance, trends);
      return;
    }

    // 否则等待 ec-canvas 初始化完成
    setTimeout(() => {
      if (this.trendsChartInstance) {
        that.updateChartData(this.trendsChartInstance, trends);
      }
    }, 500);
  },

  // 更新图表数据
  updateChartData(chart, trends) {
    try {
      console.log('更新图表数据:', trends);

      const sensorTypes = Object.keys(trends.trends || {});
      const datasets = sensorTypes.map((sensor, index) => {
        const colors = ['#FF6384', '#36A2EB', '#FFCE56', '#4BC0C0', '#9966FF'];
        const stats = trends.statistics[sensor] || {};
        const data = this.generateTrendData(stats);

        return {
          name: this.getSensorDisplayName(sensor),
          type: 'line',
          data: data,
          smooth: true,
          itemStyle: { color: colors[index % colors.length] },
          areaStyle: {
            color: {
              type: 'linear',
              x: 0, y: 0, x2: 0, y2: 1,
              colorStops: [
                { offset: 0, color: colors[index % colors.length] + '40' },
                { offset: 1, color: colors[index % colors.length] + '05' }
              ]
            }
          }
        };
      });

      const option = {
        tooltip: {
          trigger: 'axis'
        },
        legend: {
          data: sensorTypes.map(s => this.getSensorDisplayName(s)),
          bottom: 0
        },
        grid: {
          left: '3%',
          right: '4%',
          bottom: '15%',
          containLabel: true
        },
        xAxis: {
          type: 'category',
          boundaryGap: false,
          data: this.generateTimeLabels(24)
        },
        yAxis: {
          type: 'value'
        },
        series: datasets
      };

      chart.setOption(option);
    } catch (error) {
      console.error('更新图表数据失败:', error);
    }
  },

  // 加载设备列表
  loadDeviceList() {
    wx.request({
      url: `${this.data.backendUrl}/api/devices`,
      method: 'GET',
      timeout: 10000,
      success: (res) => {
        if (res.statusCode === 200 && res.data) {
          const devices = res.data;
          const deviceList = [
            { id: 'all', label: '所有设备汇总分析', type: 'summary' }
          ];

          devices.forEach(device => {
            deviceList.push({
              id: device.device_id,
              label: `${device.device_id} - ${device.location || '未知位置'}`,
              type: 'master'
            });
          });

          // 获取从机设备列表
          wx.request({
            url: `${this.data.backendUrl}/api/slaves`,
            method: 'GET',
            timeout: 10000,
            success: (slaveRes) => {
              if (slaveRes.statusCode === 200 && slaveRes.data) {
                slaveRes.data.forEach(slave => {
                  deviceList.push({
                    id: slave.device_id,
                    label: `${slave.device_id} - ${slave.location || '未知位置'}`,
                    type: 'slave'
                  });
                });
              }

              this.setData({ deviceList });
            }
          });
        }
      },
      fail: (err) => {
        console.error('加载设备列表失败:', err);
      }
    });
  },

  // 设备选择变化
  onDeviceChange(e) {
    const index = parseInt(e.detail.value);
    const selectedDevice = this.data.deviceList[index];

    this.setData({
      selectedDeviceIndex: index,
      currentDeviceId: selectedDevice.id
    });

    this.loadAllData();
  },

  // 刷新所有数据
  refreshData() {
    console.log('刷新智能分析数据...');
    this.setData({
      lastUpdate: this.formatTime(new Date())
    });
    this.loadAllData();
  },

  // 横幅刷新按钮点击事件
  refreshAllData() {
    wx.vibrateShort({
      type: 'light'
    });
    wx.showToast({
      title: '刷新中...',
      icon: 'loading',
      duration: 1000
    });
    this.refreshData();
  },

  // 加载所有分析数据
  loadAllData() {
    const { currentDeviceId } = this.data;

    // 重置数据
    this.setData({
      deviceHealth: { score: 0, status: 'unknown', statusText: '未知', factors: [] },
      safetyIndex: { score: 0, level: 'unknown', levelText: '未知', factors: [] },
      statistics: {
        flame: { avg: 0, min: 0, max: 0, trend: 'stable' },
        smoke: { avg: 0, min: 0, max: 0, trend: 'stable' },
        temperature: { avg: 0, min: 0, max: 0, trend: 'stable' },
        humidity: { avg: 0, min: 0, max: 0, trend: 'stable' },
        lightLevel: { avg: 0, min: 0, max: 0, trend: 'stable' }
      },
      aiSuggestions: [],
      errors: {
        health: '',
        safety: '',
        statistics: '',
        trends: '',
        ai: ''
      }
    });

    if (currentDeviceId === 'all') {
      // 汇总模式
      this.loadSystemStatistics();
      this.loadAllDevicesAnalysis();
    } else {
      // 单设备模式
      this.loadDeviceHealth(currentDeviceId);
      this.loadSafetyIndex(currentDeviceId);
      this.loadSensorStatistics(currentDeviceId);
      this.loadDeviceTrends(currentDeviceId);
      this.loadAiSuggestions(currentDeviceId);
    }
  },

  // 加载系统统计信息（汇总模式）
  loadSystemStatistics() {
    wx.request({
      url: `${this.data.backendUrl}/api/intelligence/statistics`,
      method: 'GET',
      timeout: 10000,
      success: (res) => {
        if (res.statusCode === 200 && res.data) {
          const stats = res.data;
          this.setData({
            systemStats: {
              totalDevices: stats.total_devices || 0,
              avgHealthScore: stats.health_statistics?.average || 0,
              avgSafetyIndex: stats.safety_statistics?.average || 0,
              warningsToday: stats.warnings_today || 0
            }
          });
        }
      },
      fail: (err) => {
        console.error('加载系统统计失败:', err);
      }
    });
  },

  // 加载所有设备分析（汇总模式）
  loadAllDevicesAnalysis() {
    wx.request({
      url: `${this.data.backendUrl}/api/intelligence/analysis`,
      method: 'GET',
      timeout: 10000,
      success: (res) => {
        if (res.statusCode === 200 && res.data) {
          const analysis = res.data;
          this.displayAllDevicesHealth(analysis);
          this.displayAllDevicesSafety(analysis);
          this.loadSystemRecommendations();
        }
      },
      fail: (err) => {
        console.error('加载所有设备分析失败:', err);
        this.setData({
          'errors.health': '无法获取汇总数据',
          'errors.safety': '无法获取汇总数据'
        });
      }
    });
  },

  // 显示所有设备健康度（汇总模式）
  displayAllDevicesHealth(analysis) {
    if (!analysis.devices || analysis.devices.length === 0) {
      this.setData({
        'errors.health': '暂无设备数据'
      });
      return;
    }

    const avgHealth = analysis.summary?.average_health_score || 0;
    const healthStatus = this.getHealthStatus(avgHealth);
    const distribution = analysis.summary?.health_distribution || {};

    const totalDevices = analysis.devices.length;
    this.setData({
      deviceHealth: {
        score: Math.round(avgHealth),
        status: healthStatus,
        statusText: this.getHealthStatusText(healthStatus),
        color: this.getHealthColor(avgHealth),
        factors: []
      },
      healthDistribution: {
        excellent: totalDevices > 0 ? Math.round((distribution.excellent || 0) / totalDevices * 100) : 0,
        excellentCount: distribution.excellent || 0,
        good: totalDevices > 0 ? Math.round((distribution.good || 0) / totalDevices * 100) : 0,
        goodCount: distribution.good || 0,
        moderate: totalDevices > 0 ? Math.round(((distribution.moderate || 0) + (distribution.poor || 0) + (distribution.critical || 0)) / totalDevices * 100) : 0,
        moderateCount: (distribution.moderate || 0) + (distribution.poor || 0) + (distribution.critical || 0)
      },
      'loading.health': false
    });
  },

  // 显示所有设备安全指数（汇总模式）
  displayAllDevicesSafety(analysis) {
    if (!analysis.devices || analysis.devices.length === 0) {
      this.setData({
        'errors.safety': '暂无设备数据'
      });
      return;
    }

    const avgSafety = analysis.summary?.average_safety_index || 0;
    const safetyLevel = this.getSafetyLevel(avgSafety);
    const distribution = analysis.summary?.safety_distribution || {};

    const totalDevices = analysis.devices.length;
    const safetyColor = this.getSafetyColor(safetyLevel);
    this.setData({
      safetyIndex: {
        score: Math.round(avgSafety),
        level: safetyLevel,
        levelText: this.getSafetyLevelText(safetyLevel),
        color: safetyColor,
        backgroundColor: safetyLevel === 'safe' ? '#f6ffed' : safetyLevel === 'moderate' ? '#fffbe6' : '#fff2f0',
        factors: []
      },
      safetyDistribution: {
        verySafe: totalDevices > 0 ? Math.round((distribution.very_safe || 0) / totalDevices * 100) : 0,
        verySafeCount: distribution.very_safe || 0,
        safe: totalDevices > 0 ? Math.round((distribution.safe || 0) / totalDevices * 100) : 0,
        safeCount: distribution.safe || 0,
        moderate: totalDevices > 0 ? Math.round(((distribution.moderate || 0) + (distribution.risky || 0) + (distribution.dangerous || 0)) / totalDevices * 100) : 0,
        moderateCount: (distribution.moderate || 0) + (distribution.risky || 0) + (distribution.dangerous || 0)
      },
      'loading.safety': false
    });
  },

  // 加载系统推荐（汇总模式）
  loadSystemRecommendations() {
    wx.request({
      url: `${this.data.backendUrl}/api/intelligence/recommendations`,
      method: 'GET',
      timeout: 10000,
      success: (res) => {
        if (res.statusCode === 200 && res.data) {
          const recommendations = res.data.recommendations || [];
          this.setData({
            aiSuggestions: recommendations,
            'loading.ai': false
          });
        }
      },
      fail: (err) => {
        console.error('加载系统推荐失败:', err);
        this.setData({
          'loading.ai': false
        });
      }
    });
  },

  // 加载设备健康度（单设备模式）
  loadDeviceHealth(deviceId) {
    this.setData({
      'loading.health': true,
      'errors.health': ''
    });

    wx.request({
      url: `${this.data.backendUrl}/api/intelligence/health-score/${deviceId}`,
      method: 'GET',
      timeout: 10000,
      success: (res) => {
        if (res.statusCode === 200 && res.data) {
          const healthData = res.data;
          let factors = [];

          if (healthData.factors && typeof healthData.factors === 'object') {
            factors = Object.entries(healthData.factors).map(([key, value]) => ({
              name: this.getFactorDisplayName(key),
              score: value.score || 0,
              percentage: value.score || 0,
              color: this.getHealthColor(value.score || 0),
              status: value.status || 'unknown'
            }));
          }

          const healthScore = healthData.score || 0;
          this.setData({
            deviceHealth: {
              score: healthScore,
              status: healthData.status || 'unknown',
              statusText: this.getHealthStatusText(healthData.status),
              color: this.getHealthColor(healthScore),
              factors: factors
            },
            'loading.health': false
          });
        }
      },
      fail: (err) => {
        console.error('设备健康度加载失败:', err);
        this.setData({
          'loading.health': false,
          'errors.health': '无法获取设备健康度数据'
        });
      }
    });
  },

  // 加载环境安全指数（单设备模式）
  loadSafetyIndex(deviceId) {
    this.setData({
      'loading.safety': true,
      'errors.safety': ''
    });

    wx.request({
      url: `${this.data.backendUrl}/api/intelligence/safety-index`,
      method: 'GET',
      timeout: 10000,
      data: { device_id: deviceId },
      success: (res) => {
        if (res.statusCode === 200 && res.data) {
          const safetyData = res.data;
          if (safetyData.error) {
            this.setData({
              'loading.safety': false,
              'errors.safety': safetyData.error
            });
          } else {
            let factors = [];
            if (safetyData.factors && typeof safetyData.factors === 'object') {
              factors = Object.entries(safetyData.factors).map(([key, value]) => ({
                name: this.getSafetyFactorDisplayName(key),
                value: value
              }));
            }

            const safetyLevel = safetyData.safety_level || 'unknown';
            const safetyColor = this.getSafetyColor(safetyLevel);
            this.setData({
              safetyIndex: {
                score: Math.round(safetyData.overall_safety_index || safetyData.safety_index || 0),
                level: safetyLevel,
                levelText: this.getSafetyLevelText(safetyLevel),
                color: safetyColor,
                backgroundColor: safetyLevel === 'safe' ? '#f6ffed' : safetyLevel === 'moderate' ? '#fffbe6' : '#fff2f0',
                factors: factors
              },
              'loading.safety': false
            });
          }
        }
      },
      fail: (err) => {
        console.error('环境安全指数加载失败:', err);
        this.setData({
          'loading.safety': false,
          'errors.safety': '无法获取环境安全指数数据'
        });
      }
    });
  },

  // 加载传感器统计分析（单设备模式）
  loadSensorStatistics(deviceId) {
    this.setData({
      'loading.statistics': true,
      'errors.statistics': ''
    });

    wx.request({
      url: `${this.data.backendUrl}/api/intelligence/analysis/${deviceId}`,
      method: 'GET',
      timeout: 10000,
      success: (res) => {
        if (res.statusCode === 200 && res.data) {
          const analysisData = res.data;
          let dataAnalysis = analysisData.data_analysis || {};
          let stats = dataAnalysis.statistics || {};

          this.setData({
            statistics: {
              flame: this.formatSensorStats(stats.flame),
              smoke: this.formatSensorStats(stats.smoke),
              temperature: this.formatSensorStats(stats.temperature),
              humidity: this.formatSensorStats(stats.humidity),
              lightLevel: this.formatSensorStats(stats.light_level)
            },
            'loading.statistics': false
          });
        }
      },
      fail: (err) => {
        console.error('传感器统计加载失败:', err);
        this.setData({
          'loading.statistics': false,
          'errors.statistics': '无法获取传感器统计数据'
        });
      }
    });
  },

  // 加载设备趋势（单设备模式）
  loadDeviceTrends(deviceId) {
    this.setData({
      'loading.trends': true,
      'errors.trends': ''
    });

    wx.request({
      url: `${this.data.backendUrl}/api/intelligence/trends/${deviceId}`,
      method: 'GET',
      timeout: 10000,
      success: (res) => {
        console.log('趋势数据响应:', res);
        if (res.statusCode === 200 && res.data) {
          try {
            const trends = res.data;
            this.setData({
              trendsData: trends,
              'loading.trends': false
            });
            this.updateTrendsChart(trends);
          } catch (error) {
            console.error('处理趋势数据失败:', error);
            this.setData({
              'loading.trends': false,
              'errors.trends': '数据处理异常: ' + error.message
            });
          }
        } else {
          this.setData({
            'loading.trends': false,
            'errors.trends': '返回数据格式错误'
          });
        }
      },
      fail: (err) => {
        console.error('设备趋势加载失败:', err);
        this.setData({
          'loading.trends': false,
          'errors.trends': '无法获取趋势数据'
        });
      }
    });
  },

  // 生成趋势数据
  generateTrendData(stats) {
    if (!stats) return [];
    const count = 24;
    const data = [];
    const min = stats.min || 0;
    const max = stats.max || 100;
    const avg = stats.mean || stats.avg || 50;

    for (let i = 0; i < count; i++) {
      // 简单模拟趋势数据
      const variation = (Math.random() - 0.5) * (max - min) * 0.3;
      data.push(Math.max(min, Math.min(max, avg + variation)));
    }

    return data;
  },

  // 生成时间标签
  generateTimeLabels(count) {
    const labels = [];
    const now = new Date();
    for (let i = count - 1; i >= 0; i--) {
      const time = new Date(now - i * 3600000);
      labels.push(`${time.getHours()}:00`);
    }
    return labels;
  },

  // 加载AI智能建议（单设备模式）
  loadAiSuggestions(deviceId) {
    this.setData({
      'loading.ai': true,
      'errors.ai': ''
    });

    wx.request({
      url: `${this.data.backendUrl}/api/intelligence/ai-suggestions/${deviceId}`,
      method: 'GET',
      timeout: 10000,
      success: (res) => {
        if (res.statusCode === 200 && res.data) {
          const aiData = res.data;
          let suggestions = [];

          if (aiData.ai_suggestions && aiData.ai_suggestions.suggestions) {
            suggestions = aiData.ai_suggestions.suggestions;
          }

          this.setData({
            aiSuggestions: suggestions,
            'loading.ai': false
          });
        }
      },
      fail: (err) => {
        console.error('AI建议加载失败:', err);
        this.setData({
          'loading.ai': false,
          'errors.ai': '无法获取AI智能建议'
        });
      }
    });
  },

  // 格式化传感器统计数据
  formatSensorStats(sensorStats) {
    if (!sensorStats) {
      return { avg: 0, min: 0, max: 0, trend: "stable" };
    }

    return {
      avg: Math.round(sensorStats.mean || sensorStats.avg || 0),
      min: Math.round(sensorStats.min || 0),
      max: Math.round(sensorStats.max || 0),
      trend: sensorStats.trend || "stable"
    };
  },

  // 获取健康状态
  getHealthStatus(score) {
    if (score >= 90) return 'excellent';
    if (score >= 70) return 'good';
    if (score >= 50) return 'moderate';
    return 'poor';
  },

  // 获取健康状态文本
  getHealthStatusText(status) {
    const statusMap = {
      'excellent': '优秀',
      'good': '良好',
      'moderate': '中等',
      'poor': '较差',
      'critical': '紧急',
      'insufficient_data': '数据不足',
      'unknown': '未知'
    };
    return statusMap[status] || '未知';
  },

  // 获取安全等级
  getSafetyLevel(score) {
    if (score >= 80) return 'very_safe';
    if (score >= 60) return 'safe';
    if (score >= 40) return 'moderate';
    return 'risky';
  },

  // 获取安全等级文本
  getSafetyLevelText(level) {
    const levelMap = {
      'very_safe': '非常安全',
      'safe': '安全',
      'moderate': '中等',
      'risky': '有风险',
      'dangerous': '危险',
      'unknown': '未知'
    };
    return levelMap[level] || '未知';
  },

  // 获取健康度颜色
  getHealthColor(score) {
    if (score >= 80) return '#52c41a';
    if (score >= 60) return '#faad14';
    if (score >= 40) return '#fa8c16';
    return '#ff4d4f';
  },

  // 获取安全指数颜色
  getSafetyColor(level) {
    const colorMap = {
      'very_safe': '#52c41a',
      'safe': '#52c41a',
      'moderate': '#faad14',
      'risky': '#fa8c16',
      'dangerous': '#ff4d4f'
    };
    return colorMap[level] || '#d9d9d9';
  },

  // 获取因子显示名称
  getFactorDisplayName(key) {
    const nameMap = {
      'data_frequency': '数据频率',
      'sensor_stability': '传感器稳定性',
      'communication_reliability': '通信可靠性',
      'environmental_normality': '环境正常性'
    };
    return nameMap[key] || key;
  },

  // 获取安全因子显示名称
  getSafetyFactorDisplayName(key) {
    const nameMap = {
      'temperature_safety': '温度安全',
      'humidity_safety': '湿度安全',
      'air_quality': '空气质量',
      'lighting_safety': '光照安全'
    };
    return nameMap[key] || key;
  },

  // 获取传感器显示名称
  getSensorDisplayName(sensor) {
    const nameMap = {
      'flame': '火焰',
      'smoke': '烟雾',
      'temperature': '温度',
      'humidity': '湿度',
      'light_level': '光照'
    };
    return nameMap[sensor] || sensor;
  },

  // 格式化时间
  formatTime(date) {
    const now = new Date(date);
    const year = now.getFullYear();
    const month = String(now.getMonth() + 1).padStart(2, '0');
    const day = String(now.getDate()).padStart(2, '0');
    const hour = String(now.getHours()).padStart(2, '0');
    const minute = String(now.getMinutes()).padStart(2, '0');
    const second = String(now.getSeconds()).padStart(2, '0');
    return `${year}-${month}-${day} ${hour}:${minute}:${second}`;
  },

  // 错误重试
  retryHealth() {
    if (this.data.currentDeviceId === 'all') {
      this.loadAllDevicesAnalysis();
    } else {
      this.loadDeviceHealth(this.data.currentDeviceId);
    }
  },

  retrySafety() {
    if (this.data.currentDeviceId === 'all') {
      this.loadAllDevicesAnalysis();
    } else {
      this.loadSafetyIndex(this.data.currentDeviceId);
    }
  },

  retryStatistics() {
    this.loadSensorStatistics(this.data.currentDeviceId);
  },

  retryTrends() {
    this.loadDeviceTrends(this.data.currentDeviceId);
  },

  retryAi() {
    if (this.data.currentDeviceId === 'all') {
      this.loadSystemRecommendations();
    } else {
      this.loadAiSuggestions(this.data.currentDeviceId);
    }
  }
});
