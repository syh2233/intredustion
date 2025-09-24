// ESP32宿舍火灾报警系统 - 主页面JavaScript

// 全局变量
let socket;
let devices = {};
let slaves = {};
let alarmHistory = [];
let realtimeChart;
let sensorData = {
    labels: [],
    temperature: [],
    humidity: [],
    smoke: [],
    flame: [],
    light: []
};
const MAX_DATA_POINTS = 20;

// 页面加载完成后初始化
document.addEventListener('DOMContentLoaded', function() {
    initializeApp();
});

// 初始化应用
function initializeApp() {
    console.log('初始化ESP32火灾报警系统...');
    
    // 初始化Socket.IO连接
    initializeSocket();
    
    // 初始化图表
    initializeChart();
    
    // 加载初始数据
    loadInitialData();
    
    // 设置事件监听器
    setupEventListeners();
    
    // 启动定时器
    startTimers();
}

// 初始化Socket.IO连接
function initializeSocket() {
    console.log('正在初始化WebSocket连接...');

    // 建立Socket.IO连接
    socket = io();

    // 连接成功
    socket.on('connect', function() {
        console.log('WebSocket连接成功');
        showNotification('连接成功', '已连接到火灾报警系统', 'success');
    });

    // 连接断开
    socket.on('disconnect', function() {
        console.log('WebSocket连接断开');
        showNotification('连接断开', '正在尝试重新连接...', 'warning');
    });

    // 连接错误
    socket.on('connect_error', function(error) {
        console.error('WebSocket连接错误:', error);
        showNotification('连接错误', '无法连接到服务器，使用HTTP轮询', 'warning');
    });

    // 接收实时传感器数据
    socket.on('sensor_data', function(data) {
        console.log('收到传感器数据:', data);
        // 可以在这里处理实时传感器数据
    });

    // 接收报警信息 - 关键修复点！
    socket.on('alarm', function(alarmData) {
        console.log('收到报警消息:', alarmData);
        handleAlarm(alarmData);
    });

    // 接收设备状态更新
    socket.on('devices_update', function(devicesData) {
        console.log('收到设备状态更新:', devicesData);
        updateDevices(devicesData);
        updateStatusOverview(devicesData);
    });
}

// 加载初始数据
function loadInitialData() {
    // 通过API获取初始设备数据
    fetch('/api/devices')
        .then(response => response.json())
        .then(data => {
            updateDevices(data);
            updateStatusOverview(data);
        })
        .catch(error => {
            console.error('加载设备数据失败:', error);
            showNotification('加载失败', '无法加载设备数据', 'error');
        });

    // 加载从机数据
    refreshSlaves();

    // 加载报警历史
    fetch('/api/history')
        .then(response => response.json())
        .then(data => {
            updateAlarmHistory(data);
        })
        .catch(error => {
            console.error('加载报警历史失败:', error);
        });
}

// 设置事件监听器
function setupEventListeners() {
    // 添加键盘快捷键
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape') {
            // ESC键停止报警声音
            stopAlarmSound();
        }
    });
    
    // 添加设备卡片点击事件
    document.addEventListener('click', function(e) {
        if (e.target.closest('.device-card')) {
            const deviceId = e.target.closest('.device-card').dataset.deviceId;
            showDeviceDetails(deviceId);
        }
    });
    
    // 图表控制按钮事件
    document.querySelectorAll('.chart-btn').forEach(btn => {
        btn.addEventListener('click', function() {
            const chartType = this.dataset.chart;
            updateChartView(chartType);
            
            // 更新按钮状态
            document.querySelectorAll('.chart-btn').forEach(b => b.classList.remove('active'));
            this.classList.add('active');
        });
    });
}

// 启动定时器
function startTimers() {
    // 每30秒检查一次连接状态
    setInterval(checkConnection, 30000);

    // 每秒更新时间显示
    setInterval(updateCurrentTime, 1000);

    // 每5秒获取一次传感器数据用于图表
    setInterval(fetchSensorDataForChart, 5000);

    // 每3秒刷新一次从机数据
    setInterval(refreshSlaves, 3000);

    // 每10秒刷新一次设备数据
    setInterval(refreshDevices, 10000);
}

// 刷新设备数据
function refreshDevices() {
    fetch('/api/devices')
        .then(response => response.json())
        .then(data => {
            updateDevices(data);
            updateStatusOverview(data);
        })
        .catch(error => {
            console.error('刷新设备数据失败:', error);
        });
}

// 更新设备显示
function updateDevices(deviceData) {
    const container = document.getElementById('devices-container');
    if (!container) return;
    
    container.innerHTML = '';
    
    deviceData.forEach(device => {
        devices[device.device_id] = device;
        const deviceCard = createDeviceCard(device);
        container.appendChild(deviceCard);
    });
}

// 创建设备卡片
function createDeviceCard(device) {
    const card = document.createElement('div');
    card.className = `device-card ${device.status.toLowerCase()}`;
    card.dataset.deviceId = device.device_id;
    
    const statusIcon = getStatusIcon(device.status);
    const lastUpdate = formatTime(device.last_update);
    
    card.innerHTML = `
        <div class="device-header">
            <div class="device-id">${device.device_id}</div>
            <div class="device-status ${device.status.toLowerCase()}">${device.status}</div>
        </div>
        <div class="device-location">
            <i class="fas fa-map-marker-alt"></i> ${device.location}
        </div>
        <div class="device-metrics">
            <div class="metric">
                <div class="metric-value">${(device.temperature || 0).toFixed(1)}°C</div>
                <div class="metric-label">温度</div>
            </div>
            <div class="metric">
                <div class="metric-value">${(device.humidity || 0).toFixed(0)}%</div>
                <div class="metric-label">湿度</div>
            </div>
            <div class="metric">
                <div class="metric-value">${(device.smoke_level || 0).toFixed(0)}</div>
                <div class="metric-label">烟雾</div>
            </div>
            <div class="metric">
                <div class="metric-value">${(device.flame || 0).toFixed(0)}</div>
                <div class="metric-label">火焰</div>
            </div>
            <div class="metric">
                <div class="metric-value">${(device.light_level || 0).toFixed(0)}</div>
                <div class="metric-label">光照</div>
            </div>
        </div>
        <div class="device-time">
            <small data-timestamp="${device.last_update}">最后更新: ${lastUpdate}</small>
        </div>
    `;
    
    return card;
}

// 获取状态图标
function getStatusIcon(status) {
    const icons = {
        '正常': '<i class="fas fa-check-circle" style="color: #4CAF50;"></i>',
        '警告': '<i class="fas fa-exclamation-triangle" style="color: #FF9800;"></i>',
        '警报': '<i class="fas fa-bell" style="color: #F44336;"></i>'
    };
    return icons[status] || '<i class="fas fa-question-circle"></i>';
}

// 更新状态概览
function updateStatusOverview(deviceData) {
    const statusCounts = {
        normal: 0,
        warning: 0,
        alarm: 0
    };
    
    deviceData.forEach(device => {
        const status = device.status;
        console.log(`设备 ${device.device_id} 状态: ${status}`);
        
        // 处理中文状态映射，不使用toLowerCase()
        if (status === '正常' || status === 'normal') {
            statusCounts.normal++;
            console.log(`设备 ${device.device_id} 计入正常状态`);
        } else if (status === '警告' || status === 'warning') {
            statusCounts.warning++;
            console.log(`设备 ${device.device_id} 计入警告状态`);
        } else if (status === '警报' || status === 'alarm') {
            statusCounts.alarm++;
            console.log(`设备 ${device.device_id} 计入警报状态`);
        } else {
            console.log(`未知状态: ${status}`);
        }
    });
    
    // 更新显示
    const normalCount = document.getElementById('normal-count');
    const warningCount = document.getElementById('warning-count');
    const alarmCount = document.getElementById('alarm-count');
    
    if (normalCount) normalCount.textContent = statusCounts.normal;
    if (warningCount) warningCount.textContent = statusCounts.warning;
    if (alarmCount) alarmCount.textContent = statusCounts.alarm;
    
    // 如果有警报，添加视觉提示
    if (statusCounts.alarm > 0) {
        document.body.classList.add('alarm-active');
    } else {
        document.body.classList.remove('alarm-active');
    }
}

// 处理报警
function handleAlarm(alarmData) {
    console.log('收到报警:', alarmData);
    
    // 添加到报警历史
    alarmHistory.unshift(alarmData);
    updateAlarmHistory(alarmHistory);
    
    // 播放报警声音
    playAlarmSound();
    
    // 显示报警通知
    showNotification(
        '火灾警报！',
        `${alarmData.location} 检测到火灾风险！`,
        'alarm'
    );
    
    // 浏览器通知（如果用户允许）
    showBrowserNotification('火灾警报', alarmData.message);
}

// 更新报警历史显示
function updateAlarmHistory(history) {
    const container = document.getElementById('alarm-container');
    if (!container) return;
    
    container.innerHTML = '';
    
    if (history.length === 0) {
        container.innerHTML = '<div class="no-data">暂无报警记录</div>';
        return;
    }
    
    // 只显示最近20条记录
    const recentHistory = history.slice(0, 20);
    
    recentHistory.forEach(alarm => {
        const alarmElement = createAlarmElement(alarm);
        container.appendChild(alarmElement);
    });
}

// 创建报警元素
function createAlarmElement(alarm) {
    const element = document.createElement('div');
    element.className = 'alarm-item';
    
    const time = formatTime(alarm.timestamp);
    
    element.innerHTML = `
        <div class="alarm-header">
            <div class="alarm-title">
                <i class="fas fa-exclamation-triangle"></i> 火灾警报
            </div>
            <div class="alarm-time">${time}</div>
        </div>
        <div class="alarm-message">${alarm.message}</div>
        <div class="alarm-details">
            <span><i class="fas fa-thermometer-half"></i> 温度: ${alarm.temperature.toFixed(1)}°C</span>
            <span><i class="fas fa-smoking"></i> 烟雾: ${alarm.smoke_level.toFixed(0)}</span>
            <span><i class="fas fa-map-marker-alt"></i> ${alarm.location}</span>
        </div>
    `;
    
    return element;
}

// 播放报警声音
function playAlarmSound() {
    const audio = document.getElementById('alarm-sound');
    if (audio) {
        audio.loop = true;
        audio.play().catch(error => {
            console.error('播放报警声音失败:', error);
        });
    }
}

// 停止报警声音
function stopAlarmSound() {
    const audio = document.getElementById('alarm-sound');
    if (audio) {
        audio.pause();
        audio.currentTime = 0;
    }
}

// 显示通知
function showNotification(title, message, type = 'info') {
    // 创建通知元素
    const notification = document.createElement('div');
    notification.className = `notification ${type}`;
    notification.innerHTML = `
        <div class="notification-header">
            <div class="notification-title">${title}</div>
            <button class="notification-close" onclick="this.parentElement.parentElement.remove()">
                <i class="fas fa-times"></i>
            </button>
        </div>
        <div class="notification-message">${message}</div>
    `;
    
    // 添加到页面
    document.body.appendChild(notification);
    
    // 自动移除
    setTimeout(() => {
        if (notification.parentElement) {
            notification.remove();
        }
    }, 5000);
}

// 显示浏览器通知
function showBrowserNotification(title, message) {
    if ('Notification' in window && Notification.permission === 'granted') {
        new Notification(title, {
            body: message,
            icon: '/static/img/fire-alarm-icon.png',
            badge: '/static/img/fire-alarm-badge.png',
            tag: 'fire-alarm'
        });
    } else if ('Notification' in window && Notification.permission !== 'denied') {
        Notification.requestPermission().then(permission => {
            if (permission === 'granted') {
                showBrowserNotification(title, message);
            }
        });
    }
}

// 显示设备详情
function showDeviceDetails(deviceId) {
    const device = devices[deviceId];
    if (!device) return;
    
    // 创建模态框显示详细信息
    const modal = document.createElement('div');
    modal.className = 'modal';
    modal.innerHTML = `
        <div class="modal-content">
            <div class="modal-header">
                <h3>设备详情 - ${device.device_id}</h3>
                <button class="modal-close" onclick="this.closest('.modal').remove()">
                    <i class="fas fa-times"></i>
                </button>
            </div>
            <div class="modal-body">
                <div class="detail-row">
                    <strong>设备ID:</strong> ${device.device_id}
                </div>
                <div class="detail-row">
                    <strong>位置:</strong> ${device.location}
                </div>
                <div class="detail-row">
                    <strong>温度:</strong> ${device.temperature.toFixed(1)}°C
                </div>
                <div class="detail-row">
                    <strong>烟雾水平:</strong> ${device.smoke_level.toFixed(0)}
                </div>
                <div class="detail-row">
                    <strong>火焰值:</strong> ${device.flame || 'N/A'}
                </div>
                <div class="detail-row">
                    <strong>湿度:</strong> ${device.humidity ? device.humidity.toFixed(1) + '%' : 'N/A'}
                </div>
                <div class="detail-row">
                    <strong>状态:</strong> <span class="status-badge ${device.status.toLowerCase()}">${device.status}</span>
                </div>
                <div class="detail-row">
                    <strong>最后更新:</strong> ${formatTime(device.last_update)}
                </div>
            </div>
        </div>
    `;
    
    document.body.appendChild(modal);
    
    // 点击背景关闭
    modal.addEventListener('click', function(e) {
        if (e.target === modal) {
            modal.remove();
        }
    });
}

// 初始化图表
function initializeChart() {
    const ctx = document.getElementById('realtime-chart');
    if (!ctx) {
        console.error('找不到图表容器元素');
        return;
    }
    
    // 初始化为0值数据，等待真实传感器数据
    if (sensorData.labels.length === 0) {
        const now = new Date();
        for (let i = 9; i >= 0; i--) {
            const time = new Date(now.getTime() - i * 5000);
            sensorData.labels.push(time.toLocaleTimeString('zh-CN'));
            sensorData.temperature.push(0); // 无数据时显示0
            sensorData.humidity.push(0);    // 无数据时显示0
            sensorData.smoke.push(0);       // 无数据时显示0
            sensorData.flame.push(0);       // 无数据时显示0
            sensorData.light.push(0);       // 无数据时显示0
        }
    }
    
    try {
        realtimeChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: sensorData.labels,
            datasets: [
                {
                    label: '温度 (°C)',
                    data: sensorData.temperature,
                    borderColor: '#FF6384',
                    backgroundColor: 'rgba(255, 99, 132, 0.1)',
                    tension: 0.4,
                    yAxisID: 'y'
                },
                {
                    label: '烟雾水平',
                    data: sensorData.smoke,
                    borderColor: '#36A2EB',
                    backgroundColor: 'rgba(54, 162, 235, 0.1)',
                    tension: 0.4,
                    yAxisID: 'y1'
                },
                {
                    label: '火焰值',
                    data: sensorData.flame,
                    borderColor: '#FFCE56',
                    backgroundColor: 'rgba(255, 206, 86, 0.1)',
                    tension: 0.4,
                    yAxisID: 'y2'
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            resizeDelay: 0,
            animation: {
                duration: 0
            },
            events: [], // 禁用所有交互事件防止尺寸变化
            interaction: {
                mode: 'index',
                intersect: false,
            },
            plugins: {
                title: {
                    display: true,
                    text: '火灾风险实时监控 - 综合视图'
                },
                legend: {
                    display: true,
                    position: 'top'
                }
            },
            scales: {
                x: {
                    display: true,
                    title: {
                        display: true,
                        text: '时间'
                    }
                },
                y: {
                    type: 'linear',
                    display: true,
                    position: 'left',
                    title: {
                        display: true,
                        text: '风险程度 (%)'
                    },
                    min: 0,
                    max: 100,
                    beginAtZero: true
                },
                y1: {
                    type: 'linear',
                    display: false,
                    position: 'right',
                    min: 0,
                    max: 2000,
                    beginAtZero: true,
                    grid: {
                        drawOnChartArea: false,
                    },
                },
                y2: {
                    type: 'linear',
                    display: false,
                    position: 'right',
                    min: 0,
                    max: 2000,
                    beginAtZero: true,
                    grid: {
                        drawOnChartArea: false,
                    },
                }
            }
        }
        });
        
        // 初始化为综合视图（标准化数据）
        normalizeDataForCombinedView();
        
        console.log('图表初始化成功');
    } catch (error) {
        console.error('图表初始化失败:', error);
    }
}

// 更新图表视图
function updateChartView(chartType) {
    if (!realtimeChart) return;
    
    const datasets = realtimeChart.data.datasets;
    
    switch(chartType) {
        case 'temperature':
            restoreOriginalData();
            datasets[0].hidden = false;
            datasets[1].hidden = true;
            datasets[2].hidden = true;
            realtimeChart.options.scales.y.display = true;
            realtimeChart.options.scales.y1.display = false;
            realtimeChart.options.scales.y2.display = false;
            realtimeChart.options.plugins.title.text = '温度监控 - 原始数据';
            realtimeChart.options.scales.y.title.text = '温度 (°C)';
            realtimeChart.options.scales.y.max = 60;
            break;
        case 'smoke':
            restoreOriginalData();
            datasets[0].hidden = true;
            datasets[1].hidden = false;
            datasets[2].hidden = true;
            realtimeChart.options.scales.y.display = false;
            realtimeChart.options.scales.y1.display = true;
            realtimeChart.options.scales.y2.display = false;
            realtimeChart.options.plugins.title.text = '烟雾水平监控 - 原始数据';
            realtimeChart.options.scales.y1.title.text = '烟雾水平';
            realtimeChart.options.scales.y1.max = 2000;
            break;
        case 'flame':
            restoreOriginalData();
            datasets[0].hidden = true;
            datasets[1].hidden = true;
            datasets[2].hidden = false;
            realtimeChart.options.scales.y.display = false;
            realtimeChart.options.scales.y1.display = false;
            realtimeChart.options.scales.y2.display = true;
            realtimeChart.options.plugins.title.text = '火焰值监控 - 原始数据';
            realtimeChart.options.scales.y2.title.text = '火焰值';
            realtimeChart.options.scales.y2.max = 2000;
            break;
        case 'humidity':
            restoreOriginalData();
            datasets[0].hidden = true;
            datasets[1].hidden = true;
            datasets[2].hidden = true;
            // 暂时使用温度数据集显示湿度，后续需要添加新的数据集
            datasets[0].hidden = false;
            datasets[0].label = '湿度 (%)';
            datasets[0].data = sensorData.humidity;
            realtimeChart.options.scales.y.display = true;
            realtimeChart.options.scales.y1.display = false;
            realtimeChart.options.scales.y2.display = false;
            realtimeChart.options.plugins.title.text = '湿度监控 - 原始数据';
            realtimeChart.options.scales.y.title.text = '湿度 (%)';
            realtimeChart.options.scales.y.max = 100;
            break;
        case 'light':
            restoreOriginalData();
            datasets[0].hidden = true;
            datasets[1].hidden = true;
            datasets[2].hidden = true;
            // 暂时使用烟雾数据集显示光照，后续需要添加新的数据集
            datasets[1].hidden = false;
            datasets[1].label = '光照强度';
            datasets[1].data = sensorData.light;
            realtimeChart.options.scales.y.display = false;
            realtimeChart.options.scales.y1.display = true;
            realtimeChart.options.scales.y2.display = false;
            realtimeChart.options.plugins.title.text = '光照强度监控 - 原始数据';
            realtimeChart.options.scales.y1.title.text = '光照强度';
            realtimeChart.options.scales.y1.max = 5000;
            break;
        default: // combined - 使用标准化数据显示
            datasets[0].hidden = false;
            datasets[1].hidden = false;
            datasets[2].hidden = false;
            realtimeChart.options.scales.y.display = true;
            realtimeChart.options.scales.y1.display = false;
            realtimeChart.options.scales.y2.display = false;
            realtimeChart.options.plugins.title.text = '火灾风险实时监控 - 综合视图';
            realtimeChart.options.scales.y.title.text = '风险程度 (%)';
            realtimeChart.options.scales.y.max = 100;
            
            // 在综合视图中标准化烟雾和火焰数据到0-100范围
            normalizeDataForCombinedView();
            break;
    }
    
    realtimeChart.update();
}

// 标准化数据用于综合视图
function normalizeDataForCombinedView() {
    if (!realtimeChart) return;
    
    const datasets = realtimeChart.data.datasets;
    
    // 调试：输出原始数据
    console.log('标准化前的原始温度数据:', sensorData.temperature.slice(-5));
    
    // 温度: 0-60°C -> 0-100%
    datasets[0].data = sensorData.temperature.map(temp => {
        // 确保温度是有效数字
        const validTemp = typeof temp === 'number' && !isNaN(temp) ? temp : 0;
        const norm = Math.min(100, Math.max(0, (validTemp / 60) * 100));
        return Math.round(norm);
    });
    datasets[0].label = '温度 (%)';
    
    // 烟雾: 0-200 -> 0-100% (烟雾值通常不会太高)
    datasets[1].data = sensorData.smoke.map(smoke => {
        const validSmoke = typeof smoke === 'number' && !isNaN(smoke) ? smoke : 0;
        const norm = Math.min(100, Math.max(0, (validSmoke / 200) * 100));
        return Math.round(norm);
    });
    datasets[1].label = '烟雾 (%)';
    
    // 火焰: 反向映射, 800-1500 -> 100-0% (值越低风险越高)
    datasets[2].data = sensorData.flame.map(flame => {
        const validFlame = typeof flame === 'number' && !isNaN(flame) ? flame : 0;
        // 将火焰值映射到风险百分比: 800=100%, 1500=0%
        const risk = Math.max(0, Math.min(100, ((1500 - validFlame) / 700) * 100));
        return Math.round(risk);
    });
    datasets[2].label = '火焰风险 (%)';
    
    console.log('标准化后的温度百分比:', datasets[0].data.slice(-5));
}

// 恢复原始数据用于单独视图
function restoreOriginalData() {
    if (!realtimeChart) return;
    
    const datasets = realtimeChart.data.datasets;
    
    datasets[0].data = [...sensorData.temperature];
    datasets[0].label = '温度 (°C)';
    
    datasets[1].data = [...sensorData.smoke];
    datasets[1].label = '烟雾水平';
    
    datasets[2].data = [...sensorData.flame];
    datasets[2].label = '火焰值';
}

// 用新数据更新图表
function updateChartWithNewData(deviceData) {
    if (!realtimeChart) return;
    
    const now = new Date();
    const timeLabel = now.toLocaleTimeString('zh-CN');
    
    let avgTemp = 0, avgHumidity = 0, avgSmoke = 0, avgFlame = 0, avgLight = 0;
    let validDevices = 0;
    
    // 调试：输出接收到的设备数据
    console.log('接收到设备数据:', deviceData);
    
    // 只有在有真实设备数据时才计算平均值
    if (deviceData && deviceData.length > 0) {
        deviceData.forEach(device => {
            if (device && typeof device.temperature === 'number' && 
                typeof device.smoke_level === 'number') {
                avgTemp += device.temperature;
                avgHumidity += device.humidity || 0;
                avgSmoke += device.smoke_level;
                avgFlame += device.flame || 0;
                avgLight += device.light_level || 0;
                validDevices++;
                console.log(`设备 ${device.device_id}: 温度=${device.temperature}, 湿度=${device.humidity || 0}, 烟雾=${device.smoke_level}, 火焰=${device.flame || 0}, 光照=${device.light_level || 0}`);
            }
        });
        
        if (validDevices > 0) {
            avgTemp /= validDevices;
            avgHumidity /= validDevices;
            avgSmoke /= validDevices;
            avgFlame /= validDevices;
            avgLight /= validDevices;
        }
    }
    
    // 如果没有有效数据，使用0值
    if (validDevices === 0) {
        avgTemp = 0;
        avgSmoke = 0;
        avgFlame = 0;
        console.log('无传感器数据，显示0值');
    }
    
    console.log(`计算平均值: 温度=${avgTemp.toFixed(1)}, 烟雾=${avgSmoke.toFixed(0)}, 火焰=${avgFlame.toFixed(0)}`);
    
    // 添加新数据点
    sensorData.labels.push(timeLabel);
    sensorData.temperature.push(Number(avgTemp.toFixed(1)));
    sensorData.humidity.push(Number(avgHumidity.toFixed(1)));
    sensorData.smoke.push(Number(avgSmoke.toFixed(0)));
    sensorData.flame.push(Number(avgFlame.toFixed(0)));
    sensorData.light.push(Number(avgLight.toFixed(0)));
    
    // 保持数据点数量限制
    if (sensorData.labels.length > MAX_DATA_POINTS) {
        sensorData.labels.shift();
        sensorData.temperature.shift();
        sensorData.humidity.shift();
        sensorData.smoke.shift();
        sensorData.flame.shift();
        sensorData.light.shift();
    }
    
    // 更新图表
    try {
        // 检查当前是否为综合视图，如果是则需要重新标准化数据
        const activeChartBtn = document.querySelector('.chart-btn.active');
        if (activeChartBtn && activeChartBtn.dataset.chart === 'combined') {
            normalizeDataForCombinedView();
        }
        
        realtimeChart.update('none');
    } catch (error) {
        console.error('图表更新失败:', error);
    }
}

// 获取传感器数据用于图表
function fetchSensorDataForChart() {
    fetch('/api/devices')
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            if (data && Array.isArray(data) && data.length > 0) {
                updateChartWithNewData(data);
            } else {
                console.log('没有获取到设备数据');
            }
        })
        .catch(error => {
            console.error('获取传感器数据失败:', error);
        });
}

// 更新当前时间显示
function updateCurrentTime() {
    const timeElement = document.getElementById('current-time');
    if (timeElement) {
        const now = new Date();
        timeElement.textContent = now.toLocaleString('zh-CN');
    }
}

// 检查连接状态
function checkConnection() {
    // 使用HTTP检查服务器连接状态
    fetch('/api/devices')
        .then(response => {
            if (!response.ok) {
                throw new Error('服务器连接异常');
            }
            console.log('服务器连接正常');
        })
        .catch(error => {
            console.warn('连接检查失败:', error);
            showNotification('连接断开', '正在尝试重新连接...', 'warning');
        });
}

// 更新时间显示
function updateTimeDisplay() {
    // 更新所有设备时间显示
    const deviceTimeElements = document.querySelectorAll('.device-time small');
    deviceTimeElements.forEach(element => {
        // 优先使用data-timestamp属性
        const timestamp = element.getAttribute('data-timestamp');
        if (timestamp) {
            element.textContent = '最后更新: ' + formatTime(parseFloat(timestamp));
        } else {
            // 备用方案：从全局devices对象中获取时间戳
            const deviceCard = element.closest('.device-card');
            if (deviceCard) {
                const deviceId = deviceCard.dataset.deviceId;
                const device = devices[deviceId];
                if (device && device.last_update) {
                    element.textContent = '最后更新: ' + formatTime(device.last_update);
                    // 设置data-timestamp属性以便下次使用
                    element.setAttribute('data-timestamp', device.last_update);
                }
            }
        }
    });
}

// 格式化时间
function formatTime(timestamp) {
    // 检查时间戳格式，如果是秒级时间戳（小于1000000000000）则转换为毫秒
    let dateMs;
    if (timestamp < 1000000000000) { // 秒级时间戳
        dateMs = timestamp * 1000;
    } else { // 毫秒级时间戳
        dateMs = timestamp;
    }
    
    // 创建本地日期对象（JavaScript会自动转换为本地时区）
    const localDate = new Date(dateMs);
    
    const now = new Date();
    const diff = now - localDate;
    
    if (diff < 60000) { // 1分钟内
        return '刚刚';
    } else if (diff < 3600000) { // 1小时内
        return Math.floor(diff / 60000) + '分钟前';
    } else if (diff < 86400000) { // 1天内
        return Math.floor(diff / 3600000) + '小时前';
    } else {
        // 使用本地时间格式化，确保显示北京时间
        return localDate.toLocaleString('zh-CN', {
            timeZone: 'Asia/Shanghai',
            year: 'numeric',
            month: '2-digit',
            day: '2-digit',
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit',
            hour12: false
        });
    }
}

// 添加通知样式
const notificationStyles = `
.notification {
    position: fixed;
    top: 20px;
    right: 20px;
    background: white;
    border-radius: 8px;
    box-shadow: 0 4px 12px rgba(0,0,0,0.15);
    z-index: 10000;
    min-width: 300px;
    max-width: 400px;
    animation: slideInRight 0.3s ease;
}

.notification.alarm {
    border-left: 4px solid #F44336;
}

.notification.warning {
    border-left: 4px solid #FF9800;
}

.notification.success {
    border-left: 4px solid #4CAF50;
}

.notification.info {
    border-left: 4px solid #2196F3;
}

.notification-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 15px 15px 0 15px;
}

.notification-title {
    font-weight: bold;
    color: #333;
}

.notification-close {
    background: none;
    border: none;
    color: #666;
    cursor: pointer;
    padding: 5px;
}

.notification-message {
    padding: 10px 15px 15px 15px;
    color: #666;
}

@keyframes slideInRight {
    from {
        transform: translateX(100%);
        opacity: 0;
    }
    to {
        transform: translateX(0);
        opacity: 1;
    }
}

/* 模态框样式 */
.modal {
    position: fixed;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    background: rgba(0,0,0,0.5);
    display: flex;
    justify-content: center;
    align-items: center;
    z-index: 10000;
}

.modal-content {
    background: white;
    border-radius: 12px;
    padding: 25px;
    max-width: 500px;
    width: 90%;
    max-height: 80vh;
    overflow-y: auto;
    animation: modalSlideIn 0.3s ease;
}

.modal-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 20px;
    padding-bottom: 15px;
    border-bottom: 1px solid #eee;
}

.modal-close {
    background: none;
    border: none;
    color: #666;
    cursor: pointer;
    padding: 5px;
    font-size: 18px;
}

.detail-row {
    margin-bottom: 12px;
    padding: 8px 0;
    border-bottom: 1px solid #f0f0f0;
}

.detail-row:last-child {
    border-bottom: none;
}

.status-badge {
    padding: 4px 8px;
    border-radius: 12px;
    font-size: 0.9rem;
    font-weight: bold;
}

.status-badge.normal {
    background: #e8f5e8;
    color: #4CAF50;
}

.status-badge.warning {
    background: #fff3e0;
    color: #FF9800;
}

.status-badge.alarm {
    background: #ffebee;
    color: #F44336;
}

@keyframes modalSlideIn {
    from {
        transform: scale(0.7);
        opacity: 0;
    }
    to {
        transform: scale(1);
        opacity: 1;
    }
}
`;

// 添加样式到页面
if (!document.querySelector('#notification-styles')) {
    const styleElement = document.createElement('style');
    styleElement.id = 'notification-styles';
    styleElement.textContent = notificationStyles;
    document.head.appendChild(styleElement);
}

// 页面卸载时清理
window.addEventListener('beforeunload', function() {
    if (socket) {
        socket.disconnect();
    }
});

// 设备刷新函数
function refreshDevices() {
    fetch('/api/devices')
        .then(response => response.json())
        .then(data => {
            updateDevices(data);
            updateStatusOverview(data);
            showNotification('刷新成功', '设备数据已更新', 'success');
        })
        .catch(error => {
            console.error('刷新设备数据失败:', error);
            showNotification('刷新失败', '无法更新设备数据', 'error');
        });
}

// 显示特定状态的设备
function showStatusDevices(status) {
    console.log(`显示状态为 ${status} 的设备`);
    
    // 获取所有设备数据
    fetch('/api/devices')
        .then(response => response.json())
        .then(data => {
            // 筛选指定状态的设备
            const filteredDevices = data.filter(device => {
                const deviceStatus = device.status;
                if (status === 'normal') {
                    return deviceStatus === '正常' || deviceStatus === 'normal';
                } else if (status === 'warning') {
                    return deviceStatus === '警告' || deviceStatus === 'warning';
                } else if (status === 'alarm') {
                    return deviceStatus === '警报' || deviceStatus === 'alarm';
                }
                return false;
            });
            
            console.log(`找到 ${filteredDevices.length} 个${getStatusName(status)}设备`);
            
            // 显示模态框
            showStatusDevicesModal(status, filteredDevices);
        })
        .catch(error => {
            console.error('获取设备数据失败:', error);
            showNotification('获取失败', '无法获取设备数据', 'error');
        });
}

// 获取状态中文名称
function getStatusName(status) {
    const statusNames = {
        'normal': '正常',
        'warning': '警告',
        'alarm': '警报'
    };
    return statusNames[status] || status;
}

// 显示设备详情模态框
function showStatusDevicesModal(status, devices) {
    const modal = document.getElementById('status-devices-modal');
    const modalTitle = document.getElementById('modal-title');
    const container = document.getElementById('status-devices-container');
    
    // 设置标题
    const statusName = getStatusName(status);
    modalTitle.textContent = `${statusName}设备 (${devices.length}台)`;
    
    // 清空容器
    container.innerHTML = '';
    
    if (devices.length === 0) {
        container.innerHTML = '<div class="no-data">暂无' + statusName + '设备</div>';
    } else {
        // 生成设备卡片
        devices.forEach(device => {
            const deviceCard = createDeviceCard(device);
            container.appendChild(deviceCard);
        });
    }
    
    // 显示模态框
    modal.style.display = 'block';
    
    // 点击模态框外部关闭
    window.onclick = function(event) {
        if (event.target === modal) {
            closeStatusDevicesModal();
        }
    };
    
    // ESC键关闭模态框
    document.addEventListener('keydown', function escKeyHandler(event) {
        if (event.key === 'Escape') {
            closeStatusDevicesModal();
            document.removeEventListener('keydown', escKeyHandler);
        }
    });
}

// 创建设备卡片（与现有设备监控区域样式一致）
function createDeviceCard(device) {
    const card = document.createElement('div');
    card.className = `device-card ${device.status}`;
    
    const statusIcon = getStatusIcon(device.status);
    const lastUpdate = formatTime(device.last_update);
    
    card.innerHTML = `
        <div class="device-header">
            <div class="device-id">${device.device_id}</div>
            <div class="device-status ${device.status}">${getStatusName(device.status)}</div>
        </div>
        <div class="device-location">${device.location}</div>
        <div class="device-metrics">
            <div class="metric">
                <div class="metric-value">${device.temperature || 0}°C</div>
                <div class="metric-label">温度</div>
            </div>
            <div class="metric">
                <div class="metric-value">${device.humidity || 0}%</div>
                <div class="metric-label">湿度</div>
            </div>
            <div class="metric">
                <div class="metric-value">${device.smoke_level || 0}</div>
                <div class="metric-label">烟雾</div>
            </div>
            <div class="metric">
                <div class="metric-value">${device.flame || 0}</div>
                <div class="metric-label">火焰</div>
            </div>
            <div class="metric">
                <div class="metric-value">${device.light_level || 0}</div>
                <div class="metric-label">光照</div>
            </div>
        </div>
        <div class="device-footer">
            <small>最后更新: ${lastUpdate}</small>
        </div>
    `;
    
    return card;
}

// 关闭设备详情模态框
function closeStatusDevicesModal() {
    const modal = document.getElementById('status-devices-modal');
    modal.style.display = 'none';
    
    // 移除事件监听器
    window.onclick = null;
}

// 导出函数供全局使用
window.stopAlarmSound = stopAlarmSound;
window.refreshDevices = refreshDevices;
window.showStatusDevices = showStatusDevices;
window.closeStatusDevicesModal = closeStatusDevicesModal;
window.refreshSlaves = refreshSlaves;
window.testSlaveAPI = testSlaveAPI;

// 从机相关函数
function updateSlaveData(slaveData) {
    console.log('更新从机数据:', slaveData);

    // 确保从机数据格式与refreshSlaves一致
    const existingSlave = slaves[slaveData.device_id] || {};

    // 合并数据，保持格式一致
    slaves[slaveData.device_id] = {
        device_id: slaveData.device_id,
        device_type: 'slave',
        slave_name: slaveData.slave_name || existingSlave.slave_name || slaveData.device_id,
        slave_location: slaveData.slave_location || existingSlave.slave_location || '未知位置',
        overall_status: slaveData.overall_status || existingSlave.overall_status || 'normal',
        flame: slaveData.flame || existingSlave.flame || 0,
        smoke: slaveData.smoke || existingSlave.smoke || 0,
        temperature: slaveData.temperature || existingSlave.temperature || 0,
        humidity: slaveData.humidity || existingSlave.humidity || 0,
        light_level: slaveData.light || slaveData.light_level || existingSlave.light_level || 0,
        timestamp: slaveData.timestamp || existingSlave.timestamp || new Date().toISOString()
    };

    // 更新从机显示
    updateSlavesDisplay();

    // 如果从机处于警报状态，触发相应处理
    if (slaveData.overall_status === 'alarm') {
        handleSlaveAlarm(slaveData);
    }
}

function updateSlavesDisplay() {
    const container = document.getElementById('slaves-container');
    if (!container) {
        console.warn('从机容器元素不存在');
        return;
    }

    container.innerHTML = '';

    const slaveIds = Object.keys(slaves);
    console.log(`更新从机显示，从机数量: ${slaveIds.length}`, slaves);

    if (slaveIds.length === 0) {
        container.innerHTML = `
            <div class="no-slaves">
                <i class="fas fa-network-wired"></i>
                <p>暂无从机设备</p>
            </div>
        `;
        return;
    }

    slaveIds.forEach(slaveId => {
        const slave = slaves[slaveId];
        console.log(`创建从机卡片: ${slaveId}`, slave);
        const slaveCard = createSlaveCard(slave);
        container.appendChild(slaveCard);
    });
}

function createSlaveCard(slave) {
    const card = document.createElement('div');
    card.className = `slave-card ${slave.overall_status || 'normal'}`;
    card.dataset.deviceId = slave.device_id;

    const statusIcon = getStatusIcon(slave.overall_status || 'normal');
    const statusText = getStatusName(slave.overall_status || 'normal');
    const lastSeen = slave.timestamp ? new Date(slave.timestamp).toLocaleString() : '未知';

    card.innerHTML = `
        <div class="slave-header">
            <div class="slave-info">
                <h4>${slave.slave_name || slave.device_id}</h4>
                <p class="slave-location">${slave.slave_location || '未知位置'}</p>
            </div>
            <div class="slave-status">
                <span class="status-icon ${slave.overall_status || 'normal'}">${statusIcon}</span>
                <span class="status-text">${statusText}</span>
            </div>
        </div>
        <div class="slave-sensors">
            <div class="sensor-item">
                <i class="fas fa-fire"></i>
                <span class="sensor-label">火焰:</span>
                <span class="sensor-value">${slave.flame || 0}</span>
            </div>
            <div class="sensor-item">
                <i class="fas fa-smog"></i>
                <span class="sensor-label">烟雾:</span>
                <span class="sensor-value">${slave.smoke || 0}</span>
            </div>
        </div>
        <div class="slave-footer">
            <span class="last-seen">更新时间: ${lastSeen}</span>
            <button class="detail-btn" onclick="showSlaveDetail('${slave.device_id}')">
                <i class="fas fa-info-circle"></i>
            </button>
        </div>
    `;

    return card;
}

// 测试从机API连接
function testSlaveAPI() {
    console.log('测试从机API连接...');

    fetch('/api/slaves')
        .then(response => {
            console.log('API响应状态:', response.status, response.statusText);
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            return response.json();
        })
        .then(data => {
            console.log('API连接测试成功，数据:', data);
            return data;
        })
        .catch(error => {
            console.error('API连接测试失败:', error);
            throw error;
        });
}

function refreshSlaves() {
    console.log('刷新从机数据...');

    fetch('/api/slaves')
        .then(response => {
            console.log('API响应状态:', response.status, response.statusText);
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            return response.json();
        })
        .then(data => {
            console.log('获取到从机数据:', data);

            // 更新从机数据存储
            data.forEach(slave => {
                console.log(`处理从机: ${slave.device_id}`, slave);
                slaves[slave.device_id] = {
                    device_id: slave.device_id,
                    device_type: 'slave',
                    slave_name: slave.name,
                    slave_location: slave.location,
                    overall_status: slave.status || 'normal',
                    flame: slave.latest_data?.flame || 0,
                    smoke: slave.latest_data?.smoke || 0,
                    temperature: slave.latest_data?.temperature || 0,
                    humidity: slave.latest_data?.humidity || 0,
                    light_level: slave.latest_data?.light_level || 0,
                    timestamp: slave.latest_data?.timestamp ? new Date(slave.latest_data.timestamp * 1000).toISOString() : null
                };
                console.log(`从机 ${slave.device_id} 数据已更新:`, slaves[slave.device_id]);
            });

            // 更新显示
            updateSlavesDisplay();

            // showNotification('刷新成功', `已加载 ${data.length} 个从机设备`, 'success');
        })
        .catch(error => {
            console.error('刷新从机数据失败:', error);
            console.error('错误详情:', {
                message: error.message,
                stack: error.stack,
                response: error.response
            });
            // showNotification('刷新失败', `无法加载从机数据: ${error.message}`, 'error');
        });
}

function showSlaveDetail(slaveId) {
    const slave = slaves[slaveId];
    if (!slave) {
        // showNotification('错误', '从机数据不存在', 'error');
        return;
    }

    // 创建从机详情模态框
    const modal = document.createElement('div');
    modal.className = 'modal slave-detail-modal';
    modal.innerHTML = `
        <div class="modal-content">
            <div class="modal-header">
                <h3>从机详情 - ${slave.slave_name || slave.device_id}</h3>
                <span class="close-btn" onclick="this.closest('.modal').remove()">&times;</span>
            </div>
            <div class="modal-body">
                <div class="detail-section">
                    <h4>基本信息</h4>
                    <p><strong>设备ID:</strong> ${slave.device_id}</p>
                    <p><strong>设备名称:</strong> ${slave.slave_name || '未设置'}</p>
                    <p><strong>安装位置:</strong> ${slave.slave_location || '未知'}</p>
                    <p><strong>设备类型:</strong> 从机</p>
                </div>
                <div class="detail-section">
                    <h4>传感器数据</h4>
                    <div class="sensor-grid">
                        <div class="sensor-detail">
                            <i class="fas fa-fire"></i>
                            <span class="sensor-name">火焰传感器</span>
                            <span class="sensor-value">${slave.flame || 0}</span>
                        </div>
                        <div class="sensor-detail">
                            <i class="fas fa-smog"></i>
                            <span class="sensor-name">烟雾传感器</span>
                            <span class="sensor-value">${slave.smoke || 0}</span>
                        </div>
                    </div>
                </div>
                <div class="detail-section">
                    <h4>状态信息</h4>
                    <p><strong>当前状态:</strong> ${getStatusName(slave.overall_status || 'normal')}</p>
                    <p><strong>最后更新:</strong> ${slave.timestamp ? new Date(slave.timestamp).toLocaleString() : '未知'}</p>
                </div>
            </div>
            <div class="modal-footer">
                <button class="btn btn-primary" onclick="this.closest('.modal').remove()">关闭</button>
            </div>
        </div>
    `;

    document.body.appendChild(modal);

    // 点击模态框外部关闭
    modal.onclick = function(event) {
        if (event.target === modal) {
            modal.remove();
        }
    };
}

function handleSlaveAlarm(slaveData) {
    console.log('从机报警:', slaveData);

    // 播放报警声音
    playAlarmSound();

    // 显示报警通知
    showNotification(
        '从机火灾警报！',
        `${slaveData.slave_location || slaveData.device_id} 检测到火灾风险！`,
        'alarm'
    );
}

