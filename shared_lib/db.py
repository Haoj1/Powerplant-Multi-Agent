"""
SQLite write layer for monitoring data.
Used by Simulator and agents in addition to JSONL logs (logs are kept as-is).
Python stdlib sqlite3 only; no extra dependency.
"""

import json
import sqlite3
import threading
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

from .config import get_settings

_lock = threading.Lock()


def _db_path() -> Path:
    p = get_settings().sqlite_path
    return Path(p) if Path(p).is_absolute() else Path(__file__).resolve().parent.parent / p


def _ensure_dir():
    _db_path().parent.mkdir(parents=True, exist_ok=True)


def get_connection() -> sqlite3.Connection:
    _ensure_dir()
    return sqlite3.connect(str(_db_path()))


def insert_telemetry(
    ts: str,
    plant_id: str,
    asset_id: str,
    pressure_bar: float,
    flow_m3h: float,
    temp_c: float,
    bearing_temp_c: float,
    vibration_rms: float,
    rpm: float,
    motor_current_a: float,
    valve_open_pct: float,
    fault: str = "none",
    severity: float = 0.0,
) -> None:
    with _lock:
        conn = get_connection()
        try:
            conn.execute(
                """INSERT INTO telemetry (
                    ts, plant_id, asset_id, pressure_bar, flow_m3h, temp_c, bearing_temp_c,
                    vibration_rms, rpm, motor_current_a, valve_open_pct, fault, severity
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    ts, plant_id, asset_id, pressure_bar, flow_m3h, temp_c, bearing_temp_c,
                    vibration_rms, rpm, motor_current_a, valve_open_pct, fault, severity,
                ),
            )
            conn.commit()
        finally:
            conn.close()


def insert_alert(
    ts: str,
    plant_id: str,
    asset_id: str,
    severity: str,
    alerts_list: List[Dict[str, Any]],
) -> Optional[int]:
    """Insert one row per alert detail. Returns the id of the first inserted row (for Agent B linkage), or None."""
    with _lock:
        conn = get_connection()
        first_id = None
        try:
            for i, a in enumerate(alerts_list):
                conn.execute(
                    """INSERT INTO alerts (ts, plant_id, asset_id, severity, signal, score, method, evidence)
                       VALUES (?,?,?,?,?,?,?,?)""",
                    (
                        ts, plant_id, asset_id, severity,
                        a.get("signal"), a.get("score"), a.get("method"),
                        json.dumps(a.get("evidence")) if a.get("evidence") else None,
                    ),
                )
                if i == 0:
                    first_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
            conn.commit()
            return first_id
        finally:
            conn.close()


def insert_diagnosis(
    ts: str,
    plant_id: str,
    asset_id: str,
    root_cause: str,
    confidence: float,
    impact: str = "",
    recommended_actions: Optional[List[str]] = None,
    evidence: Optional[List[Dict[str, Any]]] = None,
    alert_id: Optional[int] = None,
) -> Optional[int]:
    """Insert diagnosis and return the inserted row id (for Agent C linkage)."""
    with _lock:
        conn = get_connection()
        try:
            conn.execute(
                """INSERT INTO diagnosis (ts, plant_id, asset_id, root_cause, confidence, impact, recommended_actions, evidence, alert_id)
                   VALUES (?,?,?,?,?,?,?,?,?)""",
                (
                    ts, plant_id, asset_id, root_cause, confidence, impact,
                    json.dumps(recommended_actions) if recommended_actions else None,
                    json.dumps(evidence) if evidence else None,
                    alert_id,
                ),
            )
            row_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
            conn.commit()
            return row_id
        finally:
            conn.close()


def query_review_requests(status: str = "pending", limit: int = 50) -> List[Dict[str, Any]]:
    """Query review requests by status (for Agent D)."""
    return query_review_requests_paginated(status=status, limit=limit, offset=0)[0]


def query_review_requests_paginated(
    status: str = "pending",
    limit: int = 50,
    offset: int = 0,
    asset_id: Optional[str] = None,
) -> tuple:
    """Query review requests with pagination. Returns (rows, total_count)."""
    with _lock:
        conn = get_connection()
        try:
            if status:
                where = "WHERE status = ?"
                params: list = [status]
            else:
                where = "WHERE 1=1"
                params = []
            if asset_id:
                where += " AND asset_id = ?"
                params.append(asset_id)
            base = "FROM review_requests " + where
            cur = conn.execute("SELECT COUNT(*) " + base, params)
            total = cur.fetchone()[0]
            cur = conn.execute(
                "SELECT id, diagnosis_id, plant_id, asset_id, ts, status, created_at, resolved_at "
                + base + " ORDER BY created_at DESC LIMIT ? OFFSET ?",
                params + [limit, offset],
            )
            rows = cur.fetchall()
            cols = [c[0] for c in cur.description]
            return [dict(zip(cols, r)) for r in rows], total
        finally:
            conn.close()


def get_review_request_by_diagnosis_id(diagnosis_id: int, status: str = "pending") -> Optional[Dict[str, Any]]:
    """Get review request by diagnosis_id (e.g. to check if already in queue)."""
    with _lock:
        conn = get_connection()
        try:
            cur = conn.execute(
                """SELECT id, diagnosis_id, plant_id, asset_id, ts, status, created_at, resolved_at
                   FROM review_requests WHERE diagnosis_id = ? AND status = ? LIMIT 1""",
                (diagnosis_id, status),
            )
            row = cur.fetchone()
            if not row:
                return None
            cols = [c[0] for c in cur.description]
            return dict(zip(cols, row))
        finally:
            conn.close()


def insert_review_request(
    diagnosis_id: int,
    plant_id: str,
    asset_id: str,
    ts: str,
    status: str = "pending",
) -> Optional[int]:
    """Insert a review request for Agent D. Returns the new review_request id."""
    with _lock:
        conn = get_connection()
        try:
            conn.execute(
                """INSERT INTO review_requests (diagnosis_id, plant_id, asset_id, ts, status)
                   VALUES (?,?,?,?,?)""",
                (diagnosis_id, plant_id, asset_id, ts, status),
            )
            row_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
            conn.commit()
            return row_id
        finally:
            conn.close()


def insert_vision_image(ts: str, plant_id: str, asset_id: str, image_path: str) -> None:
    with _lock:
        conn = get_connection()
        try:
            conn.execute(
                """INSERT INTO vision_images (ts, plant_id, asset_id, image_path) VALUES (?,?,?,?)""",
                (ts, plant_id, asset_id, image_path),
            )
            conn.commit()
        finally:
            conn.close()


def query_vision_images(
    asset_id: Optional[str] = None,
    limit: int = 20,
) -> List[Dict[str, Any]]:
    """Query recent vision image records (ts, asset_id, image_path). Optionally filter by asset_id."""
    with _lock:
        conn = get_connection()
        try:
            if asset_id:
                cur = conn.execute(
                    """SELECT id, ts, plant_id, asset_id, image_path
                       FROM vision_images WHERE asset_id = ?
                       ORDER BY ts DESC LIMIT ?""",
                    (asset_id, limit),
                )
            else:
                cur = conn.execute(
                    """SELECT id, ts, plant_id, asset_id, image_path
                       FROM vision_images
                       ORDER BY ts DESC LIMIT ?""",
                    (limit,),
                )
            rows = cur.fetchall()
            cols = [c[0] for c in cur.description]
            return [dict(zip(cols, r)) for r in rows]
        finally:
            conn.close()


def insert_vision_analysis(
    ts: str,
    plant_id: str,
    asset_id: str,
    image_path: Optional[str],
    description: str,
    anomalies_detected: Optional[List[str]] = None,
    confidence: float = 0.0,
) -> None:
    with _lock:
        conn = get_connection()
        try:
            conn.execute(
                """INSERT INTO vision_analysis (ts, plant_id, asset_id, image_path, description, anomalies_detected, confidence)
                   VALUES (?,?,?,?,?,?,?)""",
                (
                    ts, plant_id, asset_id, image_path, description,
                    json.dumps(anomalies_detected) if anomalies_detected else None,
                    confidence,
                ),
            )
            conn.commit()
        finally:
            conn.close()


def insert_ticket(
    ts: str,
    plant_id: str,
    asset_id: str,
    ticket_id: str,
    title: str = "",
    body: str = "",
    status: str = "open",
    diagnosis_id: Optional[int] = None,
    url: Optional[str] = None,
) -> None:
    with _lock:
        conn = get_connection()
        try:
            conn.execute(
                """INSERT INTO tickets (ts, plant_id, asset_id, ticket_id, title, body, status, diagnosis_id, url)
                   VALUES (?,?,?,?,?,?,?,?,?)""",
                (ts, plant_id, asset_id, ticket_id, title, body, status, diagnosis_id, url),
            )
            conn.commit()
        finally:
            conn.close()


def query_telemetry(
    asset_id: str,
    since_ts: Optional[str] = None,
    until_ts: Optional[str] = None,
    limit: int = 100,
) -> List[Dict[str, Any]]:
    """Query telemetry for an asset, optionally in [since_ts, until_ts]. Returns list of dicts."""
    with _lock:
        conn = get_connection()
        try:
            conditions = ["asset_id = ?"]
            params: List[Any] = [asset_id]
            if since_ts:
                conditions.append("ts >= ?")
                params.append(since_ts)
            if until_ts:
                conditions.append("ts <= ?")
                params.append(until_ts)
            where = " AND ".join(conditions)
            params.append(limit)
            cur = conn.execute(
                f"""SELECT ts, plant_id, asset_id, pressure_bar, flow_m3h, temp_c, bearing_temp_c,
                           vibration_rms, rpm, motor_current_a, valve_open_pct, fault, severity
                   FROM telemetry WHERE {where}
                   ORDER BY ts DESC LIMIT ?""",
                tuple(params),
            )
            rows = cur.fetchall()
            cols = [c[0] for c in cur.description]
            return [dict(zip(cols, r)) for r in rows]
        finally:
            conn.close()


def query_telemetry_window(
    asset_id: str,
    window_sec: int = 60,
    limit: int = 200,
) -> List[Dict[str, Any]]:
    """Query telemetry for an asset in the last window_sec seconds. Returns rows in ascending ts order (oldest first)."""
    now = datetime.now(timezone.utc)
    since = now - timedelta(seconds=window_sec)
    since_ts = since.strftime("%Y-%m-%dT%H:%M:%S")
    until_ts = now.strftime("%Y-%m-%dT%H:%M:%S")
    with _lock:
        conn = get_connection()
        try:
            cur = conn.execute(
                """SELECT ts, plant_id, asset_id, pressure_bar, flow_m3h, temp_c, bearing_temp_c,
                          vibration_rms, rpm, motor_current_a, valve_open_pct, fault, severity
                   FROM telemetry WHERE asset_id = ? AND ts >= ? AND ts <= ?
                   ORDER BY ts ASC LIMIT ?""",
                (asset_id, since_ts, until_ts, limit),
            )
            rows = cur.fetchall()
            cols = [c[0] for c in cur.description]
            return [dict(zip(cols, r)) for r in rows]
        finally:
            conn.close()


def query_alerts(
    asset_id: str,
    limit: int = 20,
    since_ts: Optional[str] = None,
    until_ts: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Query recent alerts for an asset, optionally in [since_ts, until_ts]. Returns list of dicts."""
    with _lock:
        conn = get_connection()
        try:
            conditions = ["asset_id = ?"]
            params: List[Any] = [asset_id]
            if since_ts:
                conditions.append("ts >= ?")
                params.append(since_ts)
            if until_ts:
                conditions.append("ts <= ?")
                params.append(until_ts)
            where = " AND ".join(conditions)
            params.append(limit)
            cur = conn.execute(
                f"""SELECT id, ts, plant_id, asset_id, severity, signal, score, method, evidence
                   FROM alerts WHERE {where}
                   ORDER BY ts DESC LIMIT ?""",
                tuple(params),
            )
            rows = cur.fetchall()
            cols = [c[0] for c in cur.description]
            result = [dict(zip(cols, r)) for r in rows]
            for r in result:
                if r.get("evidence") and isinstance(r["evidence"], str):
                    try:
                        r["evidence"] = json.loads(r["evidence"])
                    except Exception:
                        pass
            return result
        finally:
            conn.close()


def get_diagnosis_by_id(diagnosis_id: int) -> Optional[Dict[str, Any]]:
    """Get a single diagnosis by id."""
    with _lock:
        conn = get_connection()
        try:
            cur = conn.execute(
                """SELECT id, ts, plant_id, asset_id, root_cause, confidence, impact,
                          recommended_actions, evidence, alert_id
                   FROM diagnosis WHERE id = ?""",
                (diagnosis_id,),
            )
            row = cur.fetchone()
            if not row:
                return None
            cols = [c[0] for c in cur.description]
            r = dict(zip(cols, row))
            for key in ("recommended_actions", "evidence"):
                if r.get(key) and isinstance(r[key], str):
                    try:
                        r[key] = json.loads(r[key])
                    except Exception:
                        pass
            return r
        finally:
            conn.close()


def get_diagnosis_by_alert_id(alert_id: int) -> Optional[Dict[str, Any]]:
    """Get the diagnosis linked to an alert (if any)."""
    with _lock:
        conn = get_connection()
        try:
            cur = conn.execute(
                """SELECT id, ts, plant_id, asset_id, root_cause, confidence, impact,
                          recommended_actions, evidence, alert_id
                   FROM diagnosis WHERE alert_id = ? ORDER BY ts DESC LIMIT 1""",
                (alert_id,),
            )
            row = cur.fetchone()
            if not row:
                return None
            cols = [c[0] for c in cur.description]
            r = dict(zip(cols, row))
            for key in ("recommended_actions", "evidence"):
                if r.get(key) and isinstance(r[key], str):
                    try:
                        r[key] = json.loads(r[key])
                    except Exception:
                        pass
            return r
        finally:
            conn.close()


def query_alerts_with_diagnosis_and_ticket(
    asset_id: Optional[str] = None,
    limit: int = 50,
) -> List[Dict[str, Any]]:
    """Query alerts with linked diagnosis_id and ticket_id (for Agent D Alerts list)."""
    return query_alerts_with_diagnosis_and_ticket_paginated(
        asset_id=asset_id, severity=None, limit=limit, offset=0
    )[0]


def query_alerts_with_diagnosis_and_ticket_paginated(
    asset_id: Optional[str] = None,
    severity: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
) -> tuple:
    """Query alerts with pagination. Returns (rows, total_count)."""
    with _lock:
        conn = get_connection()
        try:
            sel = """SELECT a.id as alert_id, a.ts, a.plant_id, a.asset_id, a.severity, a.signal, a.score,
                     d.id as diagnosis_id, t.id as ticket_row_id, t.ticket_id, t.url as ticket_url
                     FROM alerts a
                     LEFT JOIN diagnosis d ON d.alert_id = a.id
                     LEFT JOIN tickets t ON t.diagnosis_id = d.id"""
            where = ""
            params: list = []
            if asset_id:
                where += " AND a.asset_id = ?" if where else " WHERE a.asset_id = ?"
                params.append(asset_id)
            if severity:
                where += " AND a.severity = ?" if where else " WHERE a.severity = ?"
                params.append(severity)
            base = sel + where
            cur = conn.execute("SELECT COUNT(*) FROM alerts a" + where, params)
            total = cur.fetchone()[0]
            cur = conn.execute(
                base + " ORDER BY a.ts DESC LIMIT ? OFFSET ?",
                params + [limit, offset],
            )
            rows = cur.fetchall()
            cols = [c[0] for c in cur.description]
            return [dict(zip(cols, r)) for r in rows], total
        finally:
            conn.close()


def get_alert_by_id(alert_id: int) -> Optional[Dict[str, Any]]:
    """Get a single alert by id."""
    with _lock:
        conn = get_connection()
        try:
            cur = conn.execute(
                """SELECT id, ts, plant_id, asset_id, severity, signal, score, method, evidence
                   FROM alerts WHERE id = ?""",
                (alert_id,),
            )
            row = cur.fetchone()
            if not row:
                return None
            cols = [c[0] for c in cur.description]
            r = dict(zip(cols, row))
            if r.get("evidence") and isinstance(r["evidence"], str):
                try:
                    r["evidence"] = json.loads(r["evidence"])
                except Exception:
                    pass
            return r
        finally:
            conn.close()


def insert_chat_session(preview: Optional[str] = None) -> int:
    """Create chat session, return session id."""
    with _lock:
        conn = get_connection()
        try:
            conn.execute(
                "INSERT INTO chat_sessions (preview) VALUES (?)",
                (preview or "",),
            )
            row_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
            conn.commit()
            return row_id
        finally:
            conn.close()


def update_chat_session(session_id: int, preview: Optional[str] = None) -> None:
    """Update session updated_at and optionally preview."""
    with _lock:
        conn = get_connection()
        try:
            if preview is not None:
                conn.execute(
                    "UPDATE chat_sessions SET updated_at = datetime('now'), preview = ? WHERE id = ?",
                    (preview[:200] if preview else "", session_id),
                )
            else:
                conn.execute(
                    "UPDATE chat_sessions SET updated_at = datetime('now') WHERE id = ?",
                    (session_id,),
                )
            conn.commit()
        finally:
            conn.close()


def insert_chat_message(
    session_id: int,
    role: str,
    content: str,
    tool_calls: Optional[str] = None,
) -> int:
    """Insert chat message, return message id."""
    with _lock:
        conn = get_connection()
        try:
            conn.execute(
                """INSERT INTO chat_messages (session_id, role, content, tool_calls)
                   VALUES (?,?,?,?)""",
                (session_id, role, content, tool_calls),
            )
            row_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
            conn.commit()
            return row_id
        finally:
            conn.close()


def update_chat_message_content(message_id: int, content: str) -> None:
    """Update chat message content."""
    with _lock:
        conn = get_connection()
        try:
            conn.execute("UPDATE chat_messages SET content = ? WHERE id = ?", (content, message_id))
            conn.commit()
        finally:
            conn.close()


def insert_chat_step(
    message_id: int,
    step_type: str,
    step_order: int,
    tool_name: Optional[str] = None,
    tool_args: Optional[str] = None,
    content: Optional[str] = None,
    raw_result: Optional[str] = None,
) -> None:
    """Insert a ReAct step for a message."""
    with _lock:
        conn = get_connection()
        try:
            conn.execute(
                """INSERT INTO chat_steps (message_id, step_type, step_order, tool_name, tool_args, content, raw_result)
                   VALUES (?,?,?,?,?,?,?)""",
                (message_id, step_type, step_order, tool_name, tool_args, content, raw_result),
            )
            conn.commit()
        finally:
            conn.close()


def list_chat_sessions(limit: int = 20) -> List[Dict[str, Any]]:
    """List chat sessions by updated_at desc."""
    with _lock:
        conn = get_connection()
        try:
            cur = conn.execute(
                "SELECT id, created_at, updated_at, preview FROM chat_sessions ORDER BY updated_at DESC LIMIT ?",
                (limit,),
            )
            rows = cur.fetchall()
            cols = [c[0] for c in cur.description]
            return [dict(zip(cols, r)) for r in rows]
        finally:
            conn.close()


def get_chat_session_with_messages(session_id: int) -> Optional[Dict[str, Any]]:
    """Get session with messages and steps. Returns None if not found."""
    with _lock:
        conn = get_connection()
        try:
            cur = conn.execute(
                "SELECT id, created_at, updated_at, preview FROM chat_sessions WHERE id = ?",
                (session_id,),
            )
            row = cur.fetchone()
            if not row:
                return None
            cols = [c[0] for c in cur.description]
            session = dict(zip(cols, row))
            cur = conn.execute(
                "SELECT id, role, content, tool_calls, created_at FROM chat_messages WHERE session_id = ? ORDER BY id",
                (session_id,),
            )
            msg_rows = cur.fetchall()
            msg_cols = [c[0] for c in cur.description]
            messages = [dict(zip(msg_cols, r)) for r in msg_rows]
            for m in messages:
                if m.get("tool_calls") and isinstance(m["tool_calls"], str):
                    try:
                        m["tool_calls"] = json.loads(m["tool_calls"])
                    except Exception:
                        pass
                cur = conn.execute(
                    """SELECT step_type, step_order, tool_name, tool_args, content, raw_result
                       FROM chat_steps WHERE message_id = ? ORDER BY step_order""",
                    (m["id"],),
                )
                step_rows = cur.fetchall()
                step_cols = [c[0] for c in cur.description]
                m["steps"] = [dict(zip(step_cols, r)) for r in step_rows]
            session["messages"] = messages
            return session
        finally:
            conn.close()


def delete_chat_session(session_id: int) -> bool:
    """Delete a chat session and all its messages/steps. Returns True if deleted."""
    with _lock:
        conn = get_connection()
        try:
            cur = conn.execute("SELECT id FROM chat_messages WHERE session_id = ?", (session_id,))
            msg_ids = [r[0] for r in cur.fetchall()]
            for mid in msg_ids:
                conn.execute("DELETE FROM chat_steps WHERE message_id = ?", (mid,))
            conn.execute("DELETE FROM chat_messages WHERE session_id = ?", (session_id,))
            cur = conn.execute("DELETE FROM chat_sessions WHERE id = ?", (session_id,))
            conn.commit()
            return cur.rowcount > 0
        finally:
            conn.close()


def update_review_request_status(review_id: int, status: str) -> None:
    """Update review_request status and set resolved_at to now (e.g. approved, rejected)."""
    with _lock:
        conn = get_connection()
        try:
            conn.execute(
                "UPDATE review_requests SET status = ?, resolved_at = datetime('now') WHERE id = ?",
                (status, review_id),
            )
            conn.commit()
        finally:
            conn.close()


def insert_feedback(
    ts: str,
    plant_id: str,
    asset_id: str,
    ticket_id: str,
    review_decision: str,
    final_root_cause: Optional[str] = None,
    notes: Optional[str] = None,
) -> None:
    with _lock:
        conn = get_connection()
        try:
            conn.execute(
                """INSERT INTO feedback (ts, plant_id, asset_id, ticket_id, review_decision, final_root_cause, notes)
                   VALUES (?,?,?,?,?,?,?)""",
                (ts, plant_id, asset_id, ticket_id, review_decision, final_root_cause, notes),
            )
            conn.commit()
        finally:
            conn.close()
