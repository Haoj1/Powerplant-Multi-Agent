# AI Agent（LangChain/LangGraph）与多模态扩展说明

## 1. 当前架构 vs AI Agent

### 当前实现（无 LLM）
- **Agent A**：规则/阈值检测，无 LangChain/LangGraph，无 LLM。
- **Agent B/C/D**（规划中）：目前设计也是规则/模板为主。

### 若要做「AI Agent」、用上 LangChain/LangGraph

**何时、在哪里用：**

| 环节 | 适合用 LLM + LangChain/LangGraph 的场景 | 何时需要 API Key |
|------|----------------------------------------|------------------|
| **Agent B（诊断）** | 把 alerts + 最近 telemetry 摘要喂给 LLM，生成 root cause、confidence、recommended_actions；或用 LangGraph 做多步推理（先假设再验证）。 | ✅ 需要 `OPENAI_API_KEY` 或 `DEEPSEEK_API_KEY` |
| **Agent C（工单）** | 用 LLM 根据诊断报告生成工单 title/body，更自然；或做摘要。 | ✅ 需要 API Key |
| **Agent D（审核）** | 用 LLM 总结审核意见、或从自然语言生成结构化 feedback。 | ✅ 需要 API Key |
| **协调/编排** | 用 LangGraph 定义多 Agent 工作流（Monitor → Diagnosis → Ticket → Review），带条件分支、重试。 | ✅ 需要 API Key |

**结论：**  
- 现在代码里**还没有**任何 LLM 调用，所以 `.env` 里的 `OPENAI_API_KEY` / `DEEPSEEK_API_KEY` **目前不会被用到**。  
- 要在「AI agent」层面用上这些 key，需要在 **Agent B（或 C/D/编排）** 里接入 LangChain/LangGraph + 调用你配置的 API。

---

## 2. API Key 配置与安全

- 把 **真实 key 写在 `.env.example` 里并提交到 Git 有泄露风险**。  
- 建议：  
  - **`.env.example`**：只写占位，例如 `OPENAI_API_KEY=`、`DEEPSEEK_API_KEY=`，不写真实 key。  
  - **`.env`**：本地填写真实 key，并确保 `.env` 已在 `.gitignore` 中（本项目已忽略）。  
- 需要用时：在代码里用 `os.getenv("OPENAI_API_KEY")` 或 `settings.openai_api_key`（若用 pydantic-settings）读取即可。

---

## 3. 3D 仿真 + VLM + 多模态

### 当前 Simulator
- 只有**一维时间序列传感器数据**（压力、流量、温度、振动等），无图像、无 3D 场景。

### 3D 仿真 + VLM 是否可行？
- **可行，但属于扩展**：  
  - 3D：需要另一套仿真（如 Unity/Unreal 或 PyBullet/MuJoCo，或数字孪生平台）渲染 3D 场景。  
  - VLM：输入是**图像/视频**。做法可以是：用 3D 仿真定期渲染一张图（或从「虚拟摄像头」取图），把这张图发给 VLM，让 VLM 描述场景（例如“泵附近有烟雾”“管路泄漏”），再把这段描述作为**额外输入**送给 Agent。  
- 这样，Agent 就有两类输入：**传感器数值 + 视觉描述**，可以做成多模态决策（例如：传感器说压力异常 + VLM 说“可见泄漏” → 更高置信度）。

### 只有传感器数据算「多模态」吗？
- 一般**不算**。  
- 多模态通常指：**多种模态的输入**，例如 **数值/时序 + 图像/视频 + 文本**。  
- 若只有传感器时序，通常叫「单模态（传感器/时序）」。  
- 要算多模态，需要至少再引入一种模态，例如：  
  - **图像**（3D 渲染或摄像头）+ VLM，或  
  - **文本**（报告、工单、日志）+ LLM。

### 小结
- **现在**：Simulator 仅传感器数据，无 3D、无 VLM；Agent 未用 LangChain/LangGraph，也未用你配置的 API key。  
- **若要做 AI Agent**：在 Agent B（或 C/D）里接入 LangChain/LangGraph，并读取 `.env` 里的 key 调用 LLM。  
- **若要做 3D + VLM 多模态**：增加 3D 仿真与渲染/截图，把图像喂给 VLM，再把 VLM 输出与传感器数据一起输入到 Agent。
