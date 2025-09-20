// ESP32宿舍火灾报警系统 - 仪表板页面JavaScript

// 全局变量
let socket;
let devices = {};
let charts = {};
let historicalData = {
    temperature: [],
    smoke: [],
    timestamps: []
};

// 页面加载完成后初始化
document.addEventListener('DOMContentLoaded', function() {
    initializeDashboard();
});

// 初始化仪表板
function initializeDashboard() {
    console.log('初始化ESP32火灾报警系统仪表板...');
    
    // 初始化Socket.IO连接
    initializeSocket();
    
    // 初始化图表
    initializeCharts();
    
    // 加载初始数据
    loadInitialData();
    
    // 设置事件监听器
    setupEventListeners();
    
    // 启动定时器
    startTimers();
}

// 初始化Socket.IO连接
function initializeSocket() {
    socket = io();
    
    // 连接成功
    socket.on('connected', function(data) {
        console.log('仪表板Socket.IO连接成功:', data);
        showNotification('连接成功', '仪表板已连接到火灾报警系统', 'success');
    });
    
    // 接收设备状态更新
    socket.on('devices_update', function(deviceData) {
        updateDevices(deviceData);
        updateCharts(deviceData);
        updateStatistics(deviceData);
    });
    
    // 接收报警信息
    socket.on('alarm', function(alarmData) {
        handleAlarm(alarmData);
    });
    
    // 连接错误
    socket.on('connect_error', function(error) {
        console.error('Socket.IO连接错误:', error);
        showNotification('连接错误', '无法连接到服务器', 'error');
    });
}

// 初始化图表
function initializeCharts() {
    // 温度趋势图
    const tempCtx = document.getElementById('temperature-chart');
    if (tempCtx) {
        charts.temperature = new Chart(tempCtx, {
            type: 'line',
            data: {
                labels: [],
                datasets: [{
                    label: '温度 (°C)',
                    data: [],
                    borderColor: '#F44336',
                    backgroundColor: 'rgba(244, 67, 54, 0.1)',
                    borderWidth: 2,
                    fill: true,
                    tension: 0.4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: {
                        beginAtZero: false,
                        min: 15,
                        max: 50
                    }
                },
                plugins: {
                    legend: {
                        display: true,
                        position: 'top'
                    }
                }
            }
        });
    }
    
    // 烟雾水平图
    const smokeCtx = document.getElementById('smoke-chart');
    if (smokeCtx) {
        charts.smoke = new Chart(smokeCtx, {
            type: 'line',
            data: {
                labels: [],
                datasets: [{
                    label: '烟雾水平',
                    data: [],
                    borderColor: '#FF9800',
                    backgroundColor: 'rgba(255, 152, 0, 0.1)',
                    borderWidth: 2,
                    fill: true,
                    tension: 0.4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: {
                        beginAtZero: true,
                        min: 0,
                        max: 600
                    }
                },
                plugins: {
                    legend: {
                        display: true,
                        position: 'top'
                    }
                }
            }
        });
    }
    
    // 设备状态饼图
    const statusCtx = document.getElementById('status-chart');
    if (statusCtx) {
        charts.status = new Chart(statusCtx, {
            type: 'doughnut',
            data: {
                labels: ['正常', '警告', '警报'],
                datasets: [{
                    data: [0, 0, 0],
                    backgroundColor: [
                        '#4CAF50',
                        '#FF9800',
                        '#F44336'
                    ],
                    borderWidth: 2,
                    borderColor: '#fff'
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'bottom'
                    }
                }
            }
        });
    }
}

// 加载初始数据
function loadInitialData() {
    // 通过API获取初始设备数据
    fetch('/api/devices')
        .then(response => response.json())
        .then(data => {
            updateDevices(data);
            updateCharts(data);
            updateStatistics(data);
        })
        .catch(error => {
            console.error('加载设备数据失败:', error);
            showNotification('加载失败', '无法加载设备数据', 'error');
        });
    
    // 加载报警历史
    fetch('/api/history')
        .then(response => response.json())
        .then(data => {
            updateTodayAlarmsCount(data);
        })
        .catch(error => {
            console.error('加载报警历史失败:', error);
        });
}

// 设置事件监听器
function setupEventListeners() {
    // 添加窗口大小改变事件监听器
    window.addEventListener('resize', function() {
        // 重新调整图表大小
        Object.values(charts).forEach(chart => {
            if (chart.resize) {
                chart.resize();
            }
        });
    });
    
    // 添加设备操作按钮事件
    document.addEventListener('click', function(e) {
        if (e.target.classList.contains('action-btn')) {
            const deviceId = e.target.closest('tr').dataset.deviceId;
            const action = e.target.dataset.action;
            
            if (action === 'details') {
                showDeviceDetails(deviceId);
            } else if (action === 'refresh') {
                refreshDevice(deviceId);
            }
        }
    });
}

// 启动定时器
function startTimers() {
    // 每30秒检查一次连接状态
    setInterval(checkConnection, 30000);
    
    // 每10秒更新一次图表数据
    setInterval(updateChartPeriodically, 10000);
}

// 更新设备表格
function updateDevices(deviceData) {
    const tbody = document.getElementById('device-table-body');
    if (!tbody) return;
    
    tbody.innerHTML = '';
    
    deviceData.forEach(device => {
        devices[device.device_id] = device;
        const row = createDeviceTableRow(device);
        tbody.appendChild(row);
    });
}

// 创建设备表格行
function createDeviceTableRow(device) {
    const row = document.createElement('tr');
    row.dataset.deviceId = device.device_id;
    
    const statusBadge = createStatusBadge(device.status);
    const lastUpdate = formatTime(device.last_update);
    
    row.innerHTML = `
        <td>${device.device_id}</td>
        <td>${device.location}</td>
        <td>${device.temperature.toFixed(1)}°C</td>
        <td>${device.smoke_level.toFixed(0)}</td>
        <td>${statusBadge}</td>
        <td>${lastUpdate}</td>
        <td>
            <button class="action-btn primary" data-action="details">
                <i class="fas fa-info-circle"></i> 详情
            </button>
        </td>
    `;
    
    // 根据状态设置行背景色
    if (device.status === '警报') {
        row.style.backgroundColor = '#ffebee';
    } else if (device.status === '警告') {
        row.style.backgroundColor = '#fff3e0';
    }
    
    return row;
}

// 创建状态徽章
function createStatusBadge(status) {
    const badges = {
        '正常': '<span style="color: #4CAF50; font-weight: bold;">✓ 正常</span>',
        '警告': '<span style="color: #FF9800; font-weight: bold;">⚠ 警告</span>',
        '警报': '<span style="color: #F44336; font-weight: bold;">🚨 警报</span>'
    };
    return badges[status] || status;
}

// 更新图表
function updateCharts(deviceData) {
    const currentTime = new Date().toLocaleTimeString();
    
    // 计算平均值
    const avgTemp = deviceData.reduce((sum, device) => sum + device.temperature, 0) / deviceData.length;
    const avgSmoke = deviceData.reduce((sum, device) => sum + device.smoke_level, 0) / deviceData.length;
    
    // 更新历史数据（保留最近20个数据点）
    historicalData.timestamps.push(currentTime);
    historicalData.temperature.push(avgTemp);
    historicalData.smoke.push(avgSmoke);
    
    if (historicalData.timestamps.length > 20) {
        historicalData.timestamps.shift();
        historicalData.temperature.shift();
        historicalData.smoke.shift();
    }
    
    // 更新温度图表
    if (charts.temperature) {
        charts.temperature.data.labels = historicalData.timestamps;
        charts.temperature.data.datasets[0].data = historicalData.temperature;
        charts.temperature.update('none'); // 无动画更新以提高性能
    }
    
    // 更新烟雾图表
    if (charts.smoke) {
        charts.smoke.data.labels = historicalData.timestamps;
        charts.smoke.data.datasets[0].data = historicalData.smoke;
        charts.smoke.update('none');
    }
    
    // 更新状态饼图
    if (charts.status) {
        const statusCounts = {
            normal: 0,
            warning: 0,
            alarm: 0
        };
        
        deviceData.forEach(device => {
            const status = device.status.toLowerCase();
            if (statusCounts.hasOwnProperty(status)) {
                statusCounts[status]++;
            }
        });
        
        charts.status.data.datasets[0].data = [
            statusCounts.normal,
            statusCounts.warning,
            statusCounts.alarm
        ];
        charts.status.update('none');
    }
}

// 更新统计信息
function updateStatistics(deviceData) {
    // 计算统计数据
    const totalDevices = deviceData.length;
    const avgTemp = deviceData.reduce((sum, device) => sum + device.temperature, 0) / totalDevices;
    const avgSmoke = deviceData.reduce((sum, device) => sum + device.smoke_level, 0) / totalDevices;
    
    // 更新显示
    const totalDevicesElement = document.getElementById('total-devices');
    const avgTempElement = document.getElementById('avg-temperature');
    const avgSmokeElement = document.getElementById('avg-smoke');
    
    if (totalDevicesElement) totalDevicesElement.textContent = totalDevices;
    if (avgTempElement) avgTempElement.textContent = avgTemp.toFixed(1) + '°C';
    if (avgSmokeElement) avgSmokeElement.textContent = avgSmoke.toFixed(0);
}

// 更新今日报警计数
function updateTodayAlarmsCount(alarmData) {
    const today = new Date().toDateString();
    const todayAlarms = alarmData.filter(alarm => 
        new Date(alarm.timestamp * 1000).toDateString() === today
    );
    
    const todayAlarmsElement = document.getElementById('today-alarms');
    if (todayAlarmsElement) {
        todayAlarmsElement.textContent = todayAlarms.length;
    }
}

// 定期更新图表
function updateChartPeriodically() {
    // 如果没有收到新的数据，保持图表显示
    if (Object.keys(devices).length > 0) {
        const deviceArray = Object.values(devices);
        updateCharts(deviceArray);
    }
}

// 处理报警
function handleAlarm(alarmData) {
    console.log('仪表板收到报警:', alarmData);
    
    // 播放报警声音
    playAlarmSound();
    
    // 显示报警通知
    showNotification(
        '火灾警报！',
        `${alarmData.location} 检测到火灾风险！`,
        'alarm'
    );
    
    // 浏览器通知
    showBrowserNotification('火灾警报', alarmData.message);
    
    // 更新今日报警计数
    const todayAlarmsElement = document.getElementById('today-alarms');
    if (todayAlarmsElement) {
        const currentCount = parseInt(todayAlarmsElement.textContent) || 0;
        todayAlarmsElement.textContent = currentCount + 1;
    }
}

// 显示设备详情
function showDeviceDetails(deviceId) {
    const device = devices[deviceId];
    if (!device) return;
    
    // 创建详细信息的模态框
    const modal = document.createElement('div');
    modal.className = 'modal';
    modal.innerHTML = `
        <div class="modal-content">
            <div class="modal-header">
                <h3>设备详细信息 - ${device.device_id}</h3>
                <button class="modal-close" onclick="this.closest('.modal').remove()">
                    <i class="fas fa-times"></i>
                </button>
            </div>
            <div class="modal-body">
                <div class="detail-grid">
                    <div class="detail-item">
                        <label>设备ID:</label>
                        <span>${device.device_id}</span>
                    </div>
                    <div class="detail-item">
                        <label>位置:</label>
                        <span>${device.location}</span>
                    </div>
                    <div class="detail-item">
                        <label>当前温度:</label>
                        <span class="temp-value">${device.temperature.toFixed(1)}°C</span>
                    </div>
                    <div class="detail-item">
                        <label>烟雾水平:</label>
                        <span class="smoke-value">${device.smoke_level.toFixed(0)}</span>
                    </div>
                    <div class="detail-item">
                        <label>设备状态:</label>
                        <span>${createStatusBadge(device.status)}</span>
                    </div>
                    <div class="detail-item">
                        <label>最后更新:</label>
                        <span>${formatTime(device.last_update)}</span>
                    </div>
                </div>
                
                <div class="device-charts">
                    <h4>实时趋势</h4>
                    <canvas id="device-detail-chart" width="400" height="200"></canvas>
                </div>
            </div>
        </div>
    `;
    
    document.body.appendChild(modal);
    
    // 创建设备详情图表
    setTimeout(() => {
        createDeviceDetailChart(deviceId);
    }, 100);
    
    // 点击背景关闭
    modal.addEventListener('click', function(e) {
        if (e.target === modal) {
            modal.remove();
        }
    });
}

// 创建设备详情图表
function createDeviceDetailChart(deviceId) {
    const ctx = document.getElementById('device-detail-chart');
    if (!ctx) return;
    
    // 生成模拟历史数据
    const labels = [];
    const tempData = [];
    const smokeData = [];
    
    for (let i = 19; i >= 0; i--) {
        const time = new Date(Date.now() - i * 60000).toLocaleTimeString();
        labels.push(time);
        
        // 基于当前值生成历史数据
        const device = devices[deviceId];
        if (device) {
            tempData.push(device.temperature + (Math.random() - 0.5) * 2);
            smokeData.push(Math.max(0, device.smoke_level + (Math.random() - 0.5) * 10));
        }
    }
    
    new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [{
                label: '温度 (°C)',
                data: tempData,
                borderColor: '#F44336',
                backgroundColor: 'rgba(244, 67, 54, 0.1)',
                yAxisID: 'y-temp',
                tension: 0.4
            }, {
                label: '烟雾水平',
                data: smokeData,
                borderColor: '#FF9800',
                backgroundColor: 'rgba(255, 152, 0, 0.1)',
                yAxisID: 'y-smoke',
                tension: 0.4
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: {
                mode: 'index',
                intersect: false,
            },
            scales: {
                'y-temp': {
                    type: 'linear',
                    display: true,
                    position: 'left',
                    title: {
                        display: true,
                        text: '温度 (°C)'
                    }
                },
                'y-smoke': {
                    type: 'linear',
                    display: true,
                    position: 'right',
                    title: {
                        display: true,
                        text: '烟雾水平'
                    },
                    grid: {
                        drawOnChartArea: false,
                    },
                }
            },
            plugins: {
                legend: {
                    position: 'top'
                }
            }
        }
    });
}

// 刷新设备数据
function refreshDevice(deviceId) {
    // 显示加载状态
    const button = document.querySelector(`tr[data-device-id="${deviceId}"] .action-btn`);
    if (button) {
        const originalText = button.innerHTML;
        button.innerHTML = '<i class="fas fa-spinner fa-spin"></i> 刷新中...';
        button.disabled = true;
        
        // 模拟刷新延迟
        setTimeout(() => {
            button.innerHTML = originalText;
            button.disabled = false;
            showNotification('刷新成功', `设备 ${deviceId} 数据已更新`, 'success');
        }, 1000);
    }
}

// 检查连接状态
function checkConnection() {
    if (socket && !socket.connected) {
        showNotification('连接断开', '正在尝试重新连接...', 'warning');
    }
}

// 格式化时间
function formatTime(timestamp) {
    const date = new Date(timestamp * 1000);
    const now = new Date();
    const diff = now - date;
    
    if (diff < 60000) {
        return '刚刚';
    } else if (diff < 3600000) {
        return Math.floor(diff / 60000) + '分钟前';
    } else if (diff < 86400000) {
        return Math.floor(diff / 3600000) + '小时前';
    } else {
        return date.toLocaleString('zh-CN');
    }
}

// 显示通知
function showNotification(title, message, type = 'info') {
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
    
    document.body.appendChild(notification);
    
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
            icon: '/static/img/fire-alarm-icon.png'
        });
    }
}

// 播放报警声音
function playAlarmSound() {
    // 使用Web Audio API创建报警声音
    const audioContext = new (window.AudioContext || window.webkitAudioContext)();
    const oscillator = audioContext.createOscillator();
    const gainNode = audioContext.createGain();
    
    oscillator.connect(gainNode);
    gainNode.connect(audioContext.destination);
    
    oscillator.frequency.setValueAtTime(800, audioContext.currentTime);
    gainNode.gain.setValueAtTime(0.3, audioContext.currentTime);
    
    oscillator.start();
    oscillator.stop(audioContext.currentTime + 0.5);
}

// 添加仪表板专用样式
const dashboardStyles = `
.detail-grid {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 15px;
    margin-bottom: 20px;
}

.detail-item {
    display: flex;
    flex-direction: column;
    padding: 10px;
    background: #f8f9fa;
    border-radius: 6px;
}

.detail-item label {
    font-weight: bold;
    color: #666;
    margin-bottom: 5px;
    font-size: 0.9rem;
}

.detail-item span {
    color: #333;
    font-size: 1.1rem;
}

.temp-value {
    color: #F44336 !important;
    font-weight: bold;
}

.smoke-value {
    color: #FF9800 !important;
    font-weight: bold;
}

.device-charts {
    margin-top: 20px;
    padding-top: 20px;
    border-top: 1px solid #eee;
}

.device-charts h4 {
    margin-bottom: 15px;
    color: #333;
}

.chart-container {
    height: 300px;
    position: relative;
}

@media (max-width: 768px) {
    .detail-grid {
        grid-template-columns: 1fr;
    }
    
    .charts-grid {
        grid-template-columns: 1fr;
    }
}
`;

// 添加样式到页面
if (!document.querySelector('#dashboard-styles')) {
    const styleElement = document.createElement('style');
    styleElement.id = 'dashboard-styles';
    styleElement.textContent = dashboardStyles;
    document.head.appendChild(styleElement);
}

// 页面卸载时清理
window.addEventListener('beforeunload', function() {
    if (socket) {
        socket.disconnect();
    }
    
    // 清理图表
    Object.values(charts).forEach(chart => {
        if (chart.destroy) {
            chart.destroy();
        }
    });
});