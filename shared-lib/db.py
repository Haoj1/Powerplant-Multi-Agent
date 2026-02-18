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
) -> None:
    """Insert one row per alert detail, or one row with first alert and rest in evidence."""
    with _lock:
        conn = get_connection()
        try:
            for a in alerts_list:
                conn.execute(
                    """INSERT INTO alerts (ts, plant_id, asset_id, severity, signal, score, method, evidence)
                       VALUES (?,?,?,?,?,?,?,?)""",
                    (
                        ts, plant_id, asset_id, severity,
                        a.get("signal"), a.get("score"), a.get("method"),
                        json.dumps(a.get("evidence")) if a.get("evidence") else None,
                    ),
                )
            conn.commit()
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
) -> None:
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
