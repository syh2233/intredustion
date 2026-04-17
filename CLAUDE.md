# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概览

这是一个基于 ESP32（MicroPython）的宿舍火灾报警系统：多传感器采集（火焰/烟雾/温湿度/光照/声音等）→ 主机可汇总从机 UDP 数据 → 通过 MQTT 上报 → Flask Web 平台实时展示与告警，并新增“智能分析/AI 辅助决策”能力。

## 关键入口（先看这些）

- ESP32 主机主程序：`传感器结合/main.py`（MicroPython，含传感器采集/UDP从机汇聚/MQTT上报）
- ESP32 从机程序：`传感器结合/esp32_slave_simple.py`
- Flask Web 服务器：`web/app.py`
- 智能分析模块：`web/intelligent_analysis.py`（`IntelligentAnalyzer` / `intelligent_analyzer`）
- AI 辅助报警决策：`web/ai_alarm_decision.py`（`AIAlarmDecisionEngine` / `ai_decision_engine`）
- AI 调用封装：`web/ai.py`（OpenAI 兼容 SDK 封装）
- 桌面 GUI（Electron）：`web/electron/main.js`

## 常用命令（Windows/本机开发）

### Web（Flask）

```bash
cd web
pip install -r requirements.txt
python app.py
```

常用页面：
- `http://localhost:5000/`（5层架构主界面）
- `http://localhost:5000/dashboard`（详细仪表板）
- `http://localhost:5000/monitor`（MQTT监控）
- `http://localhost:5000/intelligence`（智能分析中心）

重置数据库（清空并初始化默认设备）：

```bash
cd web
python init_db.py
```

### 桌面 GUI（Electron，嵌入 Web 到本地桌面）

开发运行（不打包）：

```bash
cd web/electron
npm install
npm run start
```

注意：Electron 开发模式默认连接 `http://127.0.0.1:5001`（非 5000），需先启动 Flask 并设置端口，或修改 `FLASK_PORT` 环境变量。

打包为 Windows 安装包（exe）：

```bat
cd web
build_backend.bat        # 用 PyInstaller 打包 Flask 为 fire-alarm-web.exe
cd electron
npm install
npm run dist             # 生成 NSIS 安装包
```

输出目录：`web/electron/dist/`（含 `win-unpacked/` 免安装版和 `.exe` 安装包）。

## 系统架构（大图）

### 数据流

1. 传感器采集：ESP32 主机/从机采集各类传感器数据。
2. 主从机汇聚：主机通过 UDP 接收从机数据并整合（见 `传感器结合/` 目录相关实现）。
3. MQTT 上报：设备按主题发布 JSON 数据/告警（主题约定见下）。
4. Web 端接入：`web/app.py` 使用 `paho-mqtt` 订阅主题，落库（SQLite/SQLAlchemy），并通过 Socket.IO 推送实时更新到前端页面。
5. 智能分析：`web/intelligent_analysis.py` 从 SQLite 读取最近数据做统计/健康度/安全指数，并生成建议。
6. AI 辅助决策：`web/ai_alarm_decision.py` 在硬件阈值结果基础上，对误报进行二次判定（模式/历史/环境/AI 置信度加权）。

### Web 侧并发模型

- `web/app.py` 初始化 `Flask-SocketIO` 时使用 `async_mode='threading'`。

## MQTT 约定与服务器订阅

### 设备发布（ESP32）

（ESP32 侧发布主题的约定可参考 `传感器结合/main.py` 中相关逻辑）

- `esp32/{device_id}/data/json`：传感器数据（JSON）
- `esp32/{device_id}/alert/fire`：火警
- `esp32/{device_id}/alert/warning`：预警

### 服务器订阅（Flask）

`web/app.py` 在 `on_connect` 中订阅：
- `esp32/+/data/json`
- `esp32/+/alert/#`
- `esp32/+/status/#`
- `esp32/+/control`（控制命令主题）

注意：MQTT Broker 地址/端口在 `web/app.py` 的 `app.config[...]` 中配置。

## 数据库（SQLite）

- Web 侧 ORM 模型定义在 `web/app.py`：`SensorData` / `AlertHistory` / `DeviceInfo`
- 数据库文件默认在 `web/instance/fire_alarm.db`。
- 桌面端打包运行时，Electron 会设置 `FIRE_ALARM_DATA_DIR`（写入到用户目录），避免安装目录不可写。

## Web 路由与 API（重点）

### 页面路由（HTML）

- `/`：主界面（5层架构）
- `/dashboard`：仪表板
- `/monitor`：监控
- `/intelligence`：智能分析中心（模板：`web/templates/intelligence.html`）

### 智能分析 API

定义在 `web/app.py`：
- `GET /api/intelligence/analysis`：所有设备汇总（健康分/安全指数概览）
- `GET /api/intelligence/analysis/<device_id>`：单设备智能分析（统计/健康度/AI建议/安全指数）
- `GET /api/intelligence/trends/<device_id>?hours=48`：趋势分析
- `GET /api/intelligence/ai-suggestions/<device_id>`：AI 维护建议
- `GET /api/intelligence/safety-index?device_id=`：环境安全指数
- `GET /api/intelligence/health-score/<device_id>`：设备健康度
- `GET /api/intelligence/statistics`：系统统计
- `GET /api/intelligence/recommendations`：系统级建议（用于汇总视图）

### AI 报警决策 API

定义在 `web/app.py`（用于调试/观测决策效果）：
- `GET /api/ai-decision/statistics`
- `GET|POST /api/ai-decision/config`
- `GET /api/ai-decision/analyze/<device_id>`

## 智能分析/AI 模块说明

### `web/intelligent_analysis.py`

- 统计分析：取每个设备最近 20 条数据做均值/中位数/趋势/异常检测（IQR）
- 健康度：综合数据频率、传感器稳定性、通信可靠性、环境正常性等因子打分

### `web/ai_alarm_decision.py`

- 输入：硬件阈值结果（`normal`/`warning`/`alarm`）+ 当前传感器数据
- 过程：模式检测（趋势/尖峰）、环境上下文（时间/季节/报警频率/健康度）、AI 置信度打分并加权
- 输出：最终等级、置信度、是否干预、详细分析

### `web/ai.py`

- `new(system_prompt, user_prompt)` 通过环境变量读取 Key：`DEEPSEEK_API_KEY`（或 `OPENAI_API_KEY`）。

## 微信小程序（miniprogram-1）

仓库包含一个微信小程序工程（云开发 quickstart 基础结构）位于：
- `miniprogram-1/miniprogram-1/miniprogram-1/`

目前更像是小程序脚手架/示例代码，和 Flask Web 的数据接口是否已对齐，需要以小程序页面调用实现为准。
