Page({
  data: {
    // 后端API配置
    backendUrl: "https://icstop1syh.cpolar.top", // Python后端地址（cpolar内网穿透）

    // 光照传感器数据
    lightValue: 0,           // 当前光照值
    lightUnit: "lux",         // 光照单位
    isOnline: true,           // 设备在线状态

    // 光照控制参数
    lightThreshold: 300,     // 光照阈值
    autoControl: false,       // 自动控制开关
    currentStatus: "正常",    // 当前状态描述

    // 界面状态
    loading: false,
    lastUpdate: "",

    // 光照等级描述
    lightLevels: [
      { max: 50, label: "非常暗", icon: "🌙", color: "#2c3e50" },
      { max: 200, label: "暗", icon: "🌑", color: "#34495e" },
      { max: 500, label: "正常", icon: "⛅", color: "#3498db" },
      { max: 1000, label: "明亮", icon: "☀️", color: "#f39c12" },
      { max: 10000, label: "很亮", icon: "🌞", color: "#e67e22" },
      { max: Infinity, label: "极亮", icon: "🔆", color: "#e74c3c" }
    ],

    // 图表数据
    chartData: [],
    timeLabels: []
  },

  onLoad() {
    this.loadLocalSettings();
    this.initChart();
    this.startDataRefresh();
  },

  /**
   * 加载本地设置
   */
  loadLocalSettings() {
    const savedThreshold = wx.getStorageSync('lightThreshold');
    const savedAutoControl = wx.getStorageSync('lightAutoControl');

    if (savedThreshold) {
      this.setData({ lightThreshold: savedThreshold });
    }
    if (savedAutoControl !== undefined) {
      this.setData({ autoControl: savedAutoControl });
    }
  },

  /**
   * 初始化图表
   */
  initChart() {
    const chartCtx = wx.createCanvasContext('lightChart', this);
    this.setData({ chartCtx });
    this.updateChart();
  },

  /**
   * 启动数据刷新
   */
  startDataRefresh() {
    const that = this;

    // 立即执行一次刷新
    this.fetchLightData();

    // 启动5秒轮询
    const interval = setInterval(() => {
      that.fetchLightData();
    }, 5000); // 5秒 = 5000毫秒

    this.setData({ refreshInterval: interval });
  },

  /**
   * 从Python后端获取光照数据
   */
  fetchLightData() {
    console.log("从后端获取光照数据...");
    const that = this;
    const { backendUrl } = this.data;

    this.setData({ loading: true });

    wx.request({
      url: `${backendUrl}/api/devices`,
      method: 'GET',
      header: {
        'content-type': 'application/json'
      },
      success: function (res) {
        console.log("后端光照数据获取成功：", res.data);

        if (res.statusCode === 200 && res.data && res.data.length > 0) {
          // 获取第一个设备的数据
          const deviceData = res.data[0];
          const lightValue = deviceData.light_level || 0;

          that.updateLightData(lightValue);
          that.setData({
            loading: false,
            isOnline: true,  // 与主页一致，总是显示在线
            currentStatus: "数据已更新"
          });
        } else {
          console.warn("后端返回光照数据为空");
          that.setData({
            loading: false,
            isOnline: true,  // 与主页一致，即使没数据也显示在线
            currentStatus: "暂无数据"
          });
        }
      },
      fail: function (err) {
        console.error("获取后端光照数据失败：", err);
        that.setData({
          loading: false,
          isOnline: false,  // 只有网络失败时才显示离线
          currentStatus: "连接失败"
        });
      }
    });
  },

  /**
   * 更新光照数据
   */
  updateLightData(value) {
    const now = new Date();
    const timeStr = `${now.getHours().toString().padStart(2, '0')}:${now.getMinutes().toString().padStart(2, '0')}:${now.getSeconds().toString().padStart(2, '0')}`;

    // 获取光照等级
    const level = this.getLightLevel(value);

    // 检查状态
    let status = "正常";
    if (value < this.data.lightThreshold) {
      status = "光照不足";
    }

    // 更新图表数据
    const newChartData = [...this.data.chartData, value].slice(-20); // 保留最近20个数据点
    const newTimeLabels = [...this.data.timeLabels, timeStr].slice(-20);

    this.setData({
      lightValue: value,
      currentStatus: status,
      lastUpdate: timeStr,
      chartData: newChartData,
      timeLabels: newTimeLabels,
      lightLevel: level
    });

    // 自动控制逻辑
    if (this.data.autoControl) {
      this.handleAutoControl(value);
    }

    // 更新图表
    this.updateChart();
  },

  /**
   * 获取光照等级
   */
  getLightLevel(value) {
    return this.data.lightLevels.find(level => value <= level.max);
  },

  /**
   * 自动控制逻辑
   */
  handleAutoControl(value) {
    if (value < this.data.lightThreshold) {
      // 光照不足，可以在这里添加自动开灯等逻辑
      console.log("光照不足，建议开启照明");
    }
  },

  /**
   * 更新图表
   */
  updateChart() {
    const { chartCtx, chartData, timeLabels } = this.data;

    if (!chartCtx || chartData.length === 0) return;

    const width = 300;
    const height = 200;
    const padding = 40;
    const chartWidth = width - padding * 2;
    const chartHeight = height - padding * 2;

    // 清空画布
    chartCtx.clearRect(0, 0, width, height);

    // 找出最大值用于缩放
    const maxValue = Math.max(...chartData, 1000);

    // 绘制坐标轴
    chartCtx.setStrokeStyle("#e0e0e0");
    chartCtx.setLineWidth(1);
    chartCtx.beginPath();
    chartCtx.moveTo(padding, padding);
    chartCtx.lineTo(padding, height - padding);
    chartCtx.lineTo(width - padding, height - padding);
    chartCtx.stroke();

    // 绘制数据线
    if (chartData.length > 1) {
      chartCtx.setStrokeStyle("#3498db");
      chartCtx.setLineWidth(2);
      chartCtx.beginPath();

      chartData.forEach((value, index) => {
        const x = padding + (index / (chartData.length - 1)) * chartWidth;
        const y = height - padding - (value / maxValue) * chartHeight;

        if (index === 0) {
          chartCtx.moveTo(x, y);
        } else {
          chartCtx.lineTo(x, y);
        }
      });

      chartCtx.stroke();

      // 绘制数据点
      chartData.forEach((value, index) => {
        const x = padding + (index / (chartData.length - 1)) * chartWidth;
        const y = height - padding - (value / maxValue) * chartHeight;

        chartCtx.setFillStyle("#3498db");
        chartCtx.beginPath();
        chartCtx.arc(x, y, 3, 0, 2 * Math.PI);
        chartCtx.fill();
      });
    }

    chartCtx.draw();
  },

  /**
   * 手动刷新数据
   */
  refreshData() {
    this.fetchLightData();
  },

  /**
   * 页面隐藏：暂停轮询
   */
  onHide() {
    if (this.data.refreshInterval) {
      clearInterval(this.data.refreshInterval);
      this.setData({ refreshInterval: null });
      console.log("光照页面隐藏，暂停数据轮询");
    }
  },

  /**
   * 页面重新显示：重启轮询
   */
  onShow() {
    if (!this.data.refreshInterval) {
      this.startDataRefresh();
      console.log("光照页面显示，重启数据轮询");
    }
  },

  /**
   * 页面卸载：清除定时器
   */
  onUnload() {
    if (this.data.refreshInterval) clearInterval(this.data.refreshInterval);
    console.log("光照页面卸载，清除定时器");
  },

  /**
   * 设置阈值
   */
  setThreshold() {
    const that = this;
    wx.showModal({
      title: '设置光照阈值',
      content: `当前阈值：${this.data.lightThreshold} lux`,
      editable: true,
      placeholderText: '请输入新的阈值',
      success(res) {
        if (res.confirm && res.content) {
          const newThreshold = parseInt(res.content);
          if (!isNaN(newThreshold) && newThreshold > 0) {
            that.setData({ lightThreshold: newThreshold });
            wx.setStorageSync('lightThreshold', newThreshold);
            wx.showToast({
              title: '设置成功',
              icon: 'success'
            });
            // 重新检查状态
            that.updateLightData(that.data.lightValue);
          } else {
            wx.showToast({
              title: '请输入有效数值',
              icon: 'error'
            });
          }
        }
      }
    });
  },

  /**
   * 切换自动控制
   */
  toggleAutoControl() {
    const newAutoControl = !this.data.autoControl;
    this.setData({ autoControl: newAutoControl });
    wx.setStorageSync('lightAutoControl', newAutoControl);

    wx.showToast({
      title: newAutoControl ? '自动控制已开启' : '自动控制已关闭',
      icon: 'success'
    });
  },

  /**
   * 返回首页
   */
  goBack() {
    wx.navigateBack();
  },

  });