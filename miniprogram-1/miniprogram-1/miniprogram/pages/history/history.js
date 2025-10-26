Page({
  data: {
    historyData: [],
    hasData: false,
    masterCount: 0, // 新增：主机数据统计
    backendUrl: "http://localhost:5000", // Python后端地址
    loading: false,
    refreshInterval: null
  },

  onLoad() {
    this.fetchHistoryData(); // 直接从后端获取数据
    this.startDataRefresh(); // 启动定期刷新
  },

  // 启动数据刷新
  startDataRefresh() {
    const that = this;

    // 先清除旧的定时器
    if (this.data.refreshInterval) {
      clearInterval(this.data.refreshInterval);
    }

    // 立即获取一次数据
    this.fetchHistoryData();

    // 每30秒刷新一次历史数据
    const interval = setInterval(() => {
      that.fetchHistoryData();
    }, 30000);

    this.setData({ refreshInterval: interval });
  },

  // 从后端加载历史数据，只显示主机数据
  fetchHistoryData() {
    const that = this;

    this.setData({ loading: true });

    wx.request({
      url: `${that.data.backendUrl}/api/sensor/history?limit=100`,
      method: 'GET',
      header: {
        'content-type': 'application/json',
        'Accept': 'application/json'
      },
      timeout: 10000, // 10秒超时
      success: function(res) {
        console.log('=== 历史数据获取成功 ===');
        console.log('状态码:', res.statusCode);
        console.log('原始数据类型:', typeof res.data);
        console.log('原始数据长度:', res.data ? res.data.length : 'null');
        console.log('原始数据样例:', res.data ? res.data.slice(0, 2) : 'null');

        if (res.statusCode === 200 && res.data && Array.isArray(res.data)) {
          console.log('=== 测试：显示所有数据 ===');
          for (let i = 0; i < Math.min(3, res.data.length); i++) {
            console.log(`数据${i+1}:`, res.data[i].device_id, res.data[i].device_type);
          }

          // 临时显示所有数据来测试连接
          const allData = res.data;
          console.log('=== 显示所有数据（临时测试） ===');
          console.log('总数据数量:', allData.length);

          // 过滤主机数据（device_type = 'master'）
          const masterData = allData.filter(item => item.device_type === 'master');
          console.log('=== 过滤结果 ===');
          console.log('主机数据数量:', masterData.length);
          console.log('主机数据样例:', masterData.slice(0, 1));

          // 转换数据格式，适配小程序现有逻辑
          // 临时使用所有数据进行测试
          const formattedData = allData.map(item => ({
            id: item.id,
            device_id: item.device_id,
            device_type: item.device_type,
            temperature: item.temperature,
            humidity: item.humidity,
            smoke: item.smoke,
            flame: item.flame,
            light: item.light, // 使用light字段而不是light_level
            time: new Date(item.timestamp).toLocaleString(),
            timestamp: item.timestamp
          }));

          that.setData({
            historyData: formattedData,
            hasData: formattedData.length > 0,
            loading: false,
            masterCount: masterData.length // 显示实际的主机数据数量
          });

          // 可选：同时更新本地存储作为备份
          wx.setStorageSync('historyData', formattedData);

        } else {
          console.log('=== 数据获取失败或为空 ===');
          console.log('res.data 是否存在:', !!res.data);
          console.log('res.data 是否为数组:', Array.isArray(res.data));

          that.setData({
            historyData: [],
            hasData: false,
            loading: false,
            masterCount: 0
          });
          wx.showToast({
            title: '暂无主机历史数据',
            icon: 'none',
            duration: 2000
          });
        }
      },
      fail: function(err) {
        console.log('=== 网络请求失败 ===');
        console.error('错误信息:', err);
        console.error('错误类型:', typeof err);
        that.setData({
          loading: false,
          hasData: false,
          masterCount: 0
        });
        wx.showToast({
          title: '网络请求失败',
          icon: 'error',
          duration: 2000
        });
      }
    });
  },

  // 跳转到数据可视化页面
  goToChart() {
    wx.navigateTo({
      url: '/pages/chart/chart'
    });
  },

  // 页面卸载：清除定时器
  onUnload() {
    if (this.data.refreshInterval) {
      clearInterval(this.data.refreshInterval);
      console.log('历史数据页面卸载，清除定时器');
    }
  },

  // 清除所有历史记录
  clearAllRecords() {
    const that = this;
    wx.showModal({
      title: '确认清除',
      content: '确定要清除所有历史数据记录吗？此操作不可恢复。',
      success(res) {
        if (res.confirm) {
          // 清除内存数据
          that.setData({
            historyData: [],
            hasData: false
          });
          // 清除本地存储
          wx.setStorageSync('historyData', []);
          // 提示用户
          wx.showToast({
            title: '已清除所有记录',
            icon: 'success',
            duration: 2000
          });
        }
      }
    });
  },

  // 返回首页
  goBack() {
    wx.navigateBack({
      delta: 1
    });
  },

  // 页面显示时刷新数据
  onShow() {
    this.fetchHistoryData();
  }
})
    