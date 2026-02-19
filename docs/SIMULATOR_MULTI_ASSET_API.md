# Simulator 多资产 API 文档

## 概述

Simulator 现在支持**同时运行多个资产（机器）**的 scenario，每个资产独立运行。还支持**手动触发告警**用于测试。

---

## 多资产支持

### 架构变更

- **之前**：单个 `executor`，只能运行一个 scenario
- **现在**：`executors` 字典（`asset_id -> executor`），可同时运行多个 scenario

### Scenario JSON 格式

所有 scenario JSON 文件现在需要包含 `plant_id` 和 `asset_id`：

```json
{
  "version": "1.0",
  "name": "healthy_baseline",
  "plant_id": "plant01",
  "asset_id": "pump01",  // 必需：资产 ID
  "description": "...",
  "seed": 12345,
  "duration_sec": 600,
  ...
}
```

如果未指定，默认使用 `plant01` 和 `pump01`。

---

## API 端点

### 1. 加载 Scenario

**`POST /scenario/load`**

加载 scenario 到指定资产（asset_id 从 scenario JSON 中读取）。

**Request Body:**
```json
{
  "scenario": {
    "version": "1.0",
    "name": "healthy_baseline",
    "plant_id": "plant01",
    "asset_id": "pump01",
    "description": "...",
    "seed": 12345,
    "duration_sec": 600,
    "initial_conditions": {...},
    "faults": [...],
    "setpoints": [...]
  }
}
```

**Response:**
```json
{
  "status": "loaded",
  "asset_id": "pump01",
  "plant_id": "plant01",
  "scenario_name": "healthy_baseline",
  "duration_sec": 600
}
```

**注意**：如果该 asset_id 已有运行的 scenario，会自动停止。

---

### 2. 启动 Scenario（特定资产）

**`POST /scenario/start/{asset_id}`**

启动指定资产的 scenario。

**Example:**
```bash
POST /scenario/start/pump01
POST /scenario/start/pump02
```

**Response:**
```json
{
  "status": "started",
  "asset_id": "pump01"
}
```

---

### 3. 停止 Scenario（特定资产）

**`POST /scenario/stop/{asset_id}`**

停止指定资产的 scenario。

**Example:**
```bash
POST /scenario/stop/pump01
```

**Response:**
```json
{
  "status": "stopped",
  "asset_id": "pump01"
}
```

---

### 4. 停止所有 Scenario

**`POST /scenario/stop`**

停止所有正在运行的 scenario。

**Response:**
```json
{
  "status": "stopped",
  "stopped_assets": ["pump01", "pump02"]
}
```

---

### 5. 重置 Scenario（特定资产）

**`POST /scenario/reset/{asset_id}`**

重置指定资产的 scenario 到开始状态。

**Response:**
```json
{
  "status": "reset",
  "asset_id": "pump01"
}
```

---

### 6. 查询状态

**`GET /status`** - 查询所有资产状态

**`GET /status?asset_id=pump01`** - 查询特定资产状态

**Response (所有资产):**
```json
{
  "assets": [
    {
      "asset_id": "pump01",
      "scenario_name": "healthy_baseline",
      "running": true,
      "current_time": 123.45,
      "duration_sec": 600,
      ...
    },
    {
      "asset_id": "pump02",
      "scenario_name": "bearing_wear_chronic",
      "running": true,
      "current_time": 456.78,
      "duration_sec": 3600,
      ...
    }
  ],
  "total_assets": 2
}
```

**Response (单个资产):**
```json
{
  "asset_id": "pump01",
  "scenario_name": "healthy_baseline",
  "running": true,
  "current_time": 123.45,
  "duration_sec": 600,
  ...
}
```

---

### 7. 列出所有 Scenario

**`GET /scenarios`**

列出所有已加载的 scenario。

**Response:**
```json
{
  "scenarios": [
    {
      "asset_id": "pump01",
      "scenario_name": "healthy_baseline",
      "running": true,
      "current_time": 123.45,
      "duration_sec": 600
    },
    {
      "asset_id": "pump02",
      "scenario_name": "bearing_wear_chronic",
      "running": false,
      "current_time": 0.0,
      "duration_sec": 3600
    }
  ],
  "total": 2
}
```

---

### 8. 手动触发告警（测试用）

**`POST /alert/trigger`**

手动触发一个告警，发布到 MQTT 供 Agent A 处理。

**Request Body:**
```json
{
  "asset_id": "pump01",
  "plant_id": "plant01",
  "signal": "vibration_rms",
  "severity": "warning",  // 或 "critical"
  "score": 3.5,
  "method": "manual",
  "evidence": {
    "manual_trigger": true,
    "test_purpose": "testing alert flow"
  }
}
```

**Response:**
```json
{
  "status": "triggered",
  "asset_id": "pump01",
  "signal": "vibration_rms",
  "severity": "warning",
  "mqtt_topic": "alerts/pump01"
}
```

**用途**：
- 测试告警流程（Agent A → Agent B → Agent C → Agent D）
- 验证前端告警展示
- 测试 RAG 查询相似告警

---

## 使用示例

### 示例 1：同时运行两个资产

```python
import requests

BASE_URL = "http://localhost:8001"

# 加载 pump01 的 scenario
with open("scenarios/healthy_baseline.json") as f:
    scenario1 = json.load(f)
    scenario1["asset_id"] = "pump01"

requests.post(f"{BASE_URL}/scenario/load", json={"scenario": scenario1})

# 加载 pump02 的 scenario
with open("scenarios/bearing_wear_chronic.json") as f:
    scenario2 = json.load(f)
    scenario2["asset_id"] = "pump02"

requests.post(f"{BASE_URL}/scenario/load", json={"scenario": scenario2})

# 同时启动两个
requests.post(f"{BASE_URL}/scenario/start/pump01")
requests.post(f"{BASE_URL}/scenario/start/pump02")

# 查看状态
status = requests.get(f"{BASE_URL}/status").json()
print(f"Running assets: {[a['asset_id'] for a in status['assets'] if a['running']]}")
```

### 示例 2：手动触发告警测试

```python
# 触发一个告警
alert = {
    "asset_id": "pump01",
    "signal": "vibration_rms",
    "severity": "critical",
    "score": 5.0,
    "method": "manual",
    "evidence": {"test": True}
}

response = requests.post(f"{BASE_URL}/alert/trigger", json=alert)
print(response.json())
# 告警会发布到 MQTT topic: alerts/pump01
# Agent A 会处理并转发给 Agent B
```

---

## Agent D 前端集成建议

### Scenario 管理页面

1. **Scenario 列表**
   - 显示所有已加载的 scenario（`GET /scenarios`）
   - 每个 scenario 显示：asset_id、名称、运行状态、当前时间

2. **加载 Scenario**
   - 表单：选择 scenario JSON 文件或手动输入
   - 可编辑 `asset_id`（默认从 JSON 读取）
   - 调用 `POST /scenario/load`

3. **控制按钮**
   - Start / Stop / Reset 按钮（每个 asset 独立）
   - 调用 `POST /scenario/start/{asset_id}` 等

4. **手动触发告警**
   - 表单：asset_id、signal、severity、score
   - 调用 `POST /alert/trigger`
   - 用于快速测试告警流程

---

## 注意事项

1. **线程安全**：使用 `_executors_lock` 保护 `executors` 字典
2. **资源清理**：停止 scenario 时会清理线程
3. **MQTT Topic**：每个资产发布到 `telemetry/{asset_id}` 和 `alerts/{asset_id}`
4. **数据库**：所有资产的 telemetry 都写入同一个数据库（按 `asset_id` 区分）

---

## 迁移指南

### 旧代码（单资产）

```python
# 旧代码
requests.post("/scenario/load", json={"scenario": scenario})
requests.post("/scenario/start")
```

### 新代码（多资产）

```python
# 新代码
scenario["asset_id"] = "pump01"  # 添加 asset_id
requests.post("/scenario/load", json={"scenario": scenario})
requests.post("/scenario/start/pump01")  # 指定 asset_id
```

---

## 总结

✅ **多资产支持** - 可同时运行多个 scenario  
✅ **手动触发告警** - 方便测试  
✅ **向后兼容** - 默认 asset_id="pump01"  
✅ **线程安全** - 使用锁保护共享状态
