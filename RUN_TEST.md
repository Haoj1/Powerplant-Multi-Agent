# 测试运行指南

环境已激活并安装完成后，按下面步骤测试运行。

---

## 1. 启动 MQTT Broker（可选但推荐）

不启动 MQTT 也可以跑 Simulator，但不会发布遥测到 MQTT。

```bash
docker-compose up -d mosquitto
```

检查是否在跑：

```bash
docker ps | grep mosquitto
```

---

## 2. 启动 Simulator 服务

**在项目根目录**（`Multi-Agent Project`）下执行：

```bash
# 确保已激活 venv（命令行前有 (venv)）
source venv/bin/activate   # Linux/macOS
# 或 Windows: venv\Scripts\activate

# 从项目根目录运行 Simulator
cd simulator-service
python3 main.py
```

或一条命令（在项目根目录）：

```bash
python3 simulator-service/main.py
```

看到类似输出说明启动成功：

```
INFO:     Uvicorn running on http://0.0.0.0:8001
INFO:     Application startup complete.
```

如未启动 MQTT，可能有一条 “Could not connect to MQTT broker” 的警告，可忽略，服务仍会运行。

---

## 3. 测试 API（另开一个终端）

保持 Simulator 在跑，新开一个终端，激活同一 venv 后执行。

### 3.1 健康检查

```bash
curl http://localhost:8001/health
```

期望：`{"status":"healthy","service":"simulator-service",...}`

### 3.2 加载场景

```bash
curl -X POST http://localhost:8001/scenario/load \
  -H "Content-Type: application/json" \
  -d '{
    "scenario": {
      "name": "healthy_baseline",
      "duration_sec": 60,
      "initial_conditions": {"rpm": 2950, "valve_open_pct": 60},
      "faults": [],
      "setpoints": []
    }
  }'
```

期望：`{"status":"loaded","scenario_name":"healthy_baseline","duration_sec":60}`

### 3.3 启动仿真

```bash
curl -X POST http://localhost:8001/scenario/start
```

期望：`{"status":"started"}`

### 3.4 查看状态

```bash
curl http://localhost:8001/status
```

期望：包含 `"running": true`、`current_time_sec` 递增。

### 3.5 停止仿真

```bash
curl -X POST http://localhost:8001/scenario/stop
```

---

## 4. 用本地 JSON 文件加载场景

项目里已有示例场景，可从文件加载：

```bash
# 在项目根目录
cd "/Users/bianhaoji/Documents/MERN Project/Multi-Agent Project"

# 构造请求体并加载 healthy_baseline
curl -X POST http://localhost:8001/scenario/load \
  -H "Content-Type: application/json" \
  -d "{\"scenario\": $(cat simulator-service/scenarios/healthy_baseline.json)}"
```

然后同样执行 start / status / stop。

---

## 5. 查看 MQTT 遥测（可选）

若已启动 Mosquitto，可订阅遥测：

```bash
mosquitto_sub -h localhost -p 1883 -t "telemetry/#" -v
```

启动仿真后，应能看到 `telemetry/pump01` 上的 JSON 消息。

---

## 6. 查看本地日志

遥测会写入项目下的 `logs/telemetry.jsonl`：

```bash
tail -f logs/telemetry.jsonl
```

（需先创建 `logs` 目录或由程序自动创建）

---

## 常见问题

| 现象 | 处理 |
|------|------|
| `ModuleNotFoundError: No module named 'shared_lib'` | 必须在**项目根目录**执行 `python3 simulator-service/main.py`，或先 `cd simulator-service` 再从项目根运行。 |
| `Address already in use` | 8001 被占用，可改端口：`uvicorn simulator_service.main:app --port 8002` 或修改 `main.py` 末尾端口。 |
| MQTT 连接失败 | 先执行 `docker-compose up -d mosquitto`；未装 Docker 时可忽略，Simulator 仍会跑并写 logs。 |
| `No module named 'numpy'` 等 | 确认已激活 venv 并安装依赖：`pip install -r requirements.txt`。 |

---

## 一键测试脚本（可选）

在项目根目录创建 `test_run.sh`：

```bash
#!/bin/bash
set -e
echo "1. Health check..."
curl -s http://localhost:8001/health | head -1
echo ""
echo "2. Load scenario..."
curl -s -X POST http://localhost:8001/scenario/load \
  -H "Content-Type: application/json" \
  -d '{"scenario":{"name":"test","duration_sec":10,"initial_conditions":{},"faults":[],"setpoints":[]}}'
echo ""
echo "3. Start simulation..."
curl -s -X POST http://localhost:8001/scenario/start
echo ""
sleep 3
echo "4. Status..."
curl -s http://localhost:8001/status
echo ""
echo "5. Stop..."
curl -s -X POST http://localhost:8001/scenario/stop
echo ""
echo "Done."
```

使用前先启动 Simulator，再在另一终端执行：`chmod +x test_run.sh && ./test_run.sh`。
