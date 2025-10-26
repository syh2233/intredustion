const echarts = require('../../components/ec-canvas/echarts');

// 兼容iOS的日期解析工具函数
function parseDateCompatible(timeStr) {
  if (!timeStr) return new Date();
  const compatibleStr = timeStr.replace(/-/g, "/");
  return new Date(compatibleStr);
}

Page({
  data: {
    ec: {
      temp: { lazyLoad: true },
      humidity: { lazyLoad: true },
      smoke: { lazyLoad: true },
      sound: { lazyLoad: true }
    },
    historyData: [],
    filteredData: [],
    activeFilter: 'all',
    hasData: false
  },

  chartInstances: {}, // 存储有效图表实例
  isChartsDisposed: false, // 标记图表是否已销毁（避免重复销毁）
  MAX_RECORD_COUNT: 10, // 常量：最大显示记录数（最新10条）

  onLoad() {
    this.loadHistoryData();
  },

  onShow() {
    // 页面重新显示时，重置销毁标记（避免返回页面后无法重新初始化）
    this.isChartsDisposed = false;
    this.loadHistoryData();
  },

  // 单独封装数据加载函数：加载+排序+筛选+截断10条
  loadHistoryData() {
    const savedHistory = wx.getStorageSync('historyData') || [];
    // 1. 按时间倒序排序（最新的记录排在最前）
    const sortedData = savedHistory.sort((a, b) => {
      return parseDateCompatible(b.time) - parseDateCompatible(a.time);
    });
    // 2. 先筛选数据，再截断为最新10条（确保筛选后仍只留10条）
    const filteredAndLimited = this.filterData(sortedData, this.data.activeFilter)
      .slice(0, this.MAX_RECORD_COUNT);
    
    this.setData({
      historyData: sortedData, // 保留全部历史数据（用于筛选）
      filteredData: filteredAndLimited, // 筛选后且截断的10条数据
      hasData: filteredAndLimited.length > 0 // 无数据判断基于截断后的数据
    }, () => {
      this.initOrUpdateCharts();
    });
  },

  // 初始化或更新图表
  initOrUpdateCharts() {
    // 已销毁则不执行操作
    if (this.isChartsDisposed) return;
    
    if (!this.data.hasData) {
      this.clearAllCharts();
      return;
    }

    if (Object.keys(this.chartInstances).length === 0) {
      this.initAllCharts();
    } else {
      this.updateAllCharts();
    }
  },

  onReady() {
    setTimeout(() => {
      this.initOrUpdateCharts();
    }, 500);
  },

  initAllCharts() {
    if (this.isChartsDisposed || !this.data.hasData) return;

    this.initChart('tempChart', 'temperature', {
      color: '#f53f3f',
      unit: '℃',
      yMin: 10,
      yMax: 65
    });

    this.initChart('humidityChart', 'humidity', {
      color: '#1677ff',
      unit: '%',
      yMin: 15,
      yMax: 85
    });

    this.initChart('smokeChart', 'smoke', {
      color: '#722ed1',
      unit: 'ppm',
      yMin: 50,
      yMax: 850
    });

    this.initChart('soundChart', 'sound', {
      color: '#ff7d00',
      unit: 'dB',
      yMin: 10,
      yMax: 125
    });
  },

  initChart(canvasId, dataKey, config) {
    if (this.isChartsDisposed) return;

    const { color, unit, yMin, yMax } = config;
    const { filteredData } = this.data; // 使用截断后的10条数据

    const categories = filteredData.map(item => item.time.split(' ')[1]);
    const values = filteredData.map(item => item[dataKey]);

    const ecComponent = this.selectComponent(`#${canvasId}`);
    if (!ecComponent) {
      console.error(`未找到ID为${canvasId}的图表组件`);
      return;
    }

    ecComponent.init((canvas, width, height) => {
      // 初始化前检查是否已销毁
      if (this.isChartsDisposed) return;
      
      const chart = echarts.init(canvas, null, { width, height });
      canvas.setChart(chart);

      const option = {
        tooltip: {
          trigger: 'axis',
          axisPointer: { type: 'line' },
          formatter: (params) => {
            const time = filteredData[params[0].dataIndex].time;
            return `${time}<br/>${this.getSeriesName(dataKey)}: ${params[0].value}${unit}`;
          }
        },
        grid: {
          left: '3%',
          right: '4%',
          bottom: '15%',
          containLabel: true
        },
        xAxis: {
          type: 'category',
          data: categories,
          axisLabel: {
            rotate: 45,
            fontSize: 10,
            interval: 0
          }
        },
        yAxis: {
          type: 'value',
          min: yMin,
          max: yMax,
          axisLabel: {
            formatter: `{value}${unit}`
          },
          splitLine: {
            lineStyle: { type: 'dashed' }
          }
        },
        series: [
          {
            name: this.getSeriesName(dataKey),
            type: 'line',
            data: values,
            lineStyle: { color: color, width: 2 },
            itemStyle: {
              color: color,
              borderRadius: 4,
              borderWidth: 2,
              borderColor: 'white'
            },
            symbol: 'circle',
            symbolSize: 6,
            smooth: true,
            markLine: {
              data: this.getThresholdLine(dataKey)
            }
          }
        ]
      };

      chart.setOption(option);
      this.chartInstances[canvasId] = chart;
      return chart;
    });
  },

  getSeriesName(key) {
    const nameMap = {
      temperature: '温度',
      humidity: '湿度',
      smoke: '烟雾浓度',
      sound: '声音'
    };
    return nameMap[key] || key;
  },

  getThresholdLine(key) {
    const tempThreshold = wx.getStorageSync('tempThreshold') || 50;
    const smokeThreshold = wx.getStorageSync('smokeThreshold') || 600;
    
    const thresholds = {
      temperature: { value: tempThreshold, name: '温度阈值' },
      smoke: { value: smokeThreshold, name: '烟雾阈值' },
      sound: { value: 70, name: '声音阈值' },
      humidity: { value: 80, name: '湿度上限' }
    };

    if (thresholds[key]) {
      return [
        {
          name: thresholds[key].name,
          yAxis: thresholds[key].value,
          lineStyle: { color: '#f53f3f', type: 'dashed' },
          label: { show: true, formatter: `${thresholds[key].name}: ${thresholds[key].value}` }
        }
      ];
    }
    return [];
  },

  // 切换筛选类型：筛选后自动截断为10条
  changeFilter(e) {
    const filterType = e.currentTarget.dataset.type;
    // 基于全部历史数据筛选，再截断为10条
    const filteredAndLimited = this.filterData(this.data.historyData, filterType)
      .slice(0, this.MAX_RECORD_COUNT);
    
    this.setData({
      activeFilter: filterType,
      filteredData: filteredAndLimited,
      hasData: filteredAndLimited.length > 0
    }, () => {
      this.updateAllCharts();
    });
  },

  // 安全更新图表数据
  updateAllCharts() {
    if (this.isChartsDisposed || !this.data.hasData) {
      this.clearAllCharts();
      return;
    }

    const { filteredData } = this.data; // 使用截断后的10条数据
    const categories = filteredData.map(item => item.time.split(' ')[1]);

    this.updateChartData('tempChart', filteredData.map(item => item.temperature), categories);
    this.updateChartData('humidityChart', filteredData.map(item => item.humidity), categories);
    this.updateChartData('smokeChart', filteredData.map(item => item.smoke), categories);
    this.updateChartData('soundChart', filteredData.map(item => item.sound), categories);
  },

  updateChartData(canvasId, values, categories) {
    if (this.isChartsDisposed) return;

    const chart = this.chartInstances[canvasId];
    if (chart && typeof chart.setOption === 'function') {
      chart.setOption(this.getChartOption(canvasId, values, categories));
    } else {
      const dataKeyMap = {
        'tempChart': 'temperature',
        'humidityChart': 'humidity',
        'smokeChart': 'smoke',
        'soundChart': 'sound'
      };
      const configMap = {
        'tempChart': { color: '#f53f3f', unit: '℃', yMin: 10, yMax: 65 },
        'humidityChart': { color: '#1677ff', unit: '%', yMin: 15, yMax: 85 },
        'smokeChart': { color: '#722ed1', unit: 'ppm', yMin: 50, yMax: 850 },
        'soundChart': { color: '#ff7d00', unit: 'dB', yMin: 10, yMax: 125 }
      };
      this.initChart(canvasId, dataKeyMap[canvasId], configMap[canvasId]);
    }
  },

  // 生成图表完整配置
  getChartOption(canvasId, values, categories) {
    const dataKeyMap = {
      'tempChart': 'temperature',
      'humidityChart': 'humidity',
      'smokeChart': 'smoke',
      'soundChart': 'sound'
    };
    const configMap = {
      'tempChart': { color: '#f53f3f', unit: '℃', yMin: 10, yMax: 65 },
      'humidityChart': { color: '#1677ff', unit: '%', yMin: 15, yMax: 85 },
      'smokeChart': { color: '#722ed1', unit: 'ppm', yMin: 50, yMax: 850 },
      'soundChart': { color: '#ff7d00', unit: 'dB', yMin: 10, yMax: 125 }
    };

    const dataKey = dataKeyMap[canvasId];
    const config = configMap[canvasId];
    const { color, unit, yMin, yMax } = config;

    return {
      tooltip: {
        trigger: 'axis',
        axisPointer: { type: 'line' },
        formatter: (params) => {
          const time = this.data.filteredData[params[0].dataIndex].time;
          return `${time}<br/>${this.getSeriesName(dataKey)}: ${params[0].value}${unit}`;
        }
      },
      grid: {
        left: '3%',
        right: '4%',
        bottom: '15%',
        containLabel: true
      },
      xAxis: {
        type: 'category',
        data: categories,
        axisLabel: {
          rotate: 45,
          fontSize: 10,
          interval: 0
        }
      },
      yAxis: {
        type: 'value',
        min: yMin,
        max: yMax,
        axisLabel: {
          formatter: `{value}${unit}`
        },
        splitLine: {
          lineStyle: { type: 'dashed' }
        }
      },
      series: [
        {
          name: this.getSeriesName(dataKey),
          type: 'line',
          data: values,
          lineStyle: { color: color, width: 2 },
          itemStyle: {
            color: color,
            borderRadius: 4,
            borderWidth: 2,
            borderColor: 'white'
          },
          symbol: 'circle',
          symbolSize: 6,
          smooth: true,
          markLine: {
            data: this.getThresholdLine(dataKey)
          }
        }
      ]
    };
  },

  // 刷新数据按钮逻辑
  refreshData() {
    if (this.isChartsDisposed) return;

    wx.showLoading({ title: '刷新中...' });
    this.loadHistoryData(); // 刷新时重新执行加载+截断逻辑
    wx.hideLoading();
    wx.showToast({
      title: '已更新最新数据',
      icon: 'success',
      duration: 1500
    });
  },

  // 清空图表（安全版本）
  clearAllCharts() {
    if (this.isChartsDisposed) return;

    Object.values(this.chartInstances).forEach(chart => {
      // 检查实例是否有效且存在 dispose 方法
      if (chart && typeof chart.dispose === 'function') {
        try {
          chart.dispose();
        } catch (e) {
          console.warn('销毁图表实例失败:', e);
        }
      }
    });
    // 清空实例缓存
    this.chartInstances = {};
  },

  filterData(data, filterType) {
    const now = new Date();
    const todayStart = new Date(now.getFullYear(), now.getMonth(), now.getDate()).getTime();
    const sevenDaysAgo = todayStart - 7 * 24 * 60 * 60 * 1000;

    switch (filterType) {
      case 'today':
        return data.filter(item => parseDateCompatible(item.time).getTime() >= todayStart);
      case '7days':
        return data.filter(item => parseDateCompatible(item.time).getTime() >= sevenDaysAgo);
      default:
        return data;
    }
  },

  goBack() {
    wx.navigateBack();
  },

  // 页面卸载：安全销毁图表实例
  onUnload() {
    // 标记已销毁，避免后续操作触发异常
    this.isChartsDisposed = true;
    this.clearAllCharts();
  }
})