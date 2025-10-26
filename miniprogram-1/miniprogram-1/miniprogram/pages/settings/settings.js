Page({
  data: {
    tempThreshold: 50,
    smokeThreshold: 600,
    tempMin: 30,
    tempMax: 70,
    smokeMin: 300,
    smokeMax: 1000,
    tempInput: '',
    smokeInput: ''
  },

  onLoad() {
    // 加载当前阈值设置
    const savedTemp = wx.getStorageSync('tempThreshold');
    const savedSmoke = wx.getStorageSync('smokeThreshold');
    
    this.setData({
      tempThreshold: savedTemp || 50,
      smokeThreshold: savedSmoke || 600,
      tempInput: (savedTemp || 50).toString(),
      smokeInput: (savedSmoke || 600).toString()
    });
  },

  // 温度阈值滑块变化
  onTempSliderChange(e) {
    const value = e.detail.value;
    this.setData({
      tempThreshold: value,
      tempInput: value.toString()
    });
  },

  // 烟雾阈值滑块变化
  onSmokeSliderChange(e) {
    const value = e.detail.value;
    this.setData({
      smokeThreshold: value,
      smokeInput: value.toString()
    });
  },

  // 温度输入框变化
  onTempInput(e) {
    let value = e.detail.value;
    // 过滤非数字字符
    value = value.replace(/[^\d]/g, '');
    // 转换为数字
    let num = parseInt(value, 10) || this.data.tempThreshold;
    // 限制范围
    num = Math.min(this.data.tempMax, Math.max(this.data.tempMin, num));
    
    this.setData({
      tempInput: num.toString(),
      tempThreshold: num
    });
  },

  // 烟雾输入框变化
  onSmokeInput(e) {
    let value = e.detail.value;
    // 过滤非数字字符
    value = value.replace(/[^\d]/g, '');
    // 转换为数字
    let num = parseInt(value, 10) || this.data.smokeThreshold;
    // 限制范围
    num = Math.min(this.data.smokeMax, Math.max(this.data.smokeMin, num));
    
    this.setData({
      smokeInput: num.toString(),
      smokeThreshold: num
    });
  },

  // 保存设置
  saveSettings() {
    const { tempThreshold, smokeThreshold } = this.data;
    
    // 保存到本地存储
    wx.setStorageSync('tempThreshold', tempThreshold);
    wx.setStorageSync('smokeThreshold', smokeThreshold);
    
    // 更新首页数据
    const pages = getCurrentPages();
    const homePage = pages.find(page => page.route === 'pages/index/index');
    if (homePage) {
      homePage.setData({
        tempThreshold,
        smokeThreshold
      });
    }
    
    // 提示保存成功并返回
    wx.showToast({
      title: '设置已保存',
      icon: 'success',
      duration: 1500
    });
    
    // 返回上一页
    setTimeout(() => {
      wx.navigateBack();
    }, 1500);
  },

  // 重置为默认值
  resetToDefault() {
    const defaultTemp = 50;
    const defaultSmoke = 600;
    
    this.setData({
      tempThreshold: defaultTemp,
      smokeThreshold: defaultSmoke,
      tempInput: defaultTemp.toString(),
      smokeInput: defaultSmoke.toString()
    });
  }
});
    