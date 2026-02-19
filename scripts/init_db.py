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

-- Diagnosis (from Agent B; alert_id added by migration below for new + existing DBs)
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
    created_at TEXT DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS ix_diagnosis_asset_ts ON diagnosis(asset_id, ts);
CREATE INDEX IF NOT EXISTS ix_diagnosis_ts ON diagnosis(ts);
CREATE INDEX IF NOT EXISTS ix_diagnosis_ts_asset ON diagnosis(ts, asset_id);
CREATE INDEX IF NOT EXISTS ix_diagnosis_root_cause ON diagnosis(root_cause);

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

-- Review requests (from Agent C; queued for Agent D approval)
CREATE TABLE IF NOT EXISTS review_requests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    diagnosis_id INTEGER NOT NULL,
    plant_id TEXT NOT NULL,
    asset_id TEXT NOT NULL,
    ts TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    created_at TEXT DEFAULT (datetime('now')),
    resolved_at TEXT,
    FOREIGN KEY (diagnosis_id) REFERENCES diagnosis(id)
);
CREATE INDEX IF NOT EXISTS ix_review_requests_status ON review_requests(status);
CREATE INDEX IF NOT EXISTS ix_review_requests_asset_ts ON review_requests(asset_id, ts);
CREATE INDEX IF NOT EXISTS ix_review_requests_diagnosis ON review_requests(diagnosis_id);

-- Chat (Agent D - conversation and ReAct steps persistence)
CREATE TABLE IF NOT EXISTS chat_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now')),
    preview TEXT
);
CREATE INDEX IF NOT EXISTS ix_chat_sessions_updated ON chat_sessions(updated_at);

CREATE TABLE IF NOT EXISTS chat_messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER NOT NULL,
    role TEXT NOT NULL,
    content TEXT NOT NULL DEFAULT '',
    created_at TEXT DEFAULT (datetime('now')),
    tool_calls TEXT,
    FOREIGN KEY (session_id) REFERENCES chat_sessions(id)
);
CREATE INDEX IF NOT EXISTS ix_chat_messages_session ON chat_messages(session_id);

CREATE TABLE IF NOT EXISTS chat_steps (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    message_id INTEGER NOT NULL,
    step_type TEXT NOT NULL,
    step_order INTEGER NOT NULL DEFAULT 0,
    tool_name TEXT,
    tool_args TEXT,
    content TEXT,
    raw_result TEXT,
    created_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (message_id) REFERENCES chat_messages(id)
);
CREATE INDEX IF NOT EXISTS ix_chat_steps_message ON chat_steps(message_id);

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
        conn.commit()
        print("Migration: added diagnosis.alert_id")
    conn.execute("CREATE INDEX IF NOT EXISTS ix_diagnosis_alert_id ON diagnosis(alert_id)")
    conn.commit()


def _migrate_tickets_url(conn):
    """Add url column to tickets if missing (for Salesforce Case/Work Order link)."""
    cur = conn.execute("PRAGMA table_info(tickets)")
    cols = [row[1] for row in cur.fetchall()]
    if "url" not in cols:
        conn.execute("ALTER TABLE tickets ADD COLUMN url TEXT")
        conn.commit()
        print("Migration: added tickets.url")


def _init_vector_table(conn):
    """
    Initialize vec0 virtual table for RAG (optional, requires sqlite-vec).
    Virtual tables are created dynamically and persist in the database.
    """
    try:
        import sqlite_vec
        conn.enable_load_extension(True)
        sqlite_vec.load(conn)
        conn.enable_load_extension(False)
        
        # Create vec_memory table with 384 dimensions (all-MiniLM-L6-v2)
        conn.execute("""
            create virtual table if not exists vec_memory using vec0(
                embedding float[384],
                metadata text
            );
        """)
        conn.commit()
        print("Vector table 'vec_memory' initialized (RAG support enabled)")
    except ImportError:
        # sqlite-vec not installed - skip, that's ok
        pass
    except Exception as e:
        # Extension load failed - skip, that's ok
        pass


def main():
    import sqlite3
    Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.executescript(SCHEMA_SQL)
    conn.commit()
    _migrate_diagnosis_alert_id(conn)
    _migrate_tickets_url(conn)
    _init_vector_table(conn)  # Optional: initialize vec0 virtual table if sqlite-vec available
    conn.close()
    print(f"Schema created: {DB_PATH}")
    print("Tables: telemetry, alerts, diagnosis, vision_images, vision_analysis, tickets, review_requests, chat_sessions, chat_messages, chat_steps, feedback")
    print("Note: vec_memory (virtual table) created if sqlite-vec is installed")


if __name__ == "__main__":
    main()
