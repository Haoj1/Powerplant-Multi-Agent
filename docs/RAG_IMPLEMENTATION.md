# RAG 实现总结

## ✅ 已实现的功能

### 1. 向量索引模块 (`shared-lib/vector_indexing.py`)

提供了 7 种数据类型的索引函数：
- `index_diagnosis()` - 诊断索引
- `index_alert()` - 告警索引
- `index_feedback()` - 反馈索引
- `index_ticket()` - 工单索引
- `index_chat_message()` - 聊天消息索引
- `index_vision_analysis()` - 视觉分析索引
- `index_rules()` - 规则文件索引

所有函数都使用 `@_safe_index` 装饰器，确保索引失败不会影响主流程。

---

### 2. Agent A (Monitor) - 告警索引 ✅

**位置：** `agent-monitor/main.py`

在告警创建后自动索引到向量库：

```python
# 告警写入 DB 后
if primary_alert_id and index_alert:
    alert_data = {
        "asset_id": alert.asset_id,
        "plant_id": alert.plant_id,
        "severity": alert.severity,
        "signal": alert.alerts[0].signal,
        "score": alert.alerts[0].score,
        "method": alert.alerts[0].method,
        "evidence": alert.alerts[0].evidence,
    }
    index_alert(primary_alert_id, alert_data)
```

---

### 3. Agent B (Diagnosis) - 诊断索引 + 规则索引 ✅

**位置：** `agent-diagnosis/main.py`

#### 3.1 诊断索引
在诊断创建后自动索引：

```python
# 诊断写入 DB 后
if diagnosis_id and index_diagnosis:
    diagnosis_data = {
        "asset_id": report.asset_id,
        "plant_id": report.plant_id,
        "root_cause": report.root_cause,
        "confidence": report.confidence,
        "impact": report.impact,
        "recommended_actions": report.recommended_actions,
        "evidence": report.evidence,
    }
    index_diagnosis(diagnosis_id, diagnosis_data)
```

#### 3.2 规则索引
在 Agent B 启动时自动索引所有规则文件：

```python
# 在 startup_event() 中
if index_rules:
    count = index_rules()
    print(f"[Agent B] Indexed {count} rules to vector DB")
```

---

### 4. Agent D (Review) - 反馈索引 + 聊天索引 ✅

**位置：** `agent-review/main.py`

#### 4.1 反馈索引
在 approve/reject 时自动索引：

```python
# Approve
if review_req and index_feedback:
    index_feedback(feedback_id, {
        "review_decision": "approved",
        "final_root_cause": diagnosis.get("root_cause"),
        "notes": b.notes,
        ...
    })

# Reject
if review_req and index_feedback:
    index_feedback(feedback_id, {
        "review_decision": "rejected",
        "notes": b.notes,
        ...
    })
```

#### 4.2 聊天消息索引
在聊天回答完成后自动索引（仅 assistant 消息，且内容长度 > 100）：

```python
# 在 chat_ask() 中，回答完成后
if index_chat_message:
    index_chat_message(msg_id, {
        "role": "assistant",
        "content": answer,
        "session_id": session_id_out,
        "tools_used": tools_used,
        "context": question,
    })
```

---

### 5. Agent D ReAct Tools - RAG 查询工具 ✅

**位置：** `agent-review/agent/tools.py`

新增 5 个 RAG 查询工具：

#### 5.1 `query_similar_diagnoses(query, limit=5)`
搜索相似历史诊断案例

**示例：**
```
query_similar_diagnoses("bearing wear vibration high")
```

**返回：**
```json
[
  {
    "diagnosis_id": 123,
    "similarity": "87.5%",
    "similarity_score": 0.875,
    "root_cause": "bearing_wear",
    "asset_id": "pump01",
    "confidence": 0.85,
    "text_preview": "Root cause: bearing wear..."
  }
]
```

#### 5.2 `query_similar_alerts(query, limit=5)`
搜索相似历史告警

**示例：**
```
query_similar_alerts("vibration sensor anomaly")
```

#### 5.3 `query_similar_feedback(query, limit=5)`
搜索相似历史反馈/审核决策

**示例：**
```
query_similar_feedback("approved bearing replacement")
```

#### 5.4 `query_similar_rules(query, limit=5)`
语义搜索相关规则（比关键词搜索更智能）

**示例：**
```
query_similar_rules("bearing temperature vibration correlation")
```

#### 5.5 `query_similar_chat(query, limit=3)`
搜索相似历史对话

**示例：**
```
query_similar_chat("how to diagnose bearing wear")
```

---

## 📋 使用流程

### 自动索引流程

1. **Agent A** 检测到告警 → 自动索引告警
2. **Agent B** 创建诊断 → 自动索引诊断
3. **Agent B** 启动时 → 自动索引所有规则文件
4. **Agent D** 审核通过/拒绝 → 自动索引反馈
5. **Agent D** 聊天回答完成 → 自动索引有价值的对话

### RAG 查询流程

在 Agent D 的聊天中，可以使用 RAG 工具：

```
用户: "帮我找一下类似 bearing wear 的历史案例"

Agent D 调用: query_similar_diagnoses("bearing wear")
返回: 相似诊断列表（包含 diagnosis_id、相似度、root_cause 等）

Agent D: "找到了 5 个相似案例，diagnosis_id=123 的相似度最高（87.5%）..."
```

---

## 🔧 配置要求

### 必需依赖

```bash
pip install sqlite-vec sentence-transformers
```

已在 `requirements.txt` 中添加：
- `sqlite-vec>=0.1.6`
- `sentence-transformers>=2.2.0`

### 可选功能

如果未安装依赖，RAG 功能会自动禁用，不影响主流程：
- 索引函数会静默失败
- RAG 查询工具会返回 "RAG not available" 消息

---

## 📊 数据流图

```
Agent A (告警)
    ↓ index_alert()
vec_memory (向量库)

Agent B (诊断)
    ↓ index_diagnosis()
    ↓ index_rules() [启动时]
vec_memory (向量库)

Agent D (审核)
    ↓ index_feedback() [approve/reject]
    ↓ index_chat_message() [聊天完成]
vec_memory (向量库)

Agent D (查询)
    ↓ query_similar_*() [ReAct tools]
    ← 返回相似结果
```

---

## 🎯 下一步建议

1. **Ticket 索引**：在 `insert_ticket()` 调用后添加 `index_ticket()`
2. **Vision 索引**：在视觉分析创建后添加 `index_vision_analysis()`
3. **前端集成**：在前端展示"相似案例"功能
4. **性能优化**：批量索引、异步索引

---

## 📝 注意事项

1. **自动创建表**：第一次调用索引函数时会自动创建 `vec_memory` 虚拟表
2. **失败容错**：所有索引操作都有异常处理，失败不会影响主流程
3. **可选功能**：如果未安装 RAG 依赖，功能会自动禁用
4. **维度匹配**：默认使用 `all-MiniLM-L6-v2`（384 维），如需更换模型需确保维度一致
