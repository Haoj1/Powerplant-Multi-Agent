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
| **diagnosis**    | Agent B diagnosis reports  | `(asset_id, ts)`, `(ts)`, `(ts, asset_id)`, `(root_cause)`, `(alert_id)` — `alert_id` 关联触发的告警 |
| **vision_images**| Simulator image path only | `(asset_id, ts)`, `(ts)`, `(ts, asset_id)` |
| **vision_analysis** | Agent VLM analysis      | `(asset_id, ts)`, `(ts)`, `(ts, asset_id)` |
| **tickets**      | Agent C tickets           | `(asset_id, ts)`, `(ts)`, `(ts, asset_id)`, `(status)`, `(ticket_id)` |
| **feedback**     | Agent D review feedback   | `(ticket_id)`, `(ts)`, `(ts, asset_id)` |

- **`(ts)`** — 按时间范围查询（如「最近 1 小时」）
- **`(ts, asset_id)`** — 先按时间范围再按资产过滤
- **`(asset_id, ts)`** — 先按资产再按时间（如「某泵最近 N 条」）

## When each component writes to the DB

Writes happen **in addition to** existing JSONL/MQTT; logs are not replaced.

| Component     | When it writes | Table(s)        |
|--------------|----------------|-----------------|
| **Simulator**| After each telemetry publish and JSONL append (or every `DB_TELEMETRY_INTERVAL_SEC` sec if set) | `telemetry` |
| **Simulator**| After each vision image save + MQTT publish   | `vision_images` |
| **Agent A**  | After each alert publish + JSONL append      | `alerts` |
| **Agent B**  | After each diagnosis publish                 | `diagnosis` (when implemented) |
| **Agent**    | When it calls VLM and produces a description | `vision_analysis` (when implemented) |
| **Agent C**  | After creating a ticket                      | `tickets` (when implemented) |
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
