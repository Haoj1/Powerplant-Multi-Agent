# SQLite Database (querying & dashboard)

JSONL logs under `logs/` are **kept as-is**. The SQLite DB is an **additional** store for structured querying and a future web dashboard.

## Create schema (run once)

From project root:

```bash
python scripts/init_db.py
```

Creates `data/monitoring.db` (or path from `SQLITE_PATH` in `.env`).

## Dependencies

None beyond the standard library: Python’s built-in `sqlite3` is used. No extra entry in `requirements.txt`.

## Table layout and indexes

Each table has **time-oriented indexes** so agents can query by time range efficiently:

| Table            | Purpose                    | Indexes (time + asset) |
|------------------|----------------------------|-------------------------|
| **telemetry**    | One row per telemetry msg | `(asset_id, ts)`, `(ts)`, `(ts, asset_id)`, `(fault)` |
| **alerts**       | One row per alert detail   | `(asset_id, ts)`, `(ts)`, `(ts, asset_id)`, `(severity)` |
| **diagnosis**    | Agent B diagnosis reports  | `(asset_id, ts)`, `(ts)`, `(root_cause)`, `(alert_id)` |
| **vision_images**| Simulator image path only | `(asset_id, ts)`, `(ts)`, `(ts, asset_id)` |
| **vision_analysis** | Agent VLM analysis      | `(asset_id, ts)`, `(ts)`, `(ts, asset_id)` |
| **review_requests** | Agent C, queued for Agent D | `(status)`, `(diagnosis_id)`, `(asset_id, ts)` |
| **tickets**      | Agent D (after approval, e.g. SF Case) | `(asset_id, ts)`, `(status)`, `(ticket_id)`, `(diagnosis_id)` |
| **feedback**     | Agent D review feedback   | `(ticket_id)`, `(ts)`, `(ts, asset_id)` |

- **`(ts)`** — Query by time range (e.g. "last 1 hour")
- **`(ts, asset_id)`** — Time range first, then filter by asset
- **`(asset_id, ts)`** — Asset first, then time (e.g. "last N rows for pump")

## When each component writes to the DB

Writes happen **in addition to** existing JSONL/MQTT; logs are not replaced.

| Component     | When it writes | Table(s)        |
|--------------|----------------|-----------------|
| **Simulator**| After each telemetry publish and JSONL append (or every `DB_TELEMETRY_INTERVAL_SEC` sec if set) | `telemetry` |
| **Simulator**| After each vision image save + MQTT publish   | `vision_images` |
| **Agent A**  | After each alert publish + JSONL append      | `alerts` |
| **Agent B**  | After each diagnosis publish                 | `diagnosis` |
| **Agent C**  | On each diagnosis received                   | `review_requests` |
| **Agent**    | When it calls VLM and produces a description | `vision_analysis` (when implemented) |
| **Agent D**  | After approval, create SF Case/Work Order     | `tickets` |
| **Agent D**  | After submitting feedback                    | `feedback` (when implemented) |

## Example queries (for dashboard or scripts)

```sql
-- Alerts in last hour
SELECT * FROM alerts WHERE ts >= datetime('now', '-1 hour') ORDER BY ts DESC;

-- By asset
SELECT * FROM telemetry WHERE asset_id = 'pump01' AND ts >= datetime('now', '-10 minutes');

-- By fault type
SELECT * FROM telemetry WHERE fault != 'none' ORDER BY ts DESC LIMIT 100;

-- Count alerts by severity
SELECT severity, COUNT(*) FROM alerts GROUP BY severity;
```

## Config

In `.env`:

- `SQLITE_PATH=data/monitoring.db` — path to the DB file (relative to project root or absolute).
- `DB_TELEMETRY_INTERVAL_SEC=0` — write telemetry to DB every N seconds; `0` = every sim step (default). Set to e.g. `5` or `10` to reduce `telemetry` table growth (MQTT and JSONL are unchanged).
