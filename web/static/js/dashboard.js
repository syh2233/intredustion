// ESP32宿舍火灾报警系统 - 历史数据中心JavaScript

// 全局变量
let currentHistoryData = null;
let availableDevices = [];
let currentPage = 1;
let recordsPerPage = 100;
let totalRecords = 0;

// 页面加载完成后初始化
document.addEventListener('DOMContentLoaded', function() {
    initializeHistoryDashboard();
});

// 初始化历史数据仪表板
function initializeHistoryDashboard() {
    console.log('初始化ESP32火灾报警系统历史数据仪表板...');

    // 加载可用设备列表
    loadAvailableDevices();

    // 设置事件监听器
    setupEventListeners();

    // 加载初始数据
    loadHistoryData();

    // 设置自动刷新（每5分钟）
    setInterval(autoRefresh, 300000);
}


// 加载可用设备列表
function loadAvailableDevices() {
    fetch('/api/devices/all')
        .then(response => response.json())
        .then(devices => {
            availableDevices = devices;
            updateDeviceSelect(devices);
        })
        .catch(error => {
            console.error('加载设备列表失败:', error);
            showNotification('加载失败', '无法加载设备列表', 'error');
        });
}

// 更新设备选择下拉框
function updateDeviceSelect(devices) {
    const deviceSelect = document.getElementById('device-id');
    if (!deviceSelect) return;

    deviceSelect.innerHTML = '<option value="">所有设备</option>';

    devices.forEach(device => {
        const option = document.createElement('option');
        option.value = device.device_id;
        option.textContent = `${device.device_id} (${device.device_type === 'master' ? '主机' : '从机'} - ${device.location})`;
        deviceSelect.appendChild(option);
    });
}

// 设置事件监听器
function setupEventListeners() {
    // 时间范围选择
    const timeRangeSelect = document.getElementById('time-range');
    if (timeRangeSelect) {
        timeRangeSelect.addEventListener('change', () => {
            currentPage = 1; // 重置页码
            loadHistoryData();
        });
    }

    // 设备类型选择
    const deviceTypeSelect = document.getElementById('device-type');
    if (deviceTypeSelect) {
        deviceTypeSelect.addEventListener('change', () => {
            filterDeviceOptions();
            currentPage = 1; // 重置页码
            loadHistoryData();
        });
    }

    // 设备ID选择
    const deviceIdSelect = document.getElementById('device-id');
    if (deviceIdSelect) {
        deviceIdSelect.addEventListener('change', () => {
            currentPage = 1; // 重置页码
            loadHistoryData();
        });
    }

    // 刷新按钮
    const refreshBtn = document.getElementById('refresh-btn');
    if (refreshBtn) {
        refreshBtn.addEventListener('click', () => {
            refreshBtn.disabled = true;
            refreshBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> 刷新中...';

            loadHistoryData().finally(() => {
                setTimeout(() => {
                    refreshBtn.disabled = false;
                    refreshBtn.innerHTML = '<i class="fas fa-sync-alt"></i> 刷新数据';
                }, 1000);
            });
        });
    }

    // 分页按钮
    const prevBtn = document.getElementById('prev-page-btn');
    const nextBtn = document.getElementById('next-page-btn');

    if (prevBtn) {
        prevBtn.addEventListener('click', () => {
            if (currentPage > 1) {
                currentPage--;
                updateRecordsTable();
            }
        });
    }

    if (nextBtn) {
        nextBtn.addEventListener('click', () => {
            const maxPage = Math.ceil(totalRecords / recordsPerPage);
            if (currentPage < maxPage) {
                currentPage++;
                updateRecordsTable();
            }
        });
    }
}

// 根据设备类型过滤设备选项
function filterDeviceOptions() {
    const deviceType = document.getElementById('device-type').value;
    const deviceIdSelect = document.getElementById('device-id');

    if (!deviceIdSelect) return;

    const currentValue = deviceIdSelect.value;
    deviceIdSelect.innerHTML = '<option value="">所有设备</option>';

    const filteredDevices = deviceType === 'all'
        ? availableDevices
        : availableDevices.filter(device => device.device_type === deviceType);

    filteredDevices.forEach(device => {
        const option = document.createElement('option');
        option.value = device.device_id;
        option.textContent = `${device.device_id} (${device.device_type === 'master' ? '主机' : '从机'} - ${device.location})`;
        deviceIdSelect.appendChild(option);
    });

    // 恢复之前的选择（如果仍然有效）
    if (currentValue && filteredDevices.some(device => device.device_id === currentValue)) {
        deviceIdSelect.value = currentValue;
    }
}

// 加载历史数据
async function loadHistoryData() {
    try {
        showLoading(true);

        const hours = document.getElementById('time-range').value;
        const deviceType = document.getElementById('device-type').value;
        const deviceId = document.getElementById('device-id').value;

        // 构建查询参数
        const params = new URLSearchParams({
            hours: hours,
            device_type: deviceType
        });

        if (deviceId) {
            params.append('device_id', deviceId);
        }

        // 获取历史数据
        const historyResponse = await fetch(`/api/history/dashboard?${params}`);
        const historyData = await historyResponse.json();
        console.log('API response - historyData:', historyData);
        console.log('Devices count in historyData:', historyData.devices ? historyData.devices.length : 'undefined');

        // 获取统计摘要
        const summaryResponse = await fetch(`/api/history/summary?${params}`);
        const summaryData = await summaryResponse.json();
        console.log('API response - summaryData:', summaryData);

        if (!historyResponse.ok || !summaryResponse.ok) {
            throw new Error('获取历史数据失败');
        }

        // 如果没有数据，尝试使用现有的数据范围API
        if (historyData.devices.length === 0) {
            console.log('当前时间范围无数据，尝试获取现有数据...');
            await loadExistingData();
            showLoading(false);
            return;
        }

        currentHistoryData = historyData;

        // 更新界面
        updateHistoryTable(historyData.devices);
        updateStatistics(summaryData.statistics);

        showLoading(false);
        showNotification('加载成功', `已加载${hours}小时的历史数据`, 'success');

    } catch (error) {
        console.error('加载历史数据失败:', error);
        showLoading(false);
        showNotification('加载失败', '无法加载历史数据', 'error');
    }
}

// 加载现有数据（备用方案）
async function loadExistingData() {
    try {
        // 使用绝对时间范围查询现有数据，获取前1000条
        const startResponse = await fetch('/api/data/range?start=2025-10-24T00:00:00Z&end=2025-10-26T00:00:00Z&limit=1000');
        const data = await startResponse.json();

        if (!startResponse.ok || !Array.isArray(data) || data.length === 0) {
            showNotification('无历史数据', '数据库中没有找到历史数据记录', 'warning');
            return;
        }

        // 获取设备信息
        const devicesResponse = await fetch('/api/devices/all');
        const devices = await devicesResponse.json();

        const deviceInfoMap = {};
        devices.forEach(device => {
            deviceInfoMap[device.device_id] = {
                device_type: device.device_type,
                location: device.location,
                status: device.status
            };
        });

        // 为每条记录添加设备信息
        const recordsWithDeviceInfo = data.map(record => ({
            ...record,
            device_type: deviceInfoMap[record.device_id]?.device_type || 'unknown',
            location: deviceInfoMap[record.device_id]?.location || '未知'
        }));

        currentHistoryData = {
            records: recordsWithDeviceInfo,
            time_range: {
                start: '2025-10-24T00:00:00Z',
                end: '2025-10-26T00:00:00Z',
                hours: 48
            }
        };

        totalRecords = recordsWithDeviceInfo.length;
        currentPage = 1;

        // 更新界面
        updateRecordsTable();
        updateRecordsInfo();
        updateStatisticsFromRecords(recordsWithDeviceInfo);

        showNotification('加载成功', `已加载现有历史数据 (${data.length} 条记录)`, 'success');

    } catch (error) {
        console.error('加载现有数据失败:', error);
        showNotification('加载失败', '无法加载现有历史数据', 'error');
    }
}

// 更新数据记录表格
function updateRecordsTable() {
    const tbody = document.getElementById('history-table-body');
    if (!tbody || !currentHistoryData || !currentHistoryData.records) return;

    tbody.innerHTML = '';

    if (currentHistoryData.records.length === 0) {
        tbody.innerHTML = '<tr><td colspan="9" style="text-align: center; color: #666;">暂无历史数据</td></tr>';
        return;
    }

    // 计算分页
    const startIndex = (currentPage - 1) * recordsPerPage;
    const endIndex = Math.min(startIndex + recordsPerPage, currentHistoryData.records.length);
    const pageRecords = currentHistoryData.records.slice(startIndex, endIndex);

    pageRecords.forEach(record => {
        const row = document.createElement('tr');

        const deviceTypeLabel = record.device_type === 'master' ? '主机' :
                              record.device_type === 'slave' ? '从机' : '未知';
        const deviceTypeClass = record.device_type === 'master' ? 'master-type' :
                              record.device_type === 'slave' ? 'slave-type' : 'unknown-type';

        const statusBadge = getStatusBadge(record.alert);

        row.innerHTML = `
            <td>${formatDateTime(record.timestamp)}</td>
            <td>${record.device_id}</td>
            <td><span class="${deviceTypeClass}">${deviceTypeLabel}</span></td>
            <td>${record.temperature ? record.temperature.toFixed(1) + '°C' : '--'}</td>
            <td>${record.smoke || '--'}</td>
            <td>${record.flame || '--'}</td>
            <td>${record.humidity ? record.humidity.toFixed(1) + '%' : '--'}</td>
            <td>${record.light || '--'}</td>
            <td>${statusBadge}</td>
        `;

        tbody.appendChild(row);
    });

    // 更新分页按钮状态
    updatePaginationButtons();
}

// 更新记录信息
function updateRecordsInfo() {
    const countElement = document.getElementById('records-count');
    const timeRangeElement = document.getElementById('records-time-range');

    if (countElement) {
        countElement.textContent = `共 ${totalRecords} 条记录`;
    }

    if (timeRangeElement && currentHistoryData && currentHistoryData.time_range) {
        const startDate = new Date(currentHistoryData.time_range.start);
        const endDate = new Date(currentHistoryData.time_range.end);
        timeRangeElement.textContent = `时间范围: ${startDate.toLocaleDateString()} - ${endDate.toLocaleDateString()}`;
    }
}

// 更新分页按钮
function updatePaginationButtons() {
    const prevBtn = document.getElementById('prev-page-btn');
    const nextBtn = document.getElementById('next-page-btn');
    const pageInfo = document.getElementById('page-info');

    const maxPage = Math.ceil(totalRecords / recordsPerPage);

    if (prevBtn) {
        prevBtn.disabled = currentPage <= 1;
    }

    if (nextBtn) {
        nextBtn.disabled = currentPage >= maxPage;
    }

    if (pageInfo) {
        pageInfo.textContent = `第 ${currentPage} 页 / 共 ${maxPage} 页`;
    }
}

// 获取状态徽章
function getStatusBadge(alertStatus) {
    const badges = {
        'normal': '<span style="color: #4CAF50; font-weight: bold;">✓ 正常</span>',
        'warning': '<span style="color: #FF9800; font-weight: bold;">⚠ 警告</span>',
        'alarm': '<span style="color: #F44336; font-weight: bold;">🚨 警报</span>'
    };
    return badges[alertStatus] || '<span style="color: #666;">--</span>';
}

// 更新历史数据表格
function updateHistoryTable(devices) {
    const tbody = document.getElementById('history-table-body');
    if (!tbody) {
        console.error('updateHistoryTable: tbody element not found');
        return;
    }

    console.log('updateHistoryTable called with devices:', devices);
    tbody.innerHTML = '';

    if (!devices || devices.length === 0) {
        console.log('updateHistoryTable: no devices data');
        tbody.innerHTML = '<tr><td colspan="9" style="text-align: center; color: #666;">暂无历史数据</td></tr>';
        return;
    }

    // 将所有设备的数据合并到一个数组中
    const allRecords = [];
    console.log('Processing devices for records...');
    devices.forEach((device, index) => {
        console.log(`Device ${index + 1}:`, device.device_id, 'data points:', device.data ? device.data.length : 'none');
        if (device.data && Array.isArray(device.data)) {
            device.data.forEach(record => {
                allRecords.push({
                    timestamp: record.timestamp,
                    device_id: device.device_id,
                    device_type: device.device_type,
                    temperature: record.temperature,
                    smoke: record.smoke,
                    flame: record.flame,
                    humidity: record.humidity,
                    light_level: record.light,
                    alert: record.alert
                });
            });
        }
    });
    console.log('Total allRecords after processing:', allRecords.length);

    // 按时间排序（最新的在前）
    allRecords.sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp));

    // 更新记录计数
    const recordsCountElement = document.getElementById('records-count');
    if (recordsCountElement) {
        recordsCountElement.textContent = `共 ${allRecords.length} 条记录`;
    }

    // 分页显示
    const startIndex = (currentPage - 1) * recordsPerPage;
    const endIndex = Math.min(startIndex + recordsPerPage, allRecords.length);
    const pageRecords = allRecords.slice(startIndex, endIndex);

    pageRecords.forEach(record => {
        const row = document.createElement('tr');

        const deviceTypeLabel = record.device_type === 'master' ? '主机' :
                              record.device_type === 'slave' ? '从机' : '未知';
        const deviceTypeClass = record.device_type === 'master' ? 'master-type' :
                              record.device_type === 'slave' ? 'slave-type' : 'unknown-type';

        const statusBadge = getStatusBadge(record.alert);

        row.innerHTML = `
            <td>${formatDateTime(record.timestamp)}</td>
            <td>${record.device_id}</td>
            <td><span class="${deviceTypeClass}">${deviceTypeLabel}</span></td>
            <td>${record.temperature || '--'}°C</td>
            <td>${record.smoke || '--'}</td>
            <td>${record.flame || '--'}</td>
            <td>${record.humidity || '--'}%</td>
            <td>${record.light_level || '--'}</td>
            <td>${statusBadge}</td>
        `;

        tbody.appendChild(row);
    });

    // 更新分页信息
    updatePagination(allRecords.length);
}

// 更新分页信息
function updatePagination(totalRecords) {
    const pageInfo = document.getElementById('page-info');
    const prevBtn = document.getElementById('prev-page-btn');
    const nextBtn = document.getElementById('next-page-btn');
    const totalPages = Math.ceil(totalRecords / recordsPerPage);

    if (pageInfo) {
        pageInfo.textContent = `第 ${currentPage} 页，共 ${totalPages} 页`;
    }

    if (prevBtn) {
        prevBtn.disabled = currentPage <= 1;
    }

    if (nextBtn) {
        nextBtn.disabled = currentPage >= totalPages;
    }
}

// 更新统计信息
function updateStatistics(statistics) {
    const elements = {
        'total-records': statistics.total_records || 0,
        'avg-temperature': (statistics.avg_temperature || 0).toFixed(1) + '°C',
        'avg-smoke': (statistics.avg_smoke || 0).toFixed(0),
        'total-alarms': statistics.alert_count || 0,
        'max-temperature': (statistics.max_temperature || 0).toFixed(1) + '°C',
        'avg-flame': (statistics.avg_flame || 0).toFixed(0)
    };

    Object.entries(elements).forEach(([id, value]) => {
        const element = document.getElementById(id);
        if (element) {
            element.textContent = value;
        }
    });
}

// 从记录数据计算统计信息
function updateStatisticsFromRecords(records) {
    if (!records || records.length === 0) {
        updateStatistics({
            total_records: 0,
            avg_temperature: 0,
            avg_smoke: 0,
            max_temperature: 0,
            avg_flame: 0,
            alert_count: 0
        });
        return;
    }

    const temps = records.map(r => r.temperature).filter(t => t != null);
    const smokes = records.map(r => r.smoke).filter(s => s != null);
    const flames = records.map(r => r.flame).filter(f => f != null);
    const alerts = records.filter(r => ['warning', 'alarm'].includes(r.alert));

    const statistics = {
        total_records: records.length,
        avg_temperature: temps.length > 0 ? temps.reduce((a, b) => a + b, 0) / temps.length : 0,
        avg_smoke: smokes.length > 0 ? smokes.reduce((a, b) => a + b, 0) / smokes.length : 0,
        max_temperature: temps.length > 0 ? Math.max(...temps) : 0,
        avg_flame: flames.length > 0 ? flames.reduce((a, b) => a + b, 0) / flames.length : 0,
        alert_count: alerts.length
    };

    updateStatistics(statistics);
}

// 自动刷新
function autoRefresh() {
    console.log('自动刷新历史数据...');
    loadHistoryData();
}

// 显示/隐藏加载状态
function showLoading(show) {
    const loadingElements = document.querySelectorAll('.loading-overlay');
    loadingElements.forEach(element => {
        element.style.display = show ? 'block' : 'none';
    });

    // 如果没有专门的加载遮罩，创建一个
    if (show && loadingElements.length === 0) {
        const overlay = document.createElement('div');
        overlay.className = 'loading-overlay';
        overlay.innerHTML = `
            <div class="loading-spinner">
                <i class="fas fa-spinner fa-spin"></i>
                <p>正在加载历史数据...</p>
            </div>
        `;
        overlay.style.cssText = `
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0, 0, 0, 0.5);
            display: flex;
            justify-content: center;
            align-items: center;
            z-index: 9999;
            color: white;
            font-size: 18px;
        `;
        document.body.appendChild(overlay);
    } else if (!show) {
        loadingElements.forEach(element => element.remove());
    }
}

// 格式化日期时间
function formatDateTime(timestamp) {
    if (!timestamp) return '--';

    try {
        const date = new Date(timestamp);
        return date.toLocaleString('zh-CN', {
            year: 'numeric',
            month: '2-digit',
            day: '2-digit',
            hour: '2-digit',
            minute: '2-digit'
        });
    } catch (error) {
        return '--';
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

    notification.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        background: ${type === 'success' ? '#4CAF50' : type === 'error' ? '#F44336' : type === 'warning' ? '#FF9800' : '#2196F3'};
        color: white;
        padding: 15px 20px;
        border-radius: 8px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.3);
        z-index: 10000;
        max-width: 400px;
        animation: slideIn 0.3s ease;
    `;

    document.body.appendChild(notification);

    setTimeout(() => {
        if (notification.parentElement) {
            notification.remove();
        }
    }, 5000);
}

// 添加历史数据中心专用样式
const historyDashboardStyles = `
.filter-section {
    background: #f8f9fa;
    padding: 20px;
    border-radius: 10px;
    margin: 20px 0;
    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
}

.filter-container {
    display: flex;
    flex-wrap: wrap;
    gap: 20px;
    align-items: end;
}

.filter-group {
    display: flex;
    flex-direction: column;
    min-width: 150px;
}

.filter-group label {
    font-weight: bold;
    margin-bottom: 5px;
    color: #333;
}

.filter-select, .refresh-btn {
    padding: 8px 12px;
    border: 1px solid #ddd;
    border-radius: 5px;
    background: white;
    font-size: 14px;
}

.refresh-btn {
    background: #2196F3;
    color: white;
    border: none;
    cursor: pointer;
    transition: background 0.3s;
}

.refresh-btn:hover:not(:disabled) {
    background: #1976D2;
}

.refresh-btn:disabled {
    opacity: 0.6;
    cursor: not-allowed;
}

.records-controls {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin: 20px 0;
    padding: 15px;
    background: white;
    border-radius: 8px;
    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
}

.records-info {
    display: flex;
    gap: 20px;
    align-items: center;
}

.records-info span {
    color: #666;
    font-size: 14px;
}

.records-pagination {
    display: flex;
    align-items: center;
    gap: 10px;
}

.records-pagination button {
    padding: 6px 12px;
    border: 1px solid #ddd;
    border-radius: 5px;
    background: white;
    cursor: pointer;
    transition: all 0.3s;
}

.records-pagination button:hover:not(:disabled) {
    background: #f0f0f0;
}

.records-pagination button:disabled {
    opacity: 0.5;
    cursor: not-allowed;
}

.records-pagination span {
    color: #333;
    font-weight: bold;
    min-width: 100px;
    text-align: center;
}

.history-table-container {
    overflow-x: auto;
    margin: 20px 0;
    max-height: 600px;
    overflow-y: auto;
}

.history-table {
    width: 100%;
    border-collapse: collapse;
    background: white;
    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    border-radius: 8px;
    overflow: hidden;
}

.history-table th,
.history-table td {
    padding: 10px 12px;
    text-align: left;
    border-bottom: 1px solid #eee;
    white-space: nowrap;
}

.history-table th {
    background: #f5f5f5;
    font-weight: bold;
    color: #333;
    position: sticky;
    top: 0;
    z-index: 10;
}

.history-table tr:hover {
    background: #f9f9f9;
}

.master-type {
    background: #ffebee;
    color: #c62828;
    padding: 2px 8px;
    border-radius: 12px;
    font-size: 12px;
    font-weight: bold;
}

.slave-type {
    background: #e3f2fd;
    color: #1565c0;
    padding: 2px 8px;
    border-radius: 12px;
    font-size: 12px;
    font-weight: bold;
}

.unknown-type {
    background: #f5f5f5;
    color: #666;
    padding: 2px 8px;
    border-radius: 12px;
    font-size: 12px;
    font-weight: bold;
}

.stats-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
    gap: 20px;
    margin: 20px 0;
}

.stat-card {
    background: white;
    padding: 20px;
    border-radius: 10px;
    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    text-align: center;
}

.stat-icon {
    font-size: 24px;
    color: #2196F3;
    margin-bottom: 10px;
}

.stat-content h4 {
    margin: 0 0 5px 0;
    color: #666;
    font-size: 14px;
}

.stat-value {
    margin: 0;
    font-size: 24px;
    font-weight: bold;
    color: #333;
}

@keyframes slideIn {
    from {
        transform: translateX(100%);
        opacity: 0;
    }
    to {
        transform: translateX(0);
        opacity: 1;
    }
}

@media (max-width: 768px) {
    .filter-container {
        flex-direction: column;
        align-items: stretch;
    }

    .filter-group {
        min-width: auto;
    }

    .records-controls {
        flex-direction: column;
        gap: 15px;
    }

    .records-info {
        flex-direction: column;
        gap: 10px;
        align-items: flex-start;
    }

    .stats-grid {
        grid-template-columns: repeat(2, 1fr);
    }

    .history-table-container {
        font-size: 12px;
    }

    .history-table th,
    .history-table td {
        padding: 8px 6px;
    }
}
`;

// 添加样式到页面
if (!document.querySelector('#history-dashboard-styles')) {
    const styleElement = document.createElement('style');
    styleElement.id = 'history-dashboard-styles';
    styleElement.textContent = historyDashboardStyles;
    document.head.appendChild(styleElement);
}

