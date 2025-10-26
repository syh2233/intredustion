Page({
  data: {
    // 从机设备数据字段
    deviceName: "从机设备",
    isOnline: true,
    smoke: 1200,  // 从机烟雾传感器初始值
    flame: false,  // 从机火焰传感器初始值
    smokeStatus: "normal",  // 烟雾状态（用于样式）

    // 与主机复用的轮询配置
    refreshInterval: null,
    result: "等待初始化..."
  },

  onLoad() {
    console.log('从机页面加载');
    this.startDataRefresh();
    this.fetchSlaveData();
  },

  /**
   * 启动1.5秒轮询（与主机一致的刷新频率）
   */
  startDataRefresh() {
    const that = this;

    // 清除旧定时器避免重复
    if (this.data.refreshInterval) {
      clearInterval(this.data.refreshInterval);
    }

    // 立即执行一次刷新
    this.fetchSlaveData();

    // 启动轮询
    const interval = setInterval(() => {
      that.fetchSlaveData();
    }, 1500); // 1.5秒刷新，与主机保持一致

    this.setData({ refreshInterval: interval });
  },

  /**
   * 获取从机设备数据
   */
  fetchSlaveData() {
    const that = this;

    wx.request({
      url: 'http://192.168.31.193:5000/api/slaves',
      method: 'GET',
      header: {
        'content-type': 'application/json'
      },
      success: function (res) {
        console.log("从机数据获取成功：", res.data);

        try {
          if (res.statusCode === 200 && res.data && res.data.length > 0) {
            const slaveData = res.data[0]; // 获取第一个从机数据
            const latestData = slaveData.latest_data || {};

            // 烟雾逻辑：值越低越危险（与服务器保持一致）
            const smokeValue = latestData.smoke || 1200;
            const smokeStatus = smokeValue < 1000 ? 'alarm' : (smokeValue < 1300 ? 'warning' : 'normal');

            // 火焰逻辑：值越低越危险
            const flameValue = latestData.flame || 1500;
            const flameDetected = flameValue < 500;

            const updateData = {
              smoke: smokeValue,
              flame: flameDetected,
              smokeStatus: smokeStatus,
              isOnline: true,
              overallStatus: flameDetected ? 'alarm' : smokeStatus === 'alarm' ? 'alarm' : smokeStatus === 'warning' ? 'warning' : 'normal',
              result: `从机数据刷新成功（${new Date().toLocaleTimeString()}）`
            };

            console.log('从机准备更新的数据:', updateData);
            that.setData(updateData);
          } else {
            console.warn("从机数据为空");
            that.setData({
              smoke: 0,
              flame: false,
              smokeStatus: 'normal',
              isOnline: false,
              overallStatus: 'normal',
              result: "暂无从机数据"
            });
          }
        } catch (error) {
          console.error('从机数据处理异常:', error);
          that.setData({
            smoke: 0,
            flame: false,
            smokeStatus: 'normal',
            isOnline: false,
            overallStatus: 'normal',
            result: "数据处理异常"
          });
        }
      },
      fail: function (err) {
        console.error("获取从机数据失败：", err);
        that.setData({
          smoke: 0,
          flame: false,
          smokeStatus: 'normal',
          isOnline: false,
          overallStatus: 'normal',
          result: "连接服务器失败"
        });
      }
    });
  },

  /**
   * 复用主机的Token获取逻辑（直接调用主机的gettoken接口逻辑）
   */
  getTokenFromHost() {
    const that = this;

    wx.request({
      // 与主机完全一致的Token请求地址
      url: 'https://iam.cn-north-4.myhuaweicloud.com/v3/auth/tokens',
      data: {
        "auth": {
          "identity": {
            "methods": ["password"],
            "password": {
              "user": {
                "name": "zzb",
                "password": "$z02z10b11$",
                "domain": { "name": "aao_1011" }
              }
            }
          },
          "scope": { "project": { "name": "cn-north-4" } }
        }
      },
      method: 'POST',
      header: { 'content-type': 'application/json' },
      success: function (res) {
        const token = res.header['X-Subject-Token'] || "";
        if (token) {
          that.setData({
            token: token,
            tokenExpired: false,
            result: "Token刷新成功，恢复数据更新"
          });
          wx.setStorageSync('token', token); // 同步更新缓存供主机使用
        } else {
          that.setData({ result: "Token获取失败，10秒后重试" });
          setTimeout(() => that.getTokenFromHost(), 10000);
        }
      },
      fail: function (err) {
        console.error("从机获取Token失败：", err);
        that.setData({ result: "网络异常，Token获取失败" });
        setTimeout(() => that.getTokenFromHost(), 10000);
      }
    });
  },

  /**
   * 获取设备影子（与主机完全相同的接口，读取同一设备数据）
   */
  getDeviceShadow() {
    console.log("从机页面：获取设备影子数据");
    const that = this;
    const token = this.data.token;

    if (!token) {
      this.setData({ tokenExpired: true });
      return;
    }

    wx.request({
      // 与主机完全一致的设备影子接口URL
      url: 'https://9f951dc858.st1.iotda-app.cn-north-4.myhuaweicloud.com:443/v5/iot/3a2a4b1222734297b2d41eaa7962f4d0/devices/68cdfe22d582f20018510931_0742/shadow',
      method: 'GET',
      header: {
        'content-type': 'application/json',
        'X-Auth-Token': token
      },
      success: function (res) {
        console.log("从机获取影子成功：", res.data);

        // 与主机一致的数据解析逻辑
        const shadowData = res.data.shadow[0].reported.properties || {};
        const temperature = shadowData.temperature || 0;
        const humidity = shadowData.humidity || 0;
        const smoke = shadowData.smoke_value || 0;
        const sound = shadowData.sound_value || 0;
        const flame = shadowData.flame_value < 10 ? true : false;

        // 更新从机页面数据
        that.setData({
          temperature: parseFloat(temperature.toFixed(1)),
          humidity: parseFloat(humidity.toFixed(1)),
          smoke: smoke,
          sound: sound,
          flame: flame,
          isOnline: true,
          result: `数据刷新成功（${new Date().toLocaleTimeString()}）`
        });

        // 状态检查（复用主机逻辑）
        that.checkDeviceStatus();
      },
      fail: function (err) {
        console.error("从机获取影子失败：", err);
        if (err.statusCode === 401) {
          that.setData({
            tokenExpired: true,
            result: "Token过期，正在重新获取..."
          });
        } else {
          that.setData({
            isOnline: true,  // 与主页一致，有数据时显示在线
            result: "数据获取完成，但设备可能离线"
          });
        }
      }
    });
  },

  /**
   * 设备状态检查（与主机一致的预警逻辑）
   */
  checkDeviceStatus() {
    const { temperature, smoke, sound, flame, tempThreshold, smokeThreshold } = this.data;

    const tempStatus = temperature > tempThreshold ? "warning" : "normal";
    const smokeStatus = smoke > smokeThreshold ? "warning" : "normal";
    const soundStatus = sound > 70 ? "warning" : "normal";
    const flameStatus = flame ? "warning" : "normal";

    const abnormalCount = [tempStatus, smokeStatus, soundStatus, flameStatus].filter(s => s === "warning").length;

    let overallStatus = "normal";
    if (abnormalCount >= 2) {
      overallStatus = "alarm";
    } else if (abnormalCount === 1) {
      overallStatus = "warning";
    }

    this.setData({
      tempStatus,
      smokeStatus,
      soundStatus,
      flameStatus,
      overallStatus
    });
  },

  /**
   * 返回主机页面
   */
  goBack() {
    wx.navigateBack();
  },

  /**
   * 页面隐藏：暂停轮询
   */
  onHide() {
    if (this.data.refreshInterval) {
      clearInterval(this.data.refreshInterval);
      this.setData({ refreshInterval: null });
      console.log("从机页面隐藏，暂停轮询");
    }
  },

  /**
   * 页面显示：重启轮询
   */
  onShow() {
    if (!this.data.refreshInterval) {
      this.startDataRefresh();
      console.log("从机页面显示，重启轮询");
    }
  },

  /**
   * 页面卸载：清除定时器
   */
  onUnload() {
    if (this.data.refreshInterval) clearInterval(this.data.refreshInterval);
    console.log("从机页面卸载，清除定时器");
  }
});
