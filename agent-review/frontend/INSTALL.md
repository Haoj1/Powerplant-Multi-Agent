# Agent D Frontend Installation Guide

## Prerequisites

- Node.js >= 16.0.0
- npm >= 7.0.0

## Installation Steps

### 1. Enter the frontend directory

```bash
cd agent-review/frontend
```

### 2. Install dependencies

```bash
npm install
```

### 3. Start the development server

```bash
npm run dev
```

The frontend will start at `http://localhost:3000`.

## Configuration

### API Proxy

The frontend accesses backend APIs via Vite proxy:
- Agent D Backend: `http://localhost:8005` (proxied to `/api`)
- Simulator: `http://localhost:8001` (direct access)

To modify, edit `vite.config.js`.

## Development

### Project Structure

```
frontend/
├── src/
│   ├── components/      # Components
│   │   ├── layout/      # Layout components
│   │   ├── review/      # Review Queue components
│   │   ├── alerts/      # Alerts components
│   │   ├── sensors/     # Sensors components
│   │   ├── chat/        # Chat components
│   │   ├── scenarios/   # Scenarios components
│   │   └── common/      # Common components
│   ├── pages/           # Page components
│   ├── services/        # API services
│   ├── hooks/           # Custom hooks
│   ├── utils/           # Utility functions
│   ├── App.jsx          # Main app
│   └── main.jsx         # Entry point
├── public/              # Static assets
├── package.json
└── vite.config.js
```

### Skeleton files created

- ✅ Project config (package.json, vite.config.js)
- ✅ Routes and layout (App.jsx, DashboardLayout)
- ✅ 5 page skeletons (ReviewQueue, Alerts, Sensors, Chat, Scenarios)
- ✅ API services (api.js, simulatorApi.js)
- ✅ Placeholder components (all components have placeholder implementations)

### Next steps

Components to implement:
1. ReviewQueuePage components (ReviewListTable, DiagnosisDetailModal)
2. AlertsPage components (AlertsTable)
3. SensorsPage components (SensorDashboard, AssetSelector)
4. ChatPage components (ChatLayout, ReAct step display)
5. ScenariosPage components (ScenarioListTable, LoadScenarioModal, TriggerAlertModal)

## Build for production

```bash
npm run build
```

Output is in the `dist/` directory.

## Troubleshooting

### Port conflict

If port 3000 is in use, change `server.port` in `vite.config.js`.

### API connection failed

Ensure:
1. Agent D backend is running at `http://localhost:8005`
2. Simulator is running at `http://localhost:8001`
3. CORS is configured (backend has `allow_origins=["*"]`)
