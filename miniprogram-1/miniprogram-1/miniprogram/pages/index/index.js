Page({
  data: {
    // 基本信息
    deviceName: "智能火灾预警设备",
    isOnline: true,
    overallStatus: "normal", // normal, warning, alarm
    lastUpdateText: "刚刚更新",

    // 传感器数据
    temperature: 25.0,
    humidity: 45.0,
    smoke: 300,
    flame: false,
    light: 350,

    // 传感器状态 (用于样式)
    tempStatus: "normal",
    smokeStatus: "normal",
    lightStatus: "normal",

    // 报警阈值
    tempThreshold: 40,
    smokeThreshold: 1000,

    // 配置
    backendUrl: "http://192.168.31.193:5000",
    refreshInterval: null,
    result: "等待连接后端...",
    alarmRecords: [],

    // 报警状态
    lastAlarmStatus: {
      temp: false,
      smoke: false,
      flame: false,
      light: false
    },

    // 设备控制状态
    servo: false,  // 舵机状态
    servoRunning: false  // 舵机是否正在运行
  },

  onLoad() {
    console.log('页面加载开始...');

    this.setData({
      light: 0,
      isOnline: true,
      result: '正在初始化...'
    });

    this.loadLocalStorage();
    this.startDataRefresh();
    this.fetchSensorData();

    // 延迟检查火灾报警，确保数据加载完成
    setTimeout(() => {
      this.checkFireAlarmOnLoad();
    }, 2000);
  },

  // 页面加载时检查火灾报警
  checkFireAlarmOnLoad() {
    const { flame } = this.data;
    if (flame) {
      console.log('页面加载时检测到火灾报警');
      this.showFireAlarmModal();
    }
  },

  // 启动数据刷新
  startDataRefresh() {
    const that = this;

    if (this.data.refreshInterval) {
      clearInterval(this.data.refreshInterval);
    }

    this.fetchSensorData();

    const interval = setInterval(() => {
      that.fetchSensorData();
    }, 1500); // 改为1.5秒刷新一次，比ESP32发送频率稍快，确保及时响应

    this.setData({ refreshInterval: interval });
  },

  // 从后端获取传感器数据
  fetchSensorData() {
    const that = this;
    const { backendUrl } = this.data;

    wx.request({
      url: `${backendUrl}/api/devices`,
      method: 'GET',
      header: {
        'content-type': 'application/json'
      },
      success: function (res) {
        console.log("后端数据获取成功：", res.data);

        try {
          if (res.statusCode === 200 && res.data && res.data.length > 0) {
            const deviceData = res.data[0];

            // 计算各传感器状态
            const tempValue = deviceData.temperature || 0;
            const smokeValue = deviceData.smoke_level || 0;
            const tempThreshold = that.data.tempThreshold;

            // 温度逻辑：值越高越危险（与服务器保持一致：>40警报，>35警告）
            const tempStatus = tempValue > 40 ? 'alarm' : (tempValue > 35 ? 'warning' : 'normal');

            // 烟雾逻辑：值越低越危险（MQ2传感器特性，与服务器保持一致）
            const smokeStatus = smokeValue < 1000 ? 'alarm' : (smokeValue < 1300 ? 'warning' : 'normal');

            // 光照逻辑：值越高越危险（与服务器保持一致）
            const lightValue = deviceData.light_level || 0;
            const lightStatus = lightValue > 130 ? 'alarm' : (lightValue > 120 ? 'warning' : 'normal');

            const updateData = {
              temperature: tempValue,
              humidity: deviceData.humidity || 0,
              smoke: smokeValue,
              light: deviceData.light_level || 0,
              flame: deviceData.flame < 500, // 火焰值小于500表示检测到火焰
              tempStatus: tempStatus,
              smokeStatus: smokeStatus,
              lightStatus: lightStatus,
              isOnline: true, // 有数据说明设备在线
              overallStatus: deviceData.status === '火警' ? 'alarm' : deviceData.status === '警告' ? 'warning' : 'normal',
              result: `数据刷新成功（${new Date().toLocaleTimeString()}）`
            };

            console.log('准备更新的数据:', updateData);
            that.setData(updateData);
            that.checkAlarmStatus();
            that.recordHistoryData();
          } else {
            console.warn("后端返回数据为空");
            const defaultData = {
              temperature: 0,
              humidity: 0,
              smoke: 0,
              light: 0,
              flame: false,
              tempStatus: 'normal',
              smokeStatus: 'normal',
              lightStatus: 'normal',
              isOnline: false, // 没有数据时也显示离线
              overallStatus: 'normal',
              result: "暂无设备数据"
            };
            that.setData(defaultData);
          }
        } catch (error) {
          console.error('数据处理异常:', error);
          that.setData({
            temperature: 0,
            humidity: 0,
            smoke: 0,
            light: 0,
            flame: false,
            tempStatus: 'normal',
            smokeStatus: 'normal',
            lightStatus: 'normal',
            isOnline: false, // 数据处理异常时也显示离线
            overallStatus: 'normal',
            result: "数据处理异常"
          });
        }
      },
      fail: function (err) {
        console.error("获取后端数据失败：", err);
        const failData = {
          temperature: 0,
          humidity: 0,
          smoke: 0,
          light: 0,
          flame: false,
          tempStatus: 'normal',
          smokeStatus: 'normal',
          lightStatus: 'normal',
          isOnline: false, // 网络连接失败时也显示离线
          overallStatus: 'normal',
          result: "连接后端失败"
        };
        that.setData(failData);
      }
    });
  },

  // 检查报警状态并显示弹窗
  checkAlarmStatus() {
    const { tempStatus, smokeStatus, lightStatus, flame } = this.data;

    // 检查各传感器是否报警
    const currentAlarmStatus = {
      temp: tempStatus === 'alarm',
      smoke: smokeStatus === 'alarm',
      flame: flame === true,
      light: lightStatus === 'alarm'
    };

    // 火灾报警：检测到火焰时立即弹窗，持续提醒
    if (currentAlarmStatus.flame) {
      this.showFireAlarmModal();
      return; // 火灾报警优先，不处理其他报警
    }

    // 检查是否有新的非火灾报警
    const hasNewAlarm = (
      currentAlarmStatus.temp ||
      currentAlarmStatus.smoke ||
      currentAlarmStatus.light
    );

    if (hasNewAlarm) {
      // 构建报警消息
      const alarmMessages = [];
      if (currentAlarmStatus.temp) alarmMessages.push('温度过高');
      if (currentAlarmStatus.smoke) alarmMessages.push('烟雾浓度过高');
      if (currentAlarmStatus.light) alarmMessages.push('光照过强');

      if (alarmMessages.length > 0) {
        this.showAlarmModal(alarmMessages);
      }
    }
  },

  // 显示火灾报警弹窗（紧急且持续）
  showFireAlarmModal() {
    // 强震动提醒
    wx.vibrateLong();

    wx.showModal({
      title: '🔥🔥🔥 火灾警报 🔥🔥🔥',
      content: '检测到火焰！\n\n立即疏散！\n立即拨打119！\n\n这是紧急火灾报警！',
      showCancel: false,
      confirmText: '关闭警报',
      confirmColor: '#f53f3f',
      success: (res) => {
        if (res.confirm) {
          console.log('用户确认火灾报警弹窗');
          // 再次震动提醒
          wx.vibrateLong();

          // 1秒后再次检查火焰状态，如果仍然检测到火焰就继续弹窗
          setTimeout(() => {
            if (this.data.flame) {
              this.showFireAlarmModal();
            }
          }, 1000);
        }
      }
    });
  },

  // 显示普通报警弹窗
  showAlarmModal(alarmMessages) {
    const message = alarmMessages.join('、');
    wx.showModal({
      title: '⚠️ 安全报警',
      content: `检测到异常：${message}！\n请立即检查环境状况！`,
      showCancel: false,
      confirmText: '知道了',
      confirmColor: '#ff7d00',
      success: (res) => {
        if (res.confirm) {
          console.log('用户确认报警弹窗');
          // 普通报警使用短震动
          wx.vibrateShort();
        }
      }
    });
  },

  // 检查状态
  checkStatus() {
    const { temperature, humidity, smoke, tempThreshold, smokeThreshold } = this.data;

    // 简单的报警判断
    if (temperature > tempThreshold || smoke < smokeThreshold) {
      console.log('检测到报警状态');
      this.addAlarmRecord('高温', temperature > tempThreshold ? '温度过高' : '烟雾过浓');
    }
  },

  // 添加报警记录
  addAlarmRecord(type, message) {
    const alarmRecords = this.data.alarmRecords || [];
    alarmRecords.unshift({
      id: Date.now(),
      type: type,
      message: message,
      time: new Date().toLocaleString(),
      handled: false
    });

    this.setData({
      alarmRecords: alarmRecords,
      unhandledCount: alarmRecords.filter(r => !r.handled).length
    });

    wx.setStorageSync('alarmRecords', alarmRecords);
  },

  // 记录历史数据
  recordHistoryData() {
    const historyData = this.data.historyData || [];
    const newData = {
      id: Date.now(),
      temperature: this.data.temperature,
      humidity: this.data.humidity,
      smoke: this.data.smoke,
      flame: this.data.flame,
      light: this.data.light,
      time: new Date().toLocaleString()
    };

    historyData.unshift(newData);

    if (historyData.length > 100) {
      historyData = historyData.slice(0, 100);
    }

    this.setData({ historyData });
    wx.setStorageSync('historyData', historyData);
  },

  // 加载本地存储
  loadLocalStorage() {
    try {
      const savedTemp = wx.getStorageSync('savedTemp', 40);
      const savedSmoke = wx.getStorageSync('savedSmoke', 1000);
      const alarmRecords = wx.getStorageSync('alarmRecords', []);
      const historyCount = wx.getStorageSync('historyCount', 100);

      this.setData({
        tempThreshold: savedTemp,
        smokeThreshold: savedSmoke,
        alarmRecords: alarmRecords,
        unhandledCount: alarmRecords.filter(r => !r.handled).length
      });

      console.log('加载本地存储:', {
        savedTemp,
        savedSmoke,
        alarmRecordsCount: alarmRecords.length,
        historyCount
      });
    } catch (error) {
      console.error('加载本地存储失败:', error);
    }
  },

  onUnload() {
    if (this.data.refreshInterval) {
      clearInterval(this.data.refreshInterval);
    }
    console.log("页面卸载，清除定时器");
  },

  // 跳转到报警详情页面
  goToAlarmDetails() {
    wx.navigateTo({
      url: '/pages/alarm/alarm'
    });
  },

  // 跳转到历史数据页面
  goToHistory() {
    wx.navigateTo({
      url: '/pages/history/history'
    });
  },

  // 跳转到阈值设置页面
  goToSettings() {
    wx.navigateTo({
      url: '/pages/settings/settings'
    });
  },

  // 跳转到从机数据页面
  goToSlaveData() {
    wx.navigateTo({
      url: '/pages/slaveData/slaveData'
    });
  },

  // 控制舵机
  controlServo() {
    const that = this;
    const { servo } = this.data;

    // 防止重复点击
    if (that.data.servoRunning) {
      console.log('舵机正在运行，请稍候');
      return;
    }

    // 设置运行状态
    that.setData({
      servoRunning: true
    });

    // 构建控制命令
    const action = servo ? 'off' : 'on';
    const controlData = {
      device: 'servo',
      action: action,
      timestamp: Date.now()
    };

    console.log('发送舵机控制命令:', controlData);

    // 通过舵机控制API发送命令到ESP32
    wx.request({
      url: 'http://192.168.31.193:5000/api/servo/control',
      method: 'POST',
      header: {
        'content-type': 'application/json'
      },
      data: {
        action: action
      },
      success: function(res) {
        console.log('舵机控制命令发送成功:', res.data);

        // 更新舵机状态
        that.setData({
          servo: !servo,
          servoRunning: false
        });

        // 显示提示
        wx.showToast({
          title: servo ? '舵机已关闭' : '舵机已打开',
          icon: 'success',
          duration: 2000
        });

        // 震动反馈
        wx.vibrateShort();
      },
      fail: function(err) {
        console.error('舵机控制命令发送失败:', err);

        // 重置运行状态
        that.setData({
          servoRunning: false
        });

        // 显示错误提示
        wx.showToast({
          title: '控制失败',
          icon: 'error',
          duration: 2000
        });
      }
    });
  }
});