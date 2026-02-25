"""LangChain tools for diagnosis: query_rules, query_telemetry, query_alerts."""

from pathlib import Path
from typing import List, Optional

from langchain_core.tools import tool

# Lazy imports to avoid loading db when not used
_db = None


def _get_db():
    global _db
    if _db is None:
        try:
            from shared_lib import db as shared_db
            _db = shared_db
        except ImportError:
            pass
    return _db


def _get_rules_dir() -> Path:
    from shared_lib.config import get_settings
    settings = get_settings()
    rules_path = Path(settings.diagnosis_rules_path)
    if not rules_path.is_absolute():
        project_root = Path(__file__).resolve().parent.parent.parent
        rules_path = project_root / rules_path
    return rules_path


@tool
def query_rules(keywords: str) -> str:
    """
    Search diagnosis rules by symptom, signal name, or keywords.
    Use this to find which fault types match the observed symptoms.
    Keywords can be: signal names (e.g. vibration_rms, bearing_temp_c, flow_m3h),
    fault types (e.g. bearing_wear, clogging, valve_stuck), or symptom descriptions.
    Returns matching rule content as markdown.
    """
    rules_dir = _get_rules_dir()
    if not rules_dir.exists():
        return "No rules directory found."
    kw_lower = keywords.lower().strip()
    if not kw_lower:
        return "Please provide keywords to search (e.g. vibration, bearing, clogging, flow)."
    results: List[str] = []
    for f in sorted(rules_dir.glob("*.md")):
        content = f.read_text(encoding="utf-8")
        if kw_lower in content.lower() or any(
            k in content.lower() for k in kw_lower.split()
        ):
            results.append(f"--- {f.stem} ---\n{content}")
    if not results:
        return f"No rules matched keywords: {keywords}. Try broader terms or check signal names."
    return "\n\n".join(results[:5])  # Limit to 5 matches


@tool
def query_telemetry(
    asset_id: str,
    since_ts: Optional[str] = None,
    until_ts: Optional[str] = None,
    limit: int = 50,
) -> str:
    """
    Query recent telemetry for an asset from the database.
    asset_id: e.g. pump01, pump02
    since_ts: optional ISO timestamp (e.g. 2025-02-11T10:00:00). If not provided, no lower bound.
    until_ts: optional ISO timestamp for upper bound. If not provided, no upper bound.
    limit: max rows to return (default 50)
    Returns telemetry as formatted text for analysis.
    """
    db = _get_db()
    if not db:
        return "Database not available."
    try:
        rows = db.query_telemetry(
            asset_id=asset_id, since_ts=since_ts, until_ts=until_ts, limit=limit
        )
    except Exception as e:
        return f"Query error: {e}"
    if not rows:
        return f"No telemetry found for asset {asset_id}."
    lines = []
    for r in rows[:20]:  # Format first 20
        ts = r.get("ts", "")
        p = r.get("pressure_bar")
        f = r.get("flow_m3h")
        t = r.get("temp_c")
        bt = r.get("bearing_temp_c")
        v = r.get("vibration_rms")
        rpm = r.get("rpm")
        cur = r.get("motor_current_a")
        valve = r.get("valve_open_pct")
        fault = r.get("fault", "")
        lines.append(
            f"{ts} | P={p:.2f} F={f:.2f} T={t:.2f} BT={bt:.2f} Vib={v:.2f} RPM={rpm:.1f} I={cur:.2f} Valve={valve:.1f} fault={fault}"
        )
    if len(rows) > 20:
        lines.append(f"... and {len(rows) - 20} more rows")
    return "\n".join(lines)


@tool
def query_alerts(
    asset_id: str,
    limit: int = 10,
    since_ts: Optional[str] = None,
    until_ts: Optional[str] = None,
) -> str:
    """
    Query recent alerts for an asset from the database.
    asset_id: e.g. pump01, pump02
    limit: max alerts to return (default 10)
    since_ts: optional ISO timestamp for lower bound.
    until_ts: optional ISO timestamp for upper bound.
    Returns alert details for context.
    """
    db = _get_db()
    if not db:
        return "Database not available."
    try:
        rows = db.query_alerts(
            asset_id=asset_id, limit=limit, since_ts=since_ts, until_ts=until_ts
        )
    except Exception as e:
        return f"Query error: {e}"
    if not rows:
        return f"No alerts found for asset {asset_id}."
    lines = []
    for r in rows:
        aid = r.get("id", "")
        ts = r.get("ts", "")
        sev = r.get("severity", "")
        sig = r.get("signal", "")
        score = r.get("score")
        method = r.get("method", "")
        ev = r.get("evidence", {})
        ev_str = str(ev) if ev else ""
        lines.append(f"[id={aid}] {ts} severity={sev} signal={sig} score={score} method={method} evidence={ev_str}")
    return "\n".join(lines)


@tool
def get_telemetry_window(
    asset_id: str,
    window_sec: int = 60,
) -> str:
    """
    Fetch recent telemetry for an asset over the last N seconds.
    Use this to analyze trends, check sustained values, or see how signals evolved.
    asset_id: e.g. pump01, pump02
    window_sec: how many seconds of history to fetch (default 60)
    Returns telemetry rows in chronological order (oldest first) for trend analysis.
    """
    db = _get_db()
    if not db:
        return "Database not available."
    try:
        rows = db.query_telemetry_window(asset_id=asset_id, window_sec=window_sec)
    except Exception as e:
        return f"Query error: {e}"
    if not rows:
        return f"No telemetry found for asset {asset_id} in the last {window_sec} seconds."
    lines = []
    for r in rows[:50]:
        ts = r.get("ts", "")
        p = r.get("pressure_bar")
        f = r.get("flow_m3h")
        t = r.get("temp_c")
        bt = r.get("bearing_temp_c")
        v = r.get("vibration_rms")
        rpm = r.get("rpm")
        cur = r.get("motor_current_a")
        valve = r.get("valve_open_pct")
        fault = r.get("fault", "")
        lines.append(
            f"{ts} | P={p:.2f} F={f:.2f} T={t:.2f} BT={bt:.2f} Vib={v:.2f} RPM={rpm:.1f} I={cur:.2f} Valve={valve:.1f} fault={fault}"
        )
    if len(rows) > 50:
        lines.append(f"... and {len(rows) - 50} more rows")
    return "\n".join(lines)


@tool
def compute_slope(
    asset_id: str,
    signal: str,
    window_sec: int = 60,
) -> str:
    """
    Compute the trend (slope) of a signal over the last N seconds.
    Use this to detect gradual increase (e.g. bearing wear) or sudden drop (e.g. clogging).
    asset_id: e.g. pump01, pump02
    signal: one of pressure_bar, flow_m3h, temp_c, bearing_temp_c, vibration_rms, rpm, motor_current_a, valve_open_pct
    window_sec: time window for slope calculation (default 60)
    Returns slope (change per second), mean, std, and sample count.
    Positive slope = increasing; negative slope = decreasing.
    """
    db = _get_db()
    if not db:
        return "Database not available."
    valid_signals = [
        "pressure_bar", "flow_m3h", "temp_c", "bearing_temp_c",
        "vibration_rms", "rpm", "motor_current_a", "valve_open_pct",
    ]
    if signal not in valid_signals:
        return f"Invalid signal. Use one of: {', '.join(valid_signals)}"
    try:
        rows = db.query_telemetry_window(asset_id=asset_id, window_sec=window_sec)
    except Exception as e:
        return f"Query error: {e}"
    if len(rows) < 2:
        return f"Not enough data for slope (need at least 2 points). Found {len(rows)} for asset {asset_id}."
    values = [r.get(signal) for r in rows if r.get(signal) is not None]
    if len(values) < 2:
        return f"No valid {signal} values in the window."
    n = len(values)
    mean = sum(values) / n
    variance = sum((x - mean) ** 2 for x in values) / n
    std = variance ** 0.5
    t0 = rows[0].get("ts")
    t_last = rows[-1].get("ts")
    try:
        from datetime import datetime
        dt0 = datetime.fromisoformat(t0.replace("Z", "+00:00")) if isinstance(t0, str) else t0
        dt1 = datetime.fromisoformat(t_last.replace("Z", "+00:00")) if isinstance(t_last, str) else t_last
        dt_sec = (dt1 - dt0).total_seconds()
    except Exception:
        dt_sec = window_sec
    slope = (values[-1] - values[0]) / dt_sec if dt_sec > 0 else 0.0
    return (
        f"signal={signal} window_sec={window_sec} asset={asset_id}\n"
        f"slope={slope:.6f} (per second) mean={mean:.4f} std={std:.4f} count={n}\n"
        f"Interpretation: {'increasing' if slope > 0 else 'decreasing' if slope < 0 else 'stable'} trend"
    )


def get_diagnosis_tools() -> List:
    """Return list of LangChain tools for the diagnosis agent."""
    return [
        query_rules,
        query_telemetry,
        query_alerts,
        get_telemetry_window,
        compute_slope,
    ]
