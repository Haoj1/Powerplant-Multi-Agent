# Agent D Frontend

React frontend for Agent D Review Dashboard.

## Installation

```bash
cd agent-review/frontend
npm install
```

## Development

```bash
npm run dev
```

Frontend will run on `http://localhost:3000`

Backend API proxy is configured to `http://localhost:8005` (Agent D backend).

## Build

```bash
npm run build
```

## Project Structure

```
frontend/
├── src/
│   ├── components/      # Reusable components
│   ├── pages/          # Page components
│   ├── hooks/          # Custom React hooks
│   ├── services/       # API services
│   ├── utils/          # Utility functions
│   ├── App.jsx         # Main app component
│   └── main.jsx        # Entry point
├── public/             # Static assets
├── package.json
└── vite.config.js
```

## Features

- Review Queue - Manage pending diagnoses
- Alerts List - View alerts with diagnosis/ticket links
- Real-time Sensors - Monitor asset telemetry
- Chat Panel - ReAct agent with full step visibility
- Scenario Management - Control simulator scenarios
