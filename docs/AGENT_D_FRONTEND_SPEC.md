# Agent D 前端功能规格说明

## 概述

Agent D 前端是一个 React Web 应用，提供审核队列管理、实时传感器监控、智能聊天助手和 Scenario 管理功能。

**技术栈建议：**
- React + React Router
- Axios（API 调用）
- ReactMarkdown（消息渲染）
- EventSource（SSE 流式）
- 可选：Material-UI / Ant Design / Tailwind CSS

---

## 1. 页面结构

### 1.1 主布局（Dashboard Layout）

```
┌─────────────────────────────────────────────────────────┐
│  Header: Agent D Review Dashboard                       │
├──────────┬──────────────────────────────────────────────┤
│          │                                              │
│ Sidebar  │  Main Content Area                          │
│          │  (根据路由切换不同页面)                      │
│ - Review │                                              │
│ - Alerts │                                              │
│ - Sensors│                                              │
│ - Chat   │                                              │
│ - Scenarios│                                            │
│          │                                              │
└──────────┴──────────────────────────────────────────────┘
```

**导航菜单：**
- Review Queue（审核队列）
- Alerts（告警列表）
- Sensors（实时传感器）
- Chat（智能助手）
- Scenarios（Scenario 管理）

---

## 2. Review Queue（审核队列）页面

### 2.1 功能列表

**主要功能：**
- 显示待审核的诊断列表（`status=pending`）
- 筛选：按 asset_id、plant_id、时间范围
- 排序：按创建时间、优先级
- 查看诊断详情
- 审核操作：Approve / Reject / Edit

### 2.2 UI 组件

#### 2.2.1 Review List Table

| 列 | 内容 |
|----|------|
| ID | review_request.id |
| Asset | asset_id（可点击跳转到 Sensors） |
| Diagnosis ID | diagnosis_id（可点击查看详情） |
| Root Cause | diagnosis.root_cause |
| Confidence | diagnosis.confidence（进度条 + 百分比） |
| Created At | created_at（相对时间，如 "2分钟前"） |
| Actions | Approve / Reject / View 按钮 |

**筛选器：**
- Status 下拉：pending / approved / rejected / all
- Asset ID 输入框
- Plant ID 输入框（可选）
- 时间范围选择器（可选）

**操作：**
- 点击行 → 打开诊断详情 Modal
- Approve 按钮 → 打开 Approve Modal（可输入 notes）
- Reject 按钮 → 打开 Reject Modal（可输入 notes）

#### 2.2.2 Diagnosis Detail Modal

显示完整诊断信息：

```
┌─────────────────────────────────────┐
│ Diagnosis #123                      │
├─────────────────────────────────────┤
│ Asset: pump01                       │
│ Plant: plant01                      │
│ Timestamp: 2026-02-11 18:00:00     │
│                                     │
│ Root Cause: bearing_wear            │
│ Confidence: 85%                     │
│ Impact: high                        │
│                                     │
│ Recommended Actions:                │
│ - Inspect bearing lubrication      │
│ - Schedule vibration analysis       │
│                                     │
│ Evidence:                           │
│ - Rule: VIB+BEARING_TEMP_UP        │
│   Details: {...}                    │
│                                     │
│ [Approve] [Reject] [Close]         │
└─────────────────────────────────────┘
```

### 2.3 API 调用

```javascript
// 获取待审核列表
GET /api/review-requests?status=pending&asset_id=&limit=50

// 获取诊断详情
GET /api/diagnosis/{diagnosis_id}

// 批准审核
POST /api/review/{review_id}/approve
Body: { notes: "...", create_salesforce_case: false }

// 拒绝审核
POST /api/review/{review_id}/reject
Body: { notes: "..." }
```

---

## 3. Alerts（告警列表）页面

### 3.1 功能列表

**主要功能：**
- 显示所有告警（带关联的诊断和工单）
- 链接：Alert → Diagnosis → Ticket
- 筛选：按 asset_id、severity、时间范围
- 查看告警详情

### 3.2 UI 组件

#### 3.2.1 Alerts Table

| 列 | 内容 |
|----|------|
| ID | alert.id |
| Asset | asset_id |
| Signal | signal（如 vibration_rms） |
| Severity | severity（badge：warning/critical） |
| Score | score（数值） |
| Method | method（如 zscore） |
| Diagnosis | 链接到 diagnosis_id（如果有） |
| Ticket | 链接到 ticket（如果有） |
| Time | ts（相对时间） |

**筛选器：**
- Asset ID
- Severity（warning / critical / all）
- 时间范围

**操作：**
- 点击 Diagnosis 链接 → 跳转到 Review Queue 并高亮该诊断
- 点击 Ticket 链接 → 打开 Ticket 详情（或跳转到 Salesforce）

### 3.3 API 调用

```javascript
// 获取告警列表（带诊断和工单链接）
GET /api/alerts?asset_id=&limit=50
```

---

## 4. Sensors（实时传感器）页面

### 4.1 功能列表

**主要功能：**
- 选择资产（asset_id 下拉）
- 实时显示传感器数据（定时刷新）
- 传感器仪表盘（可视化）
- 历史数据图表（可选）

### 4.2 UI 组件

#### 4.2.1 Asset Selector

```
┌─────────────────────────────────────┐
│ Select Asset: [pump01 ▼]            │
│ Auto-refresh: [5秒 ▼] [✓] Enable   │
└─────────────────────────────────────┘
```

#### 4.2.2 Sensor Dashboard

**仪表盘布局（Grid）：**

```
┌─────────────┬─────────────┬─────────────┐
│ Pressure    │ Flow        │ Temperature │
│ 12.5 bar    │ 85.3 m³/h   │ 62.2 °C     │
│ [Gauge]     │ [Gauge]     │ [Gauge]     │
├─────────────┼─────────────┼─────────────┤
│ Bearing Temp│ Vibration   │ RPM         │
│ 71.0 °C     │ 0.42 mm/s   │ 2950 rpm    │
│ [Gauge]     │ [Gauge]     │ [Gauge]     │
├─────────────┼─────────────┼─────────────┤
│ Motor Current│ Valve Open │ Fault       │
│ 18.6 A      │ 62.0 %      │ none        │
│ [Gauge]     │ [Gauge]     │ [Badge]     │
└─────────────┴─────────────┴─────────────┘
```

**每个传感器显示：**
- 当前值（大号数字）
- 单位
- 仪表盘/进度条（可选）
- 状态颜色（正常/警告/危险）

**可选功能：**
- 历史趋势图（最近 1 小时）
- 阈值线标记

### 4.3 API 调用

```javascript
// 获取最新遥测数据
GET /api/telemetry?asset_id=pump01&since_ts=&limit=100

// 定时刷新（每 5 秒）
setInterval(() => {
  fetchTelemetry(assetId);
}, 5000);
```

---

## 5. Chat（智能助手）页面

### 5.1 功能列表

**主要功能：**
- 聊天会话管理（新建/加载历史会话）
- ReAct 流式对话（SSE）
- **完整显示所有 ReAct 步骤**（不隐藏）
- Markdown 渲染
- 会话持久化

### 5.2 UI 组件

#### 5.2.1 Chat Layout

```
┌─────────────────────────────────────────────┐
│ Chat Sessions                    [+ New]     │
├─────────────────────────────────────────────┤
│ Session List (左侧)                         │
│ - Session 1: "How to diagnose..."          │
│ - Session 2: "What is bearing wear?"      │
│                                             │
│ Chat Panel (右侧)                           │
│ ┌─────────────────────────────────────────┐ │
│ │ User: How to diagnose bearing wear?    │ │
│ │                                         │ │
│ │ Assistant: [Thinking...]                │ │
│ │ ┌─────────────────────────────────────┐ │ │
│ │ │ Step 1: Thought                    │ │ │
│ │ │ "I need to search for similar..."   │ │ │
│ │ └─────────────────────────────────────┘ │ │
│ │ ┌─────────────────────────────────────┐ │ │
│ │ │ Step 2: Tool Call                   │ │ │
│ │ │ query_similar_diagnoses("bearing")  │ │ │
│ │ └─────────────────────────────────────┘ │ │
│ │ ┌─────────────────────────────────────┐ │ │
│ │ │ Step 3: Tool Result                 │ │ │
│ │ │ Found 5 similar cases...            │ │ │
│ │ └─────────────────────────────────────┘ │ │
│ │                                         │ │
│ │ Final Answer: ...                       │ │
│ └─────────────────────────────────────────┘ │
│                                             │
│ [Input box] [Send]                         │
└─────────────────────────────────────────────┘
```

#### 5.2.2 ReAct Step Display（关键功能）

**每个步骤必须完整显示：**

1. **Thought（思考）**
   ```
   ┌─────────────────────────────────────┐
   │ 💭 Thought                          │
   │ I need to search for similar        │
   │ diagnoses to help the user...       │
   └─────────────────────────────────────┘
   ```

2. **Tool Call（工具调用）**
   ```
   ┌─────────────────────────────────────┐
   │ 🔧 Tool Call: query_similar_diagnoses│
   │ Args: {                             │
   │   "query": "bearing wear",          │
   │   "limit": 5                         │
   │ }                                   │
   └─────────────────────────────────────┘
   ```

3. **Tool Result（工具结果）**
   ```
   ┌─────────────────────────────────────┐
   │ ✅ Tool Result                       │
   │ [                                    │
   │   {                                 │
   │     "diagnosis_id": 123,            │
   │     "similarity": "87.5%",          │
   │     "root_cause": "bearing_wear"    │
   │   },                                │
   │   ...                               │
   │ ]                                   │
   │ [Expand] [Collapse]                 │
   └─────────────────────────────────────┘
   ```

**重要：**
- ✅ 步骤**永久显示**，不自动清除
- ✅ 显示完整 tool_args 和 raw_result
- ✅ 支持展开/折叠长结果
- ✅ 流式更新：步骤实时追加

#### 5.2.3 Session List

- 显示会话预览（preview）
- 最后更新时间
- 点击加载历史会话
- 新建会话按钮

#### 5.2.4 Input Area

- 文本输入框（支持多行）
- Send 按钮
- 快捷操作按钮（可选）：
  - "查询待审核的诊断"
  - "查看 pump01 的传感器数据"
  - "搜索相似案例"

### 5.3 SSE 流式处理

```javascript
// 连接 SSE
const eventSource = new EventSource(
  `/api/chat/ask?question=${encodeURIComponent(question)}&session_id=${sessionId}`
);

eventSource.onmessage = (event) => {
  const data = JSON.parse(event.data);
  
  if (data.type === 'step') {
    // 追加步骤到当前消息
    appendStep(data.step);
  } else if (data.type === 'result') {
    // 显示最终答案
    showAnswer(data.answer);
    eventSource.close();
  } else if (data.type === 'error') {
    // 显示错误
    showError(data.error);
    eventSource.close();
  }
};
```

### 5.4 API 调用

```javascript
// 获取会话列表
GET /api/chat/sessions?limit=20

// 获取会话详情（含消息和步骤）
GET /api/chat/sessions/{session_id}

// 发送消息（SSE）
POST /api/chat/ask
Body: {
  question: "...",
  session_id: 123,  // 可选
  conversation_history: [...]  // 可选
}
// Response: SSE stream
```

---

## 6. Scenarios（Scenario 管理）页面

### 6.1 功能列表

**主要功能：**
- 显示所有已加载的 scenario
- 加载新 scenario（上传 JSON 或手动输入）
- 控制 scenario：Start / Stop / Reset
- 手动触发告警（测试用）

### 6.2 UI 组件

#### 6.2.1 Scenario List Table

| 列 | 内容 |
|----|------|
| Asset ID | asset_id |
| Scenario Name | scenario_name |
| Status | running（badge：运行中/已停止） |
| Current Time | current_time / duration_sec |
| Progress | 进度条 |
| Actions | Start / Stop / Reset / Delete |

#### 6.2.2 Load Scenario Form

```
┌─────────────────────────────────────┐
│ Load Scenario                       │
├─────────────────────────────────────┤
│ Method:                             │
│ ○ Upload JSON File                  │
│ ○ Manual Input                      │
│                                     │
│ [Choose File] healthy_baseline.json │
│                                     │
│ Asset ID: [pump01] (可编辑)         │
│ Plant ID: [plant01] (可编辑)        │
│                                     │
│ [Load] [Cancel]                    │
└─────────────────────────────────────┘
```

**功能：**
- 上传 JSON 文件 → 自动解析
- 手动输入 JSON → 编辑器（Monaco Editor 或 CodeMirror）
- 可编辑 asset_id 和 plant_id
- 验证 JSON 格式

#### 6.2.3 Manual Alert Trigger（测试功能）

```
┌─────────────────────────────────────┐
│ Trigger Alert (Test)                │
├─────────────────────────────────────┤
│ Asset ID: [pump01 ▼]                │
│ Signal: [vibration_rms ▼]          │
│ Severity: ○ Warning ○ Critical      │
│ Score: [3.5]                        │
│ Evidence: {                         │
│   "manual_trigger": true            │
│ }                                   │
│                                     │
│ [Trigger] [Cancel]                  │
└─────────────────────────────────────┘
```

**用途：**
- 快速测试告警流程
- 验证前端告警展示
- 测试 RAG 查询

### 6.3 API 调用

```javascript
// Simulator API (端口 8001)
const SIMULATOR_URL = "http://localhost:8001";

// 获取所有 scenario
GET ${SIMULATOR_URL}/scenarios

// 加载 scenario
POST ${SIMULATOR_URL}/scenario/load
Body: { scenario: {...} }

// 启动 scenario
POST ${SIMULATOR_URL}/scenario/start/{asset_id}

// 停止 scenario
POST ${SIMULATOR_URL}/scenario/stop/{asset_id}

// 重置 scenario
POST ${SIMULATOR_URL}/scenario/reset/{asset_id}

// 查询状态
GET ${SIMULATOR_URL}/status?asset_id={asset_id}

// 手动触发告警
POST ${SIMULATOR_URL}/alert/trigger
Body: {
  asset_id: "pump01",
  signal: "vibration_rms",
  severity: "critical",
  score: 5.0,
  method: "manual",
  evidence: {}
}
```

---

## 7. 通用功能

### 7.1 导航和路由

**路由结构：**
```
/                    → Review Queue（默认）
/review              → Review Queue
/alerts              → Alerts List
/sensors             → Sensors Dashboard
/chat                → Chat Panel
/scenarios           → Scenario Management
```

### 7.2 数据刷新策略

| 页面 | 刷新方式 | 频率 |
|------|---------|------|
| Review Queue | 手动刷新 + 轮询 | 30秒 |
| Alerts | 手动刷新 + 轮询 | 30秒 |
| Sensors | 自动刷新 | 5秒（可配置） |
| Chat | 实时 SSE | 事件驱动 |
| Scenarios | 手动刷新 | 按需 |

### 7.3 错误处理

- API 错误提示（Toast / Snackbar）
- 网络错误重试
- 加载状态（Loading spinner）
- 空状态提示（Empty state）

### 7.4 响应式设计

- 桌面端：完整布局
- 移动端：侧边栏折叠，主要功能可用

---

## 8. 组件清单

### 8.1 页面组件

- [ ] `DashboardLayout.js` - 主布局（Header + Sidebar + Content）
- [ ] `ReviewQueuePage.js` - 审核队列页面
- [ ] `AlertsPage.js` - 告警列表页面
- [ ] `SensorsPage.js` - 传感器页面
- [ ] `ChatPage.js` - 聊天页面
- [ ] `ScenariosPage.js` - Scenario 管理页面

### 8.2 Review Queue 组件

- [ ] `ReviewListTable.js` - 审核列表表格
- [ ] `ReviewFilters.js` - 筛选器
- [ ] `DiagnosisDetailModal.js` - 诊断详情弹窗
- [ ] `ApproveModal.js` - 批准弹窗
- [ ] `RejectModal.js` - 拒绝弹窗

### 8.3 Alerts 组件

- [ ] `AlertsTable.js` - 告警表格
- [ ] `AlertFilters.js` - 筛选器
- [ ] `AlertDetailModal.js` - 告警详情（可选）

### 8.4 Sensors 组件

- [ ] `AssetSelector.js` - 资产选择器
- [ ] `SensorDashboard.js` - 传感器仪表盘
- [ ] `SensorGauge.js` - 单个传感器仪表（可复用）
- [ ] `TelemetryChart.js` - 历史趋势图（可选）

### 8.5 Chat 组件

- [ ] `ChatLayout.js` - 聊天布局（会话列表 + 消息区）
- [ ] `SessionList.js` - 会话列表
- [ ] `ChatPanel.js` - 聊天面板
- [ ] `MessageList.js` - 消息列表
- [ ] `MessageItem.js` - 单条消息
- [ ] `ReactStep.js` - ReAct 步骤组件
  - [ ] `ThoughtStep.js` - 思考步骤
  - [ ] `ToolCallStep.js` - 工具调用步骤
  - [ ] `ToolResultStep.js` - 工具结果步骤
- [ ] `ChatInput.js` - 输入框
- [ ] `SSEHandler.js` - SSE 流式处理工具

### 8.6 Scenarios 组件

- [ ] `ScenarioListTable.js` - Scenario 列表
- [ ] `LoadScenarioModal.js` - 加载 Scenario 弹窗
- [ ] `ScenarioControls.js` - 控制按钮组
- [ ] `TriggerAlertModal.js` - 触发告警弹窗
- [ ] `ScenarioStatus.js` - Scenario 状态显示

### 8.7 通用组件

- [ ] `LoadingSpinner.js` - 加载动画
- [ ] `ErrorToast.js` - 错误提示
- [ ] `EmptyState.js` - 空状态
- [ ] `TimeAgo.js` - 相对时间显示
- [ ] `Badge.js` - 状态徽章（severity、status）
- [ ] `ConfidenceBar.js` - 置信度进度条

---

## 9. 状态管理

### 9.1 建议方案

**选项 1：React Context + useState（简单项目）**
- `ReviewContext` - 审核队列状态
- `ChatContext` - 聊天状态
- `SensorsContext` - 传感器状态

**选项 2：Redux / Zustand（复杂项目）**
- 统一状态管理
- 更好的性能优化

### 9.2 关键状态

```javascript
// Review Queue
{
  reviewRequests: [],
  selectedDiagnosis: null,
  filters: { status: 'pending', asset_id: '' },
  loading: false
}

// Chat
{
  sessions: [],
  currentSession: null,
  messages: [],
  currentSteps: [],  // 当前消息的 ReAct 步骤
  streaming: false
}

// Sensors
{
  selectedAsset: 'pump01',
  telemetry: [],
  autoRefresh: true,
  refreshInterval: 5000
}

// Scenarios
{
  scenarios: [],
  loading: false
}
```

---

## 10. 实现优先级

### Phase 1：核心功能（必须）

1. ✅ **Review Queue 页面**
   - 列表展示
   - 诊断详情
   - Approve/Reject

2. ✅ **Chat 页面**
   - 基础聊天
   - SSE 流式
   - ReAct 步骤显示（简化版）

### Phase 2：重要功能

3. ✅ **Alerts 页面**
   - 告警列表
   - 链接到诊断和工单

4. ✅ **Sensors 页面**
   - 实时传感器展示
   - 自动刷新

### Phase 3：增强功能

5. ✅ **Scenarios 页面**
   - Scenario 管理
   - 手动触发告警

6. ✅ **Chat 增强**
   - 完整 ReAct 步骤展示
   - 会话历史加载
   - 快捷操作

---

## 11. API 端点汇总

### Agent D Backend (端口 8005)

```
GET  /api/review-requests?status=&asset_id=&limit=
GET  /api/diagnosis/{id}
GET  /api/alerts?asset_id=&limit=
GET  /api/telemetry?asset_id=&since_ts=&limit=
GET  /api/chat/sessions?limit=
GET  /api/chat/sessions/{id}
POST /api/chat/ask (SSE)
POST /api/review/{id}/approve
POST /api/review/{id}/reject
```

### Simulator (端口 8001)

```
GET  /scenarios
GET  /status?asset_id=
POST /scenario/load
POST /scenario/start/{asset_id}
POST /scenario/stop/{asset_id}
POST /scenario/reset/{asset_id}
POST /alert/trigger
```

---

## 12. 参考项目

**Email-Agent Frontend：**
- 路径：`/Users/bianhaoji/Documents/MERN Project/Mail Agent/Email-Agent/frontend`
- 参考组件：`AssistChatPanel.js`、`ThreadChatPanel.js`
- 参考模式：SSE 流式、会话管理、Markdown 渲染

**关键差异：**
- Email-Agent：思考步骤 2 秒后清除
- Agent D：**思考步骤永久显示，不隐藏**

---

## 13. 技术细节

### 13.1 SSE 流式处理

```javascript
function useChatSSE(question, sessionId, onStep, onResult, onError) {
  useEffect(() => {
    const eventSource = new EventSource(
      `/api/chat/ask?question=${encodeURIComponent(question)}&session_id=${sessionId || ''}`
    );
    
    eventSource.onmessage = (e) => {
      const data = JSON.parse(e.data);
      if (data.type === 'step') onStep(data.step);
      else if (data.type === 'result') {
        onResult(data.answer, data.session_id);
        eventSource.close();
      } else if (data.type === 'error') {
        onError(data.error);
        eventSource.close();
      }
    };
    
    return () => eventSource.close();
  }, [question, sessionId]);
}
```

### 13.2 ReAct 步骤渲染

```javascript
function ReactStep({ step }) {
  const { step_type, tool_name, tool_args, content, raw_result } = step;
  
  if (step_type === 'thought') {
    return <ThoughtStep content={content} />;
  } else if (step_type === 'tool_call') {
    return <ToolCallStep tool={tool_name} args={tool_args} />;
  } else if (step_type === 'tool_result') {
    return <ToolResultStep content={content} raw={raw_result} />;
  }
}
```

### 13.3 实时传感器刷新

```javascript
function useTelemetry(assetId, interval = 5000) {
  const [data, setData] = useState(null);
  
  useEffect(() => {
    const fetchData = async () => {
      const res = await fetch(`/api/telemetry?asset_id=${assetId}&limit=1`);
      const json = await res.json();
      setData(json.data[0]);  // 最新一条
    };
    
    fetchData();
    const timer = setInterval(fetchData, interval);
    return () => clearInterval(timer);
  }, [assetId, interval]);
  
  return data;
}
```

---

## 14. 总结

### 必须实现的功能

1. ✅ **Review Queue** - 审核队列和操作
2. ✅ **Chat** - 智能助手（含 ReAct 步骤）
3. ✅ **Alerts** - 告警列表和链接
4. ✅ **Sensors** - 实时传感器监控
5. ✅ **Scenarios** - Scenario 管理和测试

### 关键特性

- ✅ **ReAct 步骤完整显示**（不隐藏）
- ✅ **SSE 流式**（实时更新）
- ✅ **多资产支持**（Scenario 管理）
- ✅ **手动触发告警**（测试功能）

### 预计工作量

- **Phase 1**（核心）：3-4 天
- **Phase 2**（重要）：2-3 天
- **Phase 3**（增强）：2-3 天
- **总计**：7-10 天
