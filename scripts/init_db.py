#!/usr/bin/env python3
"""
Create SQLite schema for monitoring data (telemetry, alerts, diagnosis, vision, tickets, feedback).
Run from project root: python scripts/init_db.py
Keeps existing JSONL logs; DB is for querying and future dashboard.
"""

import sys
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

try:
    from shared_lib.config import get_settings
except Exception:
    get_settings = None

DB_PATH = None
if get_settings:
    DB_PATH = get_settings().sqlite_path
else:
    DB_PATH = "data/monitoring.db"

# Path can be relative to project root
if not Path(DB_PATH).is_absolute():
    DB_PATH = str(project_root / DB_PATH)

SCHEMA_SQL = """
-- Telemetry (from Simulator; optional sampling to reduce rows)
CREATE TABLE IF NOT EXISTS telemetry (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts TEXT NOT NULL,
    plant_id TEXT NOT NULL,
    asset_id TEXT NOT NULL,
    pressure_bar REAL,
    flow_m3h REAL,
    temp_c REAL,
    bearing_temp_c REAL,
    vibration_rms REAL,
    rpm REAL,
    motor_current_a REAL,
    valve_open_pct REAL,
    fault TEXT NOT NULL DEFAULT 'none',
    severity REAL NOT NULL DEFAULT 0,
    created_at TEXT DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS ix_telemetry_asset_ts ON telemetry(asset_id, ts);
CREATE INDEX IF NOT EXISTS ix_telemetry_ts ON telemetry(ts);
CREATE INDEX IF NOT EXISTS ix_telemetry_ts_asset ON telemetry(ts, asset_id);
CREATE INDEX IF NOT EXISTS ix_telemetry_fault ON telemetry(fault);

-- Alerts (from Agent A)
CREATE TABLE IF NOT EXISTS alerts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts TEXT NOT NULL,
    plant_id TEXT NOT NULL,
    asset_id TEXT NOT NULL,
    severity TEXT NOT NULL,
    signal TEXT,
    score REAL,
    method TEXT,
    evidence TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS ix_alerts_asset_ts ON alerts(asset_id, ts);
CREATE INDEX IF NOT EXISTS ix_alerts_ts ON alerts(ts);
CREATE INDEX IF NOT EXISTS ix_alerts_ts_asset ON alerts(ts, asset_id);
CREATE INDEX IF NOT EXISTS ix_alerts_severity ON alerts(severity);

-- Diagnosis (from Agent B; alert_id = which alert triggered this diagnosis)
CREATE TABLE IF NOT EXISTS diagnosis (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts TEXT NOT NULL,
    plant_id TEXT NOT NULL,
    asset_id TEXT NOT NULL,
    root_cause TEXT NOT NULL,
    confidence REAL NOT NULL,
    impact TEXT,
    recommended_actions TEXT,
    evidence TEXT,
    alert_id INTEGER,
    created_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (alert_id) REFERENCES alerts(id)
);
CREATE INDEX IF NOT EXISTS ix_diagnosis_asset_ts ON diagnosis(asset_id, ts);
CREATE INDEX IF NOT EXISTS ix_diagnosis_ts ON diagnosis(ts);
CREATE INDEX IF NOT EXISTS ix_diagnosis_ts_asset ON diagnosis(ts, asset_id);
CREATE INDEX IF NOT EXISTS ix_diagnosis_root_cause ON diagnosis(root_cause);
CREATE INDEX IF NOT EXISTS ix_diagnosis_alert_id ON diagnosis(alert_id);

-- Vision images (from Simulator: image path only)
CREATE TABLE IF NOT EXISTS vision_images (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts TEXT NOT NULL,
    plant_id TEXT NOT NULL,
    asset_id TEXT NOT NULL,
    image_path TEXT NOT NULL,
    created_at TEXT DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS ix_vision_images_asset_ts ON vision_images(asset_id, ts);
CREATE INDEX IF NOT EXISTS ix_vision_images_ts ON vision_images(ts);
CREATE INDEX IF NOT EXISTS ix_vision_images_ts_asset ON vision_images(ts, asset_id);

-- Vision analysis (from Agent when it calls VLM)
CREATE TABLE IF NOT EXISTS vision_analysis (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts TEXT NOT NULL,
    plant_id TEXT NOT NULL,
    asset_id TEXT NOT NULL,
    image_path TEXT,
    description TEXT,
    anomalies_detected TEXT,
    confidence REAL,
    created_at TEXT DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS ix_vision_analysis_asset_ts ON vision_analysis(asset_id, ts);
CREATE INDEX IF NOT EXISTS ix_vision_analysis_ts ON vision_analysis(ts);
CREATE INDEX IF NOT EXISTS ix_vision_analysis_ts_asset ON vision_analysis(ts, asset_id);

-- Tickets (from Agent C)
CREATE TABLE IF NOT EXISTS tickets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts TEXT NOT NULL,
    plant_id TEXT NOT NULL,
    asset_id TEXT NOT NULL,
    ticket_id TEXT UNIQUE NOT NULL,
    title TEXT,
    body TEXT,
    status TEXT NOT NULL DEFAULT 'open',
    diagnosis_id INTEGER,
    created_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (diagnosis_id) REFERENCES diagnosis(id)
);
CREATE INDEX IF NOT EXISTS ix_tickets_asset_ts ON tickets(asset_id, ts);
CREATE INDEX IF NOT EXISTS ix_tickets_ts ON tickets(ts);
CREATE INDEX IF NOT EXISTS ix_tickets_ts_asset ON tickets(ts, asset_id);
CREATE INDEX IF NOT EXISTS ix_tickets_status ON tickets(status);
CREATE UNIQUE INDEX IF NOT EXISTS ix_tickets_ticket_id ON tickets(ticket_id);

-- Feedback (from Agent D)
CREATE TABLE IF NOT EXISTS feedback (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts TEXT NOT NULL,
    plant_id TEXT NOT NULL,
    asset_id TEXT NOT NULL,
    ticket_id TEXT NOT NULL,
    review_decision TEXT NOT NULL,
    final_root_cause TEXT,
    notes TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS ix_feedback_ticket_id ON feedback(ticket_id);
CREATE INDEX IF NOT EXISTS ix_feedback_ts ON feedback(ts);
CREATE INDEX IF NOT EXISTS ix_feedback_ts_asset ON feedback(ts, asset_id);
"""


MIGRATION_ADD_DIAGNOSIS_ALERT_ID = """
-- Add alert_id to diagnosis if missing (for existing DBs)
"""
def _migrate_diagnosis_alert_id(conn):
    cur = conn.execute("PRAGMA table_info(diagnosis)")
    cols = [row[1] for row in cur.fetchall()]
    if "alert_id" not in cols:
        conn.execute("ALTER TABLE diagnosis ADD COLUMN alert_id INTEGER REFERENCES alerts(id)")
        conn.execute("CREATE INDEX IF NOT EXISTS ix_diagnosis_alert_id ON diagnosis(alert_id)")
        conn.commit()
        print("Migration: added diagnosis.alert_id and index")


def main():
    import sqlite3
    Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.executescript(SCHEMA_SQL)
    conn.commit()
    _migrate_diagnosis_alert_id(conn)
    conn.close()
    print(f"Schema created: {DB_PATH}")
    print("Tables: telemetry, alerts, diagnosis, vision_images, vision_analysis, tickets, feedback")


if __name__ == "__main__":
    main()
