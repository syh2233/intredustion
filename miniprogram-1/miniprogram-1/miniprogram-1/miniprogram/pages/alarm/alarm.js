Page({
  data: {
    alarmRecords: [],
    noRecords: false,
    filterType: 'all', // all, unhandled, handled
    filteredRecords: [],
    backendUrl: "https://icstop1syh.cpolar.top", // Python后端地址（cpolar内网穿透）
    loading: false
  },

  onLoad() {
    this.loadAlarmRecords();
  },

  onShow() {
    this.loadAlarmRecords();
  },

  // 从后端API加载报警记录
  loadAlarmRecords() {
    const that = this;
    this.setData({ loading: true });

    wx.request({
      url: `${that.data.backendUrl}/api/alerts`,
      method: 'GET',
      header: {
        'content-type': 'application/json'
      },
      timeout: 10000, // 10秒超时
      success: function(res) {
        console.log('报警记录获取成功:', res.data);

        if (res.statusCode === 200 && res.data) {
          // 转换后端数据格式以适配前端
          const formattedAlarms = res.data.map(alert => ({
            id: alert.id,
            type: alert.alert_type || 'unknown',
            level: alert.severity || 'medium',
            time: new Date(alert.timestamp).toLocaleString(),
            description: that.getAlertDescription(alert),
            parameters: that.getAlertParameters(alert),
            handled: alert.resolved || false,
            deviceId: alert.device_id,
            location: alert.location
          }));

          console.log('格式化后的报警记录:', formattedAlarms);

          that.setData({
            alarmRecords: formattedAlarms,
            noRecords: formattedAlarms.length === 0,
            loading: false
          });
          that.filterRecords();
        } else {
          console.warn('后端返回的报警数据为空');
          that.setData({
            alarmRecords: [],
            noRecords: true,
            loading: false
          });
          that.filterRecords();
        }
      },
      fail: function(err) {
        console.error('获取报警记录失败:', err);
        wx.showToast({
          title: '网络请求失败',
          icon: 'error',
          duration: 2000
        });
        that.setData({
          alarmRecords: [],
          noRecords: true,
          loading: false
        });
        that.filterRecords();
      }
    });
  },

  // 获取报警描述
  getAlertDescription(alert) {
    const alertType = alert.alert_type || 'unknown';
    const deviceInfo = alert.device_id ? `设备 ${alert.device_id}` : '未知设备';
    const locationInfo = alert.location && alert.location !== 'Unknown location' ? ` (${alert.location})` : '';

    switch(alertType) {
      case 'fire':
        return `${deviceInfo}${locationInfo} 检测到火焰报警！`;
      case 'temperature':
        return `${deviceInfo}${locationInfo} 温度过高 (${alert.temperature}°C)`;
      case 'smoke':
        return `${deviceInfo}${locationInfo} 烟雾浓度异常 (${alert.smoke_value}ppm)`;
      default:
        return `${deviceInfo}${locationInfo} 检测到异常！`;
    }
  },

  // 获取报警参数
  getAlertParameters(alert) {
    const params = [];
    if (alert.temperature !== null && alert.temperature !== undefined) {
      params.push(`温度: ${alert.temperature}°C`);
    }
    if (alert.humidity !== null && alert.humidity !== undefined) {
      params.push(`湿度: ${alert.humidity}%`);
    }
    if (alert.smoke_value !== null && alert.smoke_value !== undefined) {
      params.push(`烟雾: ${alert.smoke_value}ppm`);
    }
    if (alert.flame_value !== null && alert.flame_value !== undefined) {
      params.push(`火焰: ${alert.flame_value ? '检测到' : '未检测到'}`);
    }
    return params.join(', ') || '无参数数据';
  },

  // 筛选记录
  filterRecords() {
    const { alarmRecords, filterType } = this.data;
    let filtered;

    switch(filterType) {
      case 'unhandled':
        filtered = alarmRecords.filter(alarm => !alarm.handled);
        break;
      case 'handled':
        filtered = alarmRecords.filter(alarm => alarm.handled);
        break;
      default:
        filtered = alarmRecords;
    }

    this.setData({ filteredRecords: filtered });
  },

  // 切换筛选类型
  changeFilterType(e) {
    const type = e.currentTarget.dataset.type;
    this.setData({ filterType: type }, () => {
      this.filterRecords();
    });
  },

  // 查看报警详情
  viewAlarmDetails(e) {
    const alarmId = e.currentTarget.dataset.id;
    const { alarmRecords } = this.data;
    const alarm = alarmRecords.find(a => a.id === alarmId);

    if (alarm) {
      wx.showModal({
        title: `${alarm.level}详情`,
        content: `时间：${alarm.time}\n${alarm.description}\n当前参数：${alarm.parameters || '无'}`,
        showCancel: false,
        confirmText: '知道了'
      });
    }
  },

  // 标记为已处理
  markAsHandled(e) {
    const alarmId = e.currentTarget.dataset.id;
    const that = this;

    wx.showModal({
      title: '确认处理',
      content: '确定要将这条报警标记为已处理吗？',
      success(res) {
        if (res.confirm) {
          // 调用后端API更新报警状态
          wx.request({
            url: `${that.data.backendUrl}/api/alerts/${alarmId}/resolve`,
            method: 'PUT',
            header: {
              'content-type': 'application/json'
            },
            success: function(res) {
              if (res.statusCode === 200 && res.data.status === 'success') {
                console.log(`报警 ${alarmId} 已标记为已处理`);

                // 更新本地数据
                const updatedAlarms = that.data.alarmRecords.map(alarm => {
                  if (alarm.id === alarmId) {
                    return { ...alarm, handled: true };
                  }
                  return alarm;
                });

                that.setData({
                  alarmRecords: updatedAlarms
                });
                that.filterRecords();

                // 更新首页未处理计数
                const pages = getCurrentPages();
                const homePage = pages.find(page => page.route === 'pages/index/index');
                if (homePage) {
                  homePage.setData({
                    unhandledCount: updatedAlarms.filter(alarm => !alarm.handled).length
                  });
                }

                wx.showToast({
                  title: '已标记为已处理',
                  icon: 'success',
                  duration: 1500
                });
              } else {
                console.error('更新报警状态失败:', res);
                wx.showToast({
                  title: '操作失败',
                  icon: 'error',
                  duration: 2000
                });
              }
            },
            fail: function(err) {
              console.error('请求失败:', err);
              wx.showToast({
                title: '网络请求失败',
                icon: 'error',
                duration: 2000
              });
            }
          });
        }
      }
    });
  },

  // 清除全部记录
  clearAllRecords() {
    wx.showModal({
      title: '确认清除',
      content: '确定要清除所有报警记录吗？此操作不可恢复。',
      success: (res) => {
        if (res.confirm) {
          // 只清除本地显示的数据
          this.setData({
            alarmRecords: [],
            filteredRecords: [],
            noRecords: true
          });

          // 更新首页未处理计数
          const pages = getCurrentPages();
          const homePage = pages.find(page => page.route === 'pages/index/index');
          if (homePage) {
            homePage.setData({ unhandledCount: 0 });
          }

          wx.showToast({
            title: '已清除本地显示',
            icon: 'success',
            duration: 1500
          });
        }
      }
    });
  }
});
