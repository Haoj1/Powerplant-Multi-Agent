# Agent D Frontend Specification

## Overview

Agent D frontend is a React web app providing review queue management, real-time sensor monitoring, intelligent chat assistant, and Scenario management.

**Recommended stack:**
- React + React Router
- Axios (API calls)
- ReactMarkdown (message rendering)
- EventSource (SSE streaming)
- Optional: Material-UI / Ant Design / Tailwind CSS

---

## 1. Page Structure

### 1.1 Main Layout (Dashboard Layout)

```
┌─────────────────────────────────────────────────────────┐
│  Header: Agent D Review Dashboard                       │
├──────────┬──────────────────────────────────────────────┤
│          │                                              │
│ Sidebar  │  Main Content Area                          │
│          │  (switches based on route)                    │
│ - Review │                                              │
│ - Alerts │                                              │
│ - Sensors│                                              │
│ - Chat   │                                              │
│ - Scenarios│                                            │
│          │                                              │
└──────────┴──────────────────────────────────────────────┘
```

**Navigation:**
- Review Queue
- Alerts
- Sensors
- Chat
- Scenarios

---

## 2. Review Queue Page

### 2.1 Features

- Display pending diagnosis list (`status=pending`)
- Filter: asset_id, plant_id, time range
- Sort: created_at, priority
- View diagnosis details
- Review actions: Approve / Reject / Edit

### 2.2 UI Components

#### 2.2.1 Review List Table

| Column | Content |
|--------|---------|
| ID | review_request.id |
| Asset | asset_id (clickable → Sensors) |
| Diagnosis ID | diagnosis_id (clickable → details) |
| Root Cause | diagnosis.root_cause |
| Confidence | diagnosis.confidence (progress bar + %) |
| Created At | created_at (relative, e.g. "2 min ago") |
| Actions | Approve / Reject / View |

**Filters:**
- Status dropdown: pending / approved / rejected / all
- Asset ID input
- Plant ID input (optional)
- Time range picker (optional)

**Actions:**
- Click row → open Diagnosis Detail Modal
- Approve → open Approve Modal (notes input)
- Reject → open Reject Modal (notes input)

#### 2.2.2 Diagnosis Detail Modal

Shows full diagnosis info (see spec diagram).

### 2.3 API Calls

```javascript
// Get pending list
GET /api/review-requests?status=pending&asset_id=&limit=50

// Get diagnosis
GET /api/diagnosis/{diagnosis_id}

// Approve
POST /api/review/{review_id}/approve
Body: { notes: "...", create_salesforce_case: false }

// Reject
POST /api/review/{review_id}/reject
Body: { notes: "..." }
```

---

## 3. Alerts Page

### 3.1 Features

- List all alerts (with linked diagnosis and ticket)
- Links: Alert → Diagnosis → Ticket
- Filter: asset_id, severity, time range
- View alert details

### 3.2 UI Components

| Column | Content |
|--------|---------|
| ID | alert.id |
| Asset | asset_id |
| Signal | signal (e.g. vibration_rms) |
| Severity | severity (badge: warning/critical) |
| Score | score |
| Method | method (e.g. zscore) |
| Diagnosis | link to diagnosis_id |
| Ticket | link to ticket |
| Time | ts (relative) |

### 3.3 API Calls

```javascript
GET /api/alerts?asset_id=&limit=50
```

---

## 4. Sensors Page

### 4.1 Features

- Select asset (asset_id dropdown)
- Real-time sensor display (auto refresh)
- Sensor dashboard (visualization)
- History chart (optional)

### 4.2 UI Components

- Asset selector (asset dropdown, auto-refresh interval)
- Sensor dashboard grid (pressure, flow, temperature, etc.)
- Each sensor: value, unit, gauge, status color

### 4.3 API Calls

```javascript
GET /api/telemetry?asset_id=pump01&since_ts=&limit=100
// Auto refresh every 5 sec
```

---

## 5. Chat Page

### 5.1 Features

- Session management (new / load history)
- ReAct streaming (SSE)
- **Full ReAct step display** (no hiding)
- Markdown rendering
- Session persistence

### 5.2 UI Components

- Chat layout: session list + chat panel
- ReAct step display: Thought, Tool Call, Tool Result (permanent, expandable)
- Session list: preview, last update, load
- Input area: text input, Send, quick actions

**Important:**
- Steps permanently visible
- Full tool_args and raw_result
- Expand/collapse long results
- Streaming: steps append in real time

### 5.3 SSE Handling

```javascript
const eventSource = new EventSource(
  `/api/chat/ask?question=${encodeURIComponent(question)}&session_id=${sessionId}`
);
eventSource.onmessage = (event) => {
  const data = JSON.parse(event.data);
  if (data.type === 'step') appendStep(data.step);
  else if (data.type === 'result') {
    showAnswer(data.answer);
    eventSource.close();
  } else if (data.type === 'error') {
    showError(data.error);
    eventSource.close();
  }
};
```

### 5.4 API Calls

```javascript
GET /api/chat/sessions?limit=20
GET /api/chat/sessions/{session_id}
POST /api/chat/ask  // SSE response
```

---

## 6. Scenarios Page

### 6.1 Features

- List loaded scenarios
- Load new scenario (upload JSON or manual input)
- Control: Start / Stop / Reset
- Manual alert trigger (test)

### 6.2 UI Components

- Scenario list table
- Load scenario form (upload JSON, asset_id/plant_id editable)
- Manual alert trigger (test)

### 6.3 API Calls

```javascript
// Simulator API (port 8001)
GET ${SIMULATOR_URL}/scenarios
POST ${SIMULATOR_URL}/scenario/load
POST ${SIMULATOR_URL}/scenario/start/{asset_id}
POST ${SIMULATOR_URL}/scenario/stop/{asset_id}
POST ${SIMULATOR_URL}/scenario/reset/{asset_id}
GET ${SIMULATOR_URL}/status?asset_id={asset_id}
POST ${SIMULATOR_URL}/alert/trigger
```

---

## 7. Common Features

### 7.1 Routes

```
/           → Review Queue (default)
/review     → Review Queue
/alerts     → Alerts
/sensors    → Sensors
/chat       → Chat
/scenarios  → Scenario Management
```

### 7.2 Refresh Strategy

| Page | Refresh | Interval |
|------|---------|----------|
| Review Queue | Manual + poll | 30s |
| Alerts | Manual + poll | 30s |
| Sensors | Auto | 5s (configurable) |
| Chat | SSE | Event-driven |
| Scenarios | Manual | On demand |

### 7.3 Error Handling

- API error toast
- Network retry
- Loading spinner
- Empty state

### 7.4 Responsive

- Desktop: full layout
- Mobile: collapse sidebar, main features available

---

## 8. Component Checklist

### 8.1 Pages

- DashboardLayout
- ReviewQueuePage
- AlertsPage
- SensorsPage
- ChatPage
- ScenariosPage

### 8.2 Review Queue

- ReviewListTable
- ReviewFilters
- DiagnosisDetailModal
- ApproveModal
- RejectModal

### 8.3 Alerts

- AlertsTable
- AlertFilters
- AlertDetailModal (optional)

### 8.4 Sensors

- AssetSelector
- SensorDashboard
- SensorGauge
- TelemetryChart (optional)

### 8.5 Chat

- ChatLayout
- SessionList
- ChatPanel
- MessageList
- MessageItem
- ReactStep (ThoughtStep, ToolCallStep, ToolResultStep)
- ChatInput
- SSEHandler

### 8.6 Scenarios

- ScenarioListTable
- LoadScenarioModal
- ScenarioControls
- TriggerAlertModal
- ScenarioStatus

### 8.7 Common

- LoadingSpinner
- ErrorToast
- EmptyState
- TimeAgo
- Badge
- ConfidenceBar

---

## 9. State Management

- Option 1: React Context + useState
- Option 2: Redux / Zustand

---

## 10. Implementation Priority

### Phase 1: Core

1. Review Queue
2. Chat (with ReAct steps)

### Phase 2: Important

3. Alerts
4. Sensors

### Phase 3: Enhance

5. Scenarios
6. Chat enhancements

---

## 11. API Summary

### Agent D Backend (port 8005)

```
GET  /api/review-requests
GET  /api/diagnosis/{id}
GET  /api/alerts
GET  /api/telemetry
GET  /api/chat/sessions
GET  /api/chat/sessions/{id}
POST /api/chat/ask (SSE)
POST /api/review/{id}/approve
POST /api/review/{id}/reject
```

### Simulator (port 8001)

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

## 12. Reference

- Email-Agent frontend for SSE streaming, session management, Markdown
- **Key difference**: Agent D keeps ReAct steps visible; Email-Agent clears them after 2s

---

## 13. Technical Details

- SSE streaming via EventSource
- ReAct step rendering (Thought, ToolCall, ToolResult)
- Telemetry refresh interval

---

## 14. Summary

### Must Implement

1. Review Queue
2. Chat (with ReAct steps)
3. Alerts
4. Sensors
5. Scenarios

### Key Features

- ReAct steps always visible
- SSE streaming
- Multi-asset support
- Manual alert trigger (test)
