"""
SQLite write layer for monitoring data.
Used by Simulator and agents in addition to JSONL logs (logs are kept as-is).
Python stdlib sqlite3 only; no extra dependency.
"""

import json
import sqlite3
import threading
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
    with _lock:
        conn = get_connection()
        try:
            cur = conn.execute(
                """SELECT id, diagnosis_id, plant_id, asset_id, ts, status, created_at, resolved_at
                   FROM review_requests WHERE status = ? ORDER BY created_at DESC LIMIT ?""",
                (status, limit),
            )
            rows = cur.fetchall()
            cols = [c[0] for c in cur.description]
            return [dict(zip(cols, r)) for r in rows]
        finally:
            conn.close()


def insert_review_request(
    diagnosis_id: int,
    plant_id: str,
    asset_id: str,
    ts: str,
    status: str = "pending",
) -> None:
    """Insert a review request for Agent D."""
    with _lock:
        conn = get_connection()
        try:
            conn.execute(
                """INSERT INTO review_requests (diagnosis_id, plant_id, asset_id, ts, status)
                   VALUES (?,?,?,?,?)""",
                (diagnosis_id, plant_id, asset_id, ts, status),
            )
            conn.commit()
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
) -> None:
    with _lock:
        conn = get_connection()
        try:
            conn.execute(
                """INSERT INTO tickets (ts, plant_id, asset_id, ticket_id, title, body, status, diagnosis_id)
                   VALUES (?,?,?,?,?,?,?,?)""",
                (ts, plant_id, asset_id, ticket_id, title, body, status, diagnosis_id),
            )
            conn.commit()
        finally:
            conn.close()


def query_telemetry(
    asset_id: str,
    since_ts: Optional[str] = None,
    limit: int = 100,
) -> List[Dict[str, Any]]:
    """Query telemetry for an asset, optionally since a timestamp. Returns list of dicts."""
    with _lock:
        conn = get_connection()
        try:
            if since_ts:
                cur = conn.execute(
                    """SELECT ts, plant_id, asset_id, pressure_bar, flow_m3h, temp_c, bearing_temp_c,
                              vibration_rms, rpm, motor_current_a, valve_open_pct, fault, severity
                       FROM telemetry WHERE asset_id = ? AND ts >= ?
                       ORDER BY ts DESC LIMIT ?""",
                    (asset_id, since_ts, limit),
                )
            else:
                cur = conn.execute(
                    """SELECT ts, plant_id, asset_id, pressure_bar, flow_m3h, temp_c, bearing_temp_c,
                              vibration_rms, rpm, motor_current_a, valve_open_pct, fault, severity
                       FROM telemetry WHERE asset_id = ?
                       ORDER BY ts DESC LIMIT ?""",
                    (asset_id, limit),
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
) -> List[Dict[str, Any]]:
    """Query recent alerts for an asset. Returns list of dicts."""
    with _lock:
        conn = get_connection()
        try:
            if since_ts:
                cur = conn.execute(
                    """SELECT id, ts, plant_id, asset_id, severity, signal, score, method, evidence
                       FROM alerts WHERE asset_id = ? AND ts >= ?
                       ORDER BY ts DESC LIMIT ?""",
                    (asset_id, since_ts, limit),
                )
            else:
                cur = conn.execute(
                    """SELECT id, ts, plant_id, asset_id, severity, signal, score, method, evidence
                       FROM alerts WHERE asset_id = ?
                       ORDER BY ts DESC LIMIT ?""",
                    (asset_id, limit),
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
