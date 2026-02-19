# Agent D Frontend 安装指南

## 前置要求

- Node.js >= 16.0.0
- npm >= 7.0.0

## 安装步骤

### 1. 进入前端目录

```bash
cd agent-review/frontend
```

### 2. 安装依赖

```bash
npm install
```

### 3. 启动开发服务器

```bash
npm run dev
```

前端将在 `http://localhost:3000` 启动。

## 配置

### API 代理

前端通过 Vite 代理访问后端 API：
- Agent D Backend: `http://localhost:8005` (代理到 `/api`)
- Simulator: `http://localhost:8001` (直接访问)

如需修改，编辑 `vite.config.js`。

## 开发

### 项目结构

```
frontend/
├── src/
│   ├── components/      # 组件
│   │   ├── layout/      # 布局组件
│   │   ├── review/      # Review Queue 组件
│   │   ├── alerts/      # Alerts 组件
│   │   ├── sensors/     # Sensors 组件
│   │   ├── chat/        # Chat 组件
│   │   ├── scenarios/   # Scenarios 组件
│   │   └── common/      # 通用组件
│   ├── pages/           # 页面组件
│   ├── services/        # API 服务
│   ├── hooks/           # 自定义 Hooks
│   ├── utils/           # 工具函数
│   ├── App.jsx          # 主应用
│   └── main.jsx         # 入口
├── public/              # 静态资源
├── package.json
└── vite.config.js
```

### 已创建的骨架文件

- ✅ 项目配置（package.json, vite.config.js）
- ✅ 路由和布局（App.jsx, DashboardLayout）
- ✅ 5 个页面骨架（ReviewQueue, Alerts, Sensors, Chat, Scenarios）
- ✅ API 服务（api.js, simulatorApi.js）
- ✅ 占位组件（所有组件都有占位实现）

### 下一步

需要实现的具体组件功能：
1. ReviewQueuePage 的组件（ReviewListTable, DiagnosisDetailModal）
2. AlertsPage 的组件（AlertsTable）
3. SensorsPage 的组件（SensorDashboard, AssetSelector）
4. ChatPage 的组件（ChatLayout, ReAct 步骤显示）
5. ScenariosPage 的组件（ScenarioListTable, LoadScenarioModal, TriggerAlertModal）

## 构建生产版本

```bash
npm run build
```

输出在 `dist/` 目录。

## 故障排查

### 端口冲突

如果 3000 端口被占用，修改 `vite.config.js` 中的 `server.port`。

### API 连接失败

确保：
1. Agent D 后端运行在 `http://localhost:8005`
2. Simulator 运行在 `http://localhost:8001`
3. CORS 已配置（后端已配置 `allow_origins=["*"]`）
