下面是一份**可直接发给 code agent 的两周项目计划 + 规格书**（按我推荐的：**轻量 Simulator + 故障注入 + MQTT 事件总线 + 4-agent 闭环 + 工单用 GitHub Issues/自建 Ticket**）。你复制整段给 agent 就能开干。

---

## 项目目标

在 14 天内实现一个可演示的多智能体系统：

1. **Simulator** 模拟 powerplant 子系统（推荐：泵/管路/轴承），实时输出传感器流数据
2. **Multi-agent** 实时监控并检测异常、诊断根因
3. 自动创建 **Case/WorkOrder（用 Ticket 替代）**，并支持 human-in-the-loop 审核与反馈
4. 可视化与指标：误报/漏报/检测延迟/工单生成延迟

---

## 总体架构

### 服务/模块

* `simulator-service`：生成传感器数据，发布到 MQTT `telemetry/*`
* `agent-monitor`（Agent A）：订阅 telemetry，滑窗检测异常，发布 `alerts/*`
* `agent-diagnosis`（Agent B）：订阅 alerts + 拉取历史窗口，输出 RCA 诊断，发布 `diagnosis/*`
* `agent-ticket`（Agent C）：订阅 diagnosis，创建工单（GitHub Issues 或自建 Ticket API），发布 `tickets/*`
* `agent-review`（Agent D）：订阅 tickets，提供审批/修改/关闭接口，并发布 `feedback/*`
* `shared_lib`：统一 schema、序列化、特征提取、工具函数
* 可选：`dashboard`（简单前端/CLI）+ Grafana（如果有时间）

### 消息总线（推荐）

* MQTT（Mosquitto Docker）
* Topic 约定：

  * `telemetry/pump01`
  * `alerts/pump01`
  * `diagnosis/pump01`
  * `tickets/pump01`
  * `feedback/pump01`

---

## 数据 Schema（统一 JSON）

### Telemetry（simulator → MQTT）

```json
{
  "ts": "2026-02-11T18:00:00Z",
  "plant_id": "plant01",
  "asset_id": "pump01",
  "signals": {
    "pressure_bar": 12.3,
    "flow_m3h": 85.1,
    "temp_c": 62.2,
    "bearing_temp_c": 71.0,
    "vibration_rms": 0.42,
    "rpm": 2950,
    "motor_current_a": 18.6,
    "valve_open_pct": 62.0
  },
  "truth": {
    "fault": "none",
    "severity": 0.0
  }
}
```

### AlertEvent（Agent A → MQTT）

```json
{
  "ts": "...",
  "plant_id": "plant01",
  "asset_id": "pump01",
  "severity": "warning|critical",
  "alerts": [
    {
      "signal": "vibration_rms",
      "score": 3.2,
      "method": "zscore",
      "window_sec": 120,
      "evidence": {"mean": 0.62, "baseline": 0.35, "z": 3.2}
    }
  ]
}
```

### DiagnosisReport（Agent B → MQTT）

```json
{
  "ts": "...",
  "plant_id": "plant01",
  "asset_id": "pump01",
  "root_cause": "bearing_wear|clogging|valve_stuck|sensor_drift|unknown",
  "confidence": 0.78,
  "impact": "low|medium|high",
  "recommended_actions": [
    "Inspect bearing lubrication",
    "Schedule vibration analysis",
    "Check inlet filter differential pressure"
  ],
  "evidence": [
    {"rule": "VIB+BEARING_TEMP_UP", "details": {"vibration_trend": 0.15, "bearing_temp_delta": 8.2}}
  ]
}
```

### Ticket（Agent C → MQTT）

```json
{
  "ts": "...",
  "plant_id": "plant01",
  "asset_id": "pump01",
  "ticket_system": "github|local",
  "ticket_id": "12345",
  "url": "..."
}
```

### Feedback（Agent D → MQTT）

```json
{
  "ts": "...",
  "plant_id": "plant01",
  "asset_id": "pump01",
  "ticket_id": "12345",
  "review_decision": "approved|edited|rejected|closed",
  "final_root_cause": "bearing_wear",
  "notes": "Confirmed by engineer; adjust threshold for vibration_rms"
}
```

---

## Simulator 设计（轻量动态模型 + 故障注入）

### 子系统：泵/管路/轴承（推荐）

内部状态（可简化成几个变量）：

* `R` 阻力（clogging 会升高）
* `d` 轴承磨损（随时间增长）
* `eta` 泵效率（随磨损/堵塞影响）
* 输出信号：

  * flow 与阀门开度 `u`、阻力 `R`、效率 `eta` 相关
  * pressure 与 flow、R 相关
  * bearing_temp 与 d、负载相关
  * vibration 与 d 强相关
  * motor_current 与负载（flow/pressure）相关

### 故障脚本（JSON 驱动，必须可复现）

支持：

* `bearing_wear`：d 以 rate 增长（慢性）
* `clogging`：R 阶跃或缓慢上升（慢性/突发）
* `valve_stuck`：u 固定
* `sensor_drift`：指定 signal 加 bias slope
* `sensor_stuck`：指定 signal 卡死
* `noise_burst`：噪声突然变大
  输出 `truth.fault` 和 `truth.severity` 作为 ground truth

### Simulator API

* `POST /scenario/load`：上传 scenario JSON
* `POST /scenario/start` / `stop`
* `GET /scenario/status`
* MQTT 发布频率：默认 1Hz（可配置）

---

## Multi-agent 逻辑（两周版本务实实现）

### Agent A：监控检测（必须）

* 订阅 telemetry
* 滑窗（60s/120s）特征：均值、标准差、斜率、差分
* 检测方法（任选其一先做通，再迭代）：

  * Z-score（按每个 signal 自适应 baseline）
  * 或 ESD / IsolationForest（可选）
* 输出 AlertEvent（含 evidence）

### Agent B：诊断（规则优先，解释性强）

用 YAML/JSON 规则库（至少 8–12 条规则）：

* VIB 上升 + BEARING_TEMP 上升 → bearing_wear（高置信）
* FLOW 下降 + PRESSURE 上升 + CURRENT 上升 → clogging
* VALVE_OPEN 变化但 FLOW 不动 → valve_stuck
* 单一传感器偏移但其他一致 → sensor_drift
  输出 DiagnosisReport（root cause、confidence、actions、evidence）

### Agent C：工单/Case 创建（先替代）

首选：GitHub Issues（免费稳定）
备用：自建 Ticket service（FastAPI + Postgres）
创建字段：

* title: `[plant01/pump01] suspected bearing_wear (conf 0.78)`
* body: 诊断摘要 + evidence + 最近 5min 关键指标
* labels: severity/asset/root_cause

### Agent D：审核/闭环（最小可用）

提供一个最简单的审核接口（CLI 或 Web）：

* `POST /review/approve`
* `POST /review/edit`
* `POST /review/close`
  记录反馈并发布 Feedback，用于：
* 更新规则阈值（简单实现：把阈值写入 yaml 并 reload）
* 记录“误报案例库”（JSONL）

---

## 可视化与评估（必做但做轻）

### 指标

* detection latency：故障注入到首次告警的时间
* precision/recall：基于 `truth.fault != none` 的事件级评估
* ticket creation latency：诊断到工单创建时间
* false positive rate（每小时误报次数）

### 可视化

最小：

* console log + 保存 CSV/JSONL
  加分：
* Grafana（MQTT→Telegraf→InfluxDB 或直接写入 InfluxDB）

---

## 14 天任务拆分（可照此排期）

### Day 1–2：基础设施 + Simulator

* mosquitto docker + python 项目骨架
* simulator-service：可发布 telemetry、支持 scenario 脚本、可复现 seed
* 生成至少 8 个 signals + truth

### Day 3–4：Agent A

* 订阅 telemetry
* 滑窗检测 + 产出 alerts
* 记录 alerts 日志

### Day 5–6：Agent B

* 规则库（>= 8条）
* 产出 diagnosis（带 evidence）
* 单元测试：对已知 scenario 能输出正确 root cause

### Day 7–8：Agent C

* GitHub Issues connector（token 配置化）
* 创建工单 + 回写 ticket_id 到 MQTT

### Day 9：Agent D（最小审核）

* approve/edit/close API
* feedback 发布 + 写入本地记忆库

### Day 10–11：评估脚本 + 指标输出

* 读取 truth/alerts/diagnosis 计算 precision/recall/latency
* 生成一份 metrics report（markdown）

### Day 12–14：打磨 Demo

* 准备 3 个 demo scenario：正常、慢性磨损、突发堵塞+传感器漂移
* 演示脚本：从数据→告警→诊断→自动工单→人审闭环

---

## 交付物清单（必须产出）

1. 可运行 docker-compose（至少 mosquitto + 各服务）
2. 三个 scenario JSON（可复现）
3. 指标报告（markdown）
4. Demo 脚本（一步启动、一步播放 scenario、一步查看工单）

---

## 工程约束/规范

* Python 3.11
* FastAPI + pydantic schema
* MQTT 客户端：paho-mqtt（或 asyncio-mqtt）
* 配置用 `.env`（包含 MQTT broker、GitHub token、repo）
* 日志：JSONL（便于评估）
* 每个服务都要有 health check：`GET /health`

---

## 可选加分（不影响两周主线）

* 抽象 `TicketConnector` 接口：`create_case()`，将来可替换 Salesforce
* 若要 Salesforce：实现 `SalesforceCaseConnector`（只做 Case，不强依赖 WorkOrder）

---

把这份计划发给 agent 后，你可以要求它：

* 先产出 repo 目录结构 + docker-compose + 最小可跑链路（simulator→monitor→alerts）
* 再逐步补齐 diagnosis/ticket/review

如果你希望我再帮你“更像电厂一点”，我可以把**泵/轴承模型方程、默认参数、三套 scenario JSON**也直接写出来（agent 复制就能跑）。
