-- =====================================================================
-- ESP32火灾报警系统数据库重置脚本
-- 功能：删除并重新创建所有表，添加默认数据
-- 使用方法：在SQLite命令行中执行 .read reset_database.sql
-- =====================================================================

-- 删除所有已存在的表
DROP TABLE IF EXISTS sensor_data;
DROP TABLE IF EXISTS alert_history;
DROP TABLE IF EXISTS device_info;

-- 重新创建表结构

-- 传感器数据表
CREATE TABLE sensor_data (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    device_id VARCHAR(50) NOT NULL,
    device_type VARCHAR(20) DEFAULT 'master',  -- 'master' or 'slave'
    flame_value INTEGER NOT NULL,
    smoke_value INTEGER NOT NULL,
    temperature REAL,
    humidity REAL,
    light_level REAL,  -- 光照传感器
    alert_status BOOLEAN DEFAULT FALSE,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 报警历史表
CREATE TABLE alert_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    device_id VARCHAR(50) NOT NULL,
    alert_type VARCHAR(20) NOT NULL,
    severity VARCHAR(10) NOT NULL,
    flame_value INTEGER,
    smoke_value INTEGER,
    temperature REAL,
    humidity REAL,
    light_level REAL,  -- 光照传感器
    location VARCHAR(100),
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    resolved BOOLEAN DEFAULT FALSE,
    resolved_time DATETIME
);

-- 设备信息表
CREATE TABLE device_info (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    device_id VARCHAR(50) UNIQUE NOT NULL,
    name VARCHAR(100) NOT NULL,
    location VARCHAR(200),
    ip_address VARCHAR(15),
    device_type VARCHAR(20) DEFAULT 'master',  -- 'master' or 'slave'
    master_id VARCHAR(50),  -- 对于从机，记录其所属的主机ID
    last_seen DATETIME,
    status VARCHAR(20) DEFAULT 'online',
    config TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 创建索引以提高查询性能
CREATE INDEX idx_sensor_data_device_id ON sensor_data(device_id);
CREATE INDEX idx_sensor_data_timestamp ON sensor_data(timestamp);
CREATE INDEX idx_alert_history_device_id ON alert_history(device_id);
CREATE INDEX idx_alert_history_timestamp ON alert_history(timestamp);
CREATE INDEX idx_device_info_device_id ON device_info(device_id);
CREATE INDEX idx_device_info_master_id ON device_info(master_id);

-- 插入默认设备数据

-- 默认主机设备
INSERT INTO device_info (
    device_id,
    name,
    location,
    device_type,
    status,
    created_at
) VALUES (
    'esp32_fire_alarm_01',
    'ESP32火灾报警主机',
    '宿舍A栋101',
    'master',
    'online',
    datetime('now', '+8 hours')  -- 北京时间
);

-- 默认从机设备
INSERT INTO device_info (
    device_id,
    name,
    location,
    device_type,
    master_id,
    status,
    created_at
) VALUES (
    'esp32_slave_01',
    'ESP32从机-01',
    '宿舍A栋102',
    'slave',
    'esp32_fire_alarm_01',
    'online',
    datetime('now', '+8 hours')  -- 北京时间
);

-- 插入示例传感器数据（可选，用于测试）
INSERT INTO sensor_data (
    device_id,
    device_type,
    flame_value,
    smoke_value,
    temperature,
    humidity,
    light_level,
    alert_status,
    timestamp
) VALUES (
    'esp32_fire_alarm_01',
    'master',
    1200,
    1800,
    25.5,
    60.2,
    15.3,
    FALSE,
    datetime('now', '+8 hours')
);

-- 插入示例报警历史（可选，用于测试）
INSERT INTO alert_history (
    device_id,
    alert_type,
    severity,
    flame_value,
    smoke_value,
    temperature,
    humidity,
    light_level,
    location,
    resolved,
    timestamp
) VALUES (
    'esp32_fire_alarm_01',
    'fire',
    'warning',
    950,
    1600,
    28.5,
    65.2,
    22.8,
    '宿舍A栋101',
    TRUE,
    datetime('now', '-1 hours', '+8 hours')
);

-- 显示创建结果
SELECT '数据库重置完成！' AS message;
SELECT COUNT(*) AS device_count FROM device_info;
SELECT COUNT(*) AS sensor_data_count FROM sensor_data;
SELECT COUNT(*) AS alert_history_count FROM alert_history;

-- 显示设备信息
SELECT '设备信息：' AS info;
SELECT device_id, name, location, device_type, status FROM device_info;

-- =====================================================================
-- 脚本执行完成
-- =====================================================================