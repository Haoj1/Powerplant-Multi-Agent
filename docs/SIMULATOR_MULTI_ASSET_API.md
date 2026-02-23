# Simulator Multi-Asset API Documentation

## Overview

The Simulator now supports **running multiple assets (machines) simultaneously**, each running independently. It also supports **manual alert triggering** for testing.

---

## Multi-Asset Support

### Architecture Change

- **Before**: Single `executor`, only one scenario at a time
- **Now**: `executors` dict (`asset_id -> executor`), can run multiple scenarios in parallel

### Scenario JSON Format

All scenario JSON files must include `plant_id` and `asset_id`:

```json
{
  "version": "1.0",
  "name": "healthy_baseline",
  "plant_id": "plant01",
  "asset_id": "pump01",  // Required: asset ID
  "description": "...",
  "seed": 12345,
  "duration_sec": 600,
  ...
}
```

If not specified, defaults to `plant01` and `pump01`.

---

## API Endpoints

### 1. Load Scenario

**`POST /scenario/load`**

Load scenario for the specified asset (asset_id read from scenario JSON).

**Request Body:** See spec.

**Note**: If that asset_id already has a running scenario, it will be stopped automatically.

---

### 2. Start Scenario (per asset)

**`POST /scenario/start/{asset_id}`**

Start the scenario for the specified asset.

---

### 3. Stop Scenario (per asset)

**`POST /scenario/stop/{asset_id}`**

Stop the scenario for the specified asset.

---

### 4. Stop All Scenarios

**`POST /scenario/stop`**

Stop all running scenarios.

---

### 5. Reset Scenario (per asset)

**`POST /scenario/reset/{asset_id}`**

Reset the scenario to its initial state.

---

### 6. Query Status

**`GET /status`** - All assets

**`GET /status?asset_id=pump01`** - Single asset

---

### 7. List All Scenarios

**`GET /scenarios`**

List all loaded scenarios.

---

### 8. Manual Alert Trigger (testing)

**`POST /alert/trigger`**

Manually trigger an alert, published to MQTT for Agent A to process.

**Use cases:**
- Test alert flow (Agent A → Agent B → Agent C → Agent D)
- Verify frontend alert display
- Test RAG similar-alert queries

---

## Usage Examples

### Example 1: Run Two Assets Simultaneously

```python
import requests

BASE_URL = "http://localhost:8001"

# Load pump01 scenario
with open("scenarios/healthy_baseline.json") as f:
    scenario1 = json.load(f)
    scenario1["asset_id"] = "pump01"

requests.post(f"{BASE_URL}/scenario/load", json={"scenario": scenario1})

# Load pump02 scenario
with open("scenarios/bearing_wear_chronic.json") as f:
    scenario2 = json.load(f)
    scenario2["asset_id"] = "pump02"

requests.post(f"{BASE_URL}/scenario/load", json={"scenario": scenario2})

# Start both
requests.post(f"{BASE_URL}/scenario/start/pump01")
requests.post(f"{BASE_URL}/scenario/start/pump02")

# Check status
status = requests.get(f"{BASE_URL}/status").json()
print(f"Running assets: {[a['asset_id'] for a in status['assets'] if a['running']]}")
```

### Example 2: Manual Alert Trigger Test

```python
alert = {
    "asset_id": "pump01",
    "signal": "vibration_rms",
    "severity": "critical",
    "score": 5.0,
    "method": "manual",
    "evidence": {"test": True}
}

response = requests.post(f"{BASE_URL}/alert/trigger", json=alert)
# Alert is published to MQTT topic: alerts/pump01
# Agent A processes and forwards to Agent B
```

---

## Agent D Frontend Integration

### Scenario Management Page

1. **Scenario list**: Show all loaded scenarios (`GET /scenarios`), asset_id, name, status, current time
2. **Load scenario**: Form for JSON file or manual input; editable `asset_id`; call `POST /scenario/load`
3. **Control buttons**: Start / Stop / Reset per asset; call `POST /scenario/start/{asset_id}` etc.
4. **Manual alert trigger**: Form (asset_id, signal, severity, score); call `POST /alert/trigger`

---

## Notes

1. **Thread safety**: `_executors_lock` protects `executors` dict
2. **Resource cleanup**: Threads cleaned on scenario stop
3. **MQTT topics**: Each asset publishes to `telemetry/{asset_id}` and `alerts/{asset_id}`
4. **Database**: All telemetry in same DB, distinguished by `asset_id`

---

## Migration Guide

### Old (single asset)

```python
requests.post("/scenario/load", json={"scenario": scenario})
requests.post("/scenario/start")
```

### New (multi-asset)

```python
scenario["asset_id"] = "pump01"
requests.post("/scenario/load", json={"scenario": scenario})
requests.post("/scenario/start/pump01")
```

---

## Summary

✅ **Multi-asset** - Run multiple scenarios in parallel  
✅ **Manual alert trigger** - Easy testing  
✅ **Backward compatible** - Default asset_id="pump01"  
✅ **Thread safe** - Lock protects shared state
