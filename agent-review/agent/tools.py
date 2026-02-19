"""LangChain tools for Agent D review chat."""

import json
from pathlib import Path
from typing import List, Optional

from langchain_core.tools import tool

# RAG / Vector search (optional)
try:
    from shared_lib.vector_db import search_text_in_vector_db
    _HAS_RAG = True
except ImportError:
    _HAS_RAG = False

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
def query_review_requests(status: str = "pending", asset_id: Optional[str] = None, limit: int = 20) -> str:
    """
    Query pending review requests. Use status='pending' for items awaiting approval.
    Optionally filter by asset_id.
    """
    db = _get_db()
    if not db:
        return "Database not available."
    try:
        rows = db.query_review_requests(status=status, limit=limit)
        if asset_id:
            rows = [r for r in rows if r.get("asset_id") == asset_id]
        if not rows:
            return f"No review requests with status={status}."
        lines = []
        for r in rows:
            lines.append(
                f"[id={r['id']}] diagnosis_id={r['diagnosis_id']} asset={r['asset_id']} "
                f"ts={r['ts']} status={r['status']}"
            )
        return "\n".join(lines)
    except Exception as e:
        return f"Query error: {e}"


@tool
def query_diagnosis(diagnosis_id: int) -> str:
    """Get full diagnosis details by id. Use this to inspect a specific diagnosis before approving."""
    db = _get_db()
    if not db:
        return "Database not available."
    try:
        d = db.get_diagnosis_by_id(diagnosis_id)
        if not d:
            return f"No diagnosis found for id={diagnosis_id}."
        actions = d.get("recommended_actions")
        if isinstance(actions, str):
            try:
                actions = json.loads(actions)
            except Exception:
                actions = []
        actions = actions or []
        evidence = d.get("evidence")
        if isinstance(evidence, str):
            try:
                evidence = json.loads(evidence)
            except Exception:
                evidence = []
        evidence = evidence or []
        parts = [
            f"Diagnosis id={d['id']}",
            f"  asset_id={d['asset_id']} plant_id={d['plant_id']} ts={d['ts']}",
            f"  root_cause={d['root_cause']} confidence={d['confidence']} impact={d.get('impact','')}",
            f"  recommended_actions: {actions}",
            f"  evidence: {evidence}",
        ]
        return "\n".join(parts)
    except Exception as e:
        return f"Query error: {e}"


@tool
def query_alerts(asset_id: str, limit: int = 10, since_ts: Optional[str] = None) -> str:
    """Query recent alerts for an asset."""
    db = _get_db()
    if not db:
        return "Database not available."
    try:
        rows = db.query_alerts(asset_id=asset_id, limit=limit, since_ts=since_ts)
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
        lines.append(f"[id={aid}] {ts} severity={sev} signal={sig} score={score}")
    return "\n".join(lines)


@tool
def query_telemetry(asset_id: str, since_ts: Optional[str] = None, limit: int = 50) -> str:
    """Query recent telemetry (sensor data) for an asset."""
    db = _get_db()
    if not db:
        return "Database not available."
    try:
        rows = db.query_telemetry(asset_id=asset_id, since_ts=since_ts, limit=limit)
    except Exception as e:
        return f"Query error: {e}"
    if not rows:
        return f"No telemetry found for asset {asset_id}."
    lines = []
    for r in rows[:20]:
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
def query_rules(keywords: str) -> str:
    """Search diagnosis rules by symptom, signal, or keywords (e.g. vibration, bearing, clogging)."""
    rules_dir = _get_rules_dir()
    if not rules_dir.exists():
        return "No rules directory found."
    kw_lower = keywords.lower().strip()
    if not kw_lower:
        return "Please provide keywords."
    results = []
    for f in sorted(rules_dir.glob("*.md")):
        content = f.read_text(encoding="utf-8")
        if kw_lower in content.lower() or any(k in content.lower() for k in kw_lower.split()):
            results.append(f"--- {f.stem} ---\n{content}")
    if not results:
        return f"No rules matched: {keywords}."
    return "\n\n".join(results[:5])


# --- RAG / Vector Search Tools ---

@tool
def query_similar_diagnoses(query: str, limit: int = 5) -> str:
    """
    Search for similar past diagnoses using semantic search (RAG).
    Useful for finding historical cases with similar symptoms or root causes.
    
    Args:
        query: Natural language query describing symptoms, root cause, or issue (e.g., "bearing wear vibration high")
        limit: Maximum number of results to return (default: 5)
    
    Returns:
        JSON string with similar diagnoses, including diagnosis_id, similarity score, root_cause, and text preview.
    """
    if not _HAS_RAG:
        return "RAG not available. Install sqlite-vec and sentence-transformers."
    
    try:
        results = search_text_in_vector_db(
            query_text=query,
            filter_type="diagnosis",
            limit=limit,
        )
        
        if not results:
            return f"No similar diagnoses found for query: '{query}'"
        
        formatted = []
        for rowid, distance, metadata in results:
            similarity = 1.0 - distance  # Convert distance to similarity (0-1)
            formatted.append({
                "diagnosis_id": metadata.get("id"),
                "similarity": f"{similarity:.2%}",
                "similarity_score": round(similarity, 3),
                "root_cause": metadata.get("root_cause", "unknown"),
                "asset_id": metadata.get("asset_id", ""),
                "confidence": metadata.get("confidence"),
                "text_preview": metadata.get("text", "")[:200],
            })
        
        return json.dumps(formatted, indent=2)
    except Exception as e:
        return f"RAG search error: {e}"


@tool
def query_similar_alerts(query: str, limit: int = 5) -> str:
    """
    Search for similar past alerts using semantic search (RAG).
    Useful for identifying alert patterns or recurring issues.
    
    Args:
        query: Natural language query describing alert type or signal (e.g., "vibration sensor anomaly")
        limit: Maximum number of results to return (default: 5)
    
    Returns:
        JSON string with similar alerts, including alert_id, similarity score, signal, severity, and text preview.
    """
    if not _HAS_RAG:
        return "RAG not available. Install sqlite-vec and sentence-transformers."
    
    try:
        results = search_text_in_vector_db(
            query_text=query,
            filter_type="alert",
            limit=limit,
        )
        
        if not results:
            return f"No similar alerts found for query: '{query}'"
        
        formatted = []
        for rowid, distance, metadata in results:
            similarity = 1.0 - distance
            formatted.append({
                "alert_id": metadata.get("id"),
                "similarity": f"{similarity:.2%}",
                "similarity_score": round(similarity, 3),
                "signal": metadata.get("signal", ""),
                "severity": metadata.get("severity", ""),
                "asset_id": metadata.get("asset_id", ""),
                "text_preview": metadata.get("text", "")[:200],
            })
        
        return json.dumps(formatted, indent=2)
    except Exception as e:
        return f"RAG search error: {e}"


@tool
def query_similar_feedback(query: str, limit: int = 5) -> str:
    """
    Search for similar past feedback/reviews using semantic search (RAG).
    Useful for learning from human review decisions and notes.
    
    Args:
        query: Natural language query describing review decision or feedback (e.g., "approved bearing replacement")
        limit: Maximum number of results to return (default: 5)
    
    Returns:
        JSON string with similar feedback, including feedback_id, similarity score, review_decision, and notes preview.
    """
    if not _HAS_RAG:
        return "RAG not available. Install sqlite-vec and sentence-transformers."
    
    try:
        results = search_text_in_vector_db(
            query_text=query,
            filter_type="feedback",
            limit=limit,
        )
        
        if not results:
            return f"No similar feedback found for query: '{query}'"
        
        formatted = []
        for rowid, distance, metadata in results:
            similarity = 1.0 - distance
            formatted.append({
                "feedback_id": metadata.get("id"),
                "similarity": f"{similarity:.2%}",
                "similarity_score": round(similarity, 3),
                "review_decision": metadata.get("review_decision", ""),
                "asset_id": metadata.get("asset_id", ""),
                "text_preview": metadata.get("text", "")[:200],
            })
        
        return json.dumps(formatted, indent=2)
    except Exception as e:
        return f"RAG search error: {e}"


@tool
def query_similar_rules(query: str, limit: int = 5) -> str:
    """
    Search for relevant diagnosis rules using semantic search (RAG).
    More intelligent than keyword search - finds rules by meaning, not just exact keywords.
    
    Args:
        query: Natural language query describing symptoms or conditions (e.g., "bearing temperature vibration correlation")
        limit: Maximum number of results to return (default: 5)
    
    Returns:
        JSON string with similar rules, including rule_name, similarity score, and rule content preview.
    """
    if not _HAS_RAG:
        return "RAG not available. Install sqlite-vec and sentence-transformers."
    
    try:
        results = search_text_in_vector_db(
            query_text=query,
            filter_type="rule",
            limit=limit,
        )
        
        if not results:
            return f"No similar rules found for query: '{query}'. Try query_rules with keywords instead."
        
        formatted = []
        for rowid, distance, metadata in results:
            similarity = 1.0 - distance
            formatted.append({
                "rule_name": metadata.get("rule_name", ""),
                "similarity": f"{similarity:.2%}",
                "similarity_score": round(similarity, 3),
                "file_path": metadata.get("file_path", ""),
                "content_preview": metadata.get("text", "")[:300],
            })
        
        return json.dumps(formatted, indent=2)
    except Exception as e:
        return f"RAG search error: {e}"


@tool
def query_similar_chat(query: str, limit: int = 3) -> str:
    """
    Search for similar past chat conversations using semantic search (RAG).
    Useful for finding answers to similar questions from previous sessions.
    
    Args:
        query: Natural language query describing the question or topic (e.g., "how to diagnose bearing wear")
        limit: Maximum number of results to return (default: 3)
    
    Returns:
        JSON string with similar chat messages, including message_id, similarity score, and answer preview.
    """
    if not _HAS_RAG:
        return "RAG not available. Install sqlite-vec and sentence-transformers."
    
    try:
        results = search_text_in_vector_db(
            query_text=query,
            filter_type="chat",
            limit=limit,
        )
        
        if not results:
            return f"No similar chat history found for query: '{query}'"
        
        formatted = []
        for rowid, distance, metadata in results:
            similarity = 1.0 - distance
            formatted.append({
                "message_id": metadata.get("id"),
                "session_id": metadata.get("session_id"),
                "similarity": f"{similarity:.2%}",
                "similarity_score": round(similarity, 3),
                "answer_preview": metadata.get("text", "")[:300],
            })
        
        return json.dumps(formatted, indent=2)
    except Exception as e:
        return f"RAG search error: {e}"


def get_review_tools() -> List:
    """Return tools for the review agent."""
    tools = [
        query_review_requests,
        query_diagnosis,
        query_alerts,
        query_telemetry,
        query_rules,
    ]
    
    # Add RAG tools if available
    if _HAS_RAG:
        tools.extend([
            query_similar_diagnoses,
            query_similar_alerts,
            query_similar_feedback,
            query_similar_rules,
            query_similar_chat,
        ])
    
    return tools
