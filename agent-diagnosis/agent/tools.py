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


def get_diagnosis_tools() -> List:
    """Return list of LangChain tools for the diagnosis agent."""
    return [query_rules, query_telemetry, query_alerts]
