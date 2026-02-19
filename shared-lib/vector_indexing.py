"""
Helper functions to index various data types into vector DB for RAG.
Used by agents to automatically index data when created.
"""

import json
from typing import Any, Dict, List, Optional

try:
    from .vector_db import add_text_to_vector_db
    _HAS_VECTOR_DB = True
except ImportError:
    _HAS_VECTOR_DB = False


def _safe_index(func):
    """Decorator to safely index data (failures don't break main flow)."""
    def wrapper(*args, **kwargs):
        if not _HAS_VECTOR_DB:
            return None
        try:
            return func(*args, **kwargs)
        except Exception as e:
            # Silently fail - vector indexing is optional
            print(f"[Vector Index] Warning: Failed to index: {e}")
            return None
    return wrapper


@_safe_index
def index_diagnosis(diagnosis_id: int, diagnosis_data: Dict[str, Any]) -> Optional[int]:
    """
    Index a diagnosis into vector DB.
    
    Args:
        diagnosis_id: Diagnosis ID
        diagnosis_data: Dict with keys: root_cause, confidence, impact, recommended_actions, evidence, asset_id, plant_id
    
    Returns:
        rowid in vector DB, or None if failed
    """
    root_cause = diagnosis_data.get("root_cause", "")
    confidence = diagnosis_data.get("confidence", 0.0)
    impact = diagnosis_data.get("impact", "")
    recommended_actions = diagnosis_data.get("recommended_actions", [])
    evidence = diagnosis_data.get("evidence", [])
    
    # Build text for embedding
    actions_str = ", ".join(recommended_actions) if isinstance(recommended_actions, list) else str(recommended_actions)
    evidence_str = json.dumps(evidence) if isinstance(evidence, (list, dict)) else str(evidence)
    
    text = f"""
    Root cause: {root_cause}
    Confidence: {confidence:.2f}
    Impact: {impact}
    Recommended actions: {actions_str}
    Evidence: {evidence_str}
    """
    
    return add_text_to_vector_db(
        text=text.strip(),
        doc_type="diagnosis",
        doc_id=diagnosis_id,
        extra_metadata={
            "asset_id": diagnosis_data.get("asset_id", ""),
            "plant_id": diagnosis_data.get("plant_id", ""),
            "confidence": confidence,
            "root_cause": root_cause,
        },
    )


@_safe_index
def index_alert(alert_id: int, alert_data: Dict[str, Any]) -> Optional[int]:
    """
    Index an alert into vector DB.
    
    Args:
        alert_id: Alert ID
        alert_data: Dict with keys: signal, severity, score, method, evidence, asset_id, plant_id
    
    Returns:
        rowid in vector DB, or None if failed
    """
    signal = alert_data.get("signal", "")
    severity = alert_data.get("severity", "")
    score = alert_data.get("score", 0.0)
    method = alert_data.get("method", "")
    evidence = alert_data.get("evidence", {})
    
    evidence_str = json.dumps(evidence) if isinstance(evidence, dict) else str(evidence)
    
    text = f"""
    Alert: {signal} exceeded threshold
    Severity: {severity}
    Score: {score:.2f}
    Method: {method}
    Evidence: {evidence_str}
    """
    
    return add_text_to_vector_db(
        text=text.strip(),
        doc_type="alert",
        doc_id=alert_id,
        extra_metadata={
            "asset_id": alert_data.get("asset_id", ""),
            "plant_id": alert_data.get("plant_id", ""),
            "severity": severity,
            "signal": signal,
            "score": score,
        },
    )


@_safe_index
def index_feedback(feedback_id: int, feedback_data: Dict[str, Any]) -> Optional[int]:
    """
    Index feedback into vector DB.
    
    Args:
        feedback_id: Feedback ID
        feedback_data: Dict with keys: review_decision, final_root_cause, notes, asset_id, plant_id, ticket_id
    
    Returns:
        rowid in vector DB, or None if failed
    """
    review_decision = feedback_data.get("review_decision", "")
    final_root_cause = feedback_data.get("final_root_cause", "")
    notes = feedback_data.get("notes", "")
    original_root_cause = feedback_data.get("original_root_cause", "")
    
    text = f"""
    Review decision: {review_decision}
    Final root cause: {final_root_cause}
    Original root cause: {original_root_cause}
    Notes: {notes}
    """
    
    return add_text_to_vector_db(
        text=text.strip(),
        doc_type="feedback",
        doc_id=feedback_id,
        extra_metadata={
            "asset_id": feedback_data.get("asset_id", ""),
            "plant_id": feedback_data.get("plant_id", ""),
            "review_decision": review_decision,
            "ticket_id": feedback_data.get("ticket_id", ""),
        },
    )


@_safe_index
def index_ticket(ticket_id: str, ticket_data: Dict[str, Any]) -> Optional[int]:
    """
    Index a ticket into vector DB.
    
    Args:
        ticket_id: Ticket ID (string, e.g., GitHub issue number or Salesforce Case ID)
        ticket_data: Dict with keys: title, body, status, asset_id, plant_id, diagnosis_id, id (DB id)
    
    Returns:
        rowid in vector DB, or None if failed
    """
    title = ticket_data.get("title", "")
    body = ticket_data.get("body", "")
    status = ticket_data.get("status", "")
    diagnosis_id = ticket_data.get("diagnosis_id")
    
    text = f"""
    Ticket: {title}
    Description: {body}
    Status: {status}
    Related diagnosis ID: {diagnosis_id}
    """
    
    # Use DB id if available, otherwise hash ticket_id
    doc_id = ticket_data.get("id") or hash(ticket_id) % (2**31)
    
    return add_text_to_vector_db(
        text=text.strip(),
        doc_type="ticket",
        doc_id=doc_id,
        extra_metadata={
            "asset_id": ticket_data.get("asset_id", ""),
            "plant_id": ticket_data.get("plant_id", ""),
            "ticket_id": ticket_id,
            "status": status,
            "diagnosis_id": diagnosis_id,
        },
    )


@_safe_index
def index_chat_message(message_id: int, message_data: Dict[str, Any]) -> Optional[int]:
    """
    Index a chat message into vector DB (only assistant messages with substantial content).
    
    Args:
        message_id: Message ID
        message_data: Dict with keys: role, content, session_id, tools_used (optional), context (optional)
    
    Returns:
        rowid in vector DB, or None if failed or skipped
    """
    role = message_data.get("role", "")
    content = message_data.get("content", "")
    
    # Only index assistant messages with substantial content
    if role != "assistant" or len(content) < 100:
        return None
    
    tools_used = message_data.get("tools_used", [])
    context = message_data.get("context", "")
    
    tools_str = ", ".join(tools_used) if isinstance(tools_used, list) else ""
    
    text = f"""
    Question context: {context}
    Answer: {content}
    Tools used: {tools_str}
    """
    
    return add_text_to_vector_db(
        text=text.strip(),
        doc_type="chat",
        doc_id=message_id,
        extra_metadata={
            "session_id": message_data.get("session_id"),
            "role": "assistant",
        },
    )


@_safe_index
def index_vision_analysis(analysis_id: int, analysis_data: Dict[str, Any]) -> Optional[int]:
    """
    Index vision analysis into vector DB.
    
    Args:
        analysis_id: Vision analysis ID
        analysis_data: Dict with keys: description, anomalies_detected, confidence, asset_id, plant_id
    
    Returns:
        rowid in vector DB, or None if failed
    """
    description = analysis_data.get("description", "")
    anomalies = analysis_data.get("anomalies_detected", [])
    confidence = analysis_data.get("confidence", 0.0)
    
    anomalies_str = ", ".join(anomalies) if isinstance(anomalies, list) else str(anomalies)
    
    text = f"""
    Vision description: {description}
    Anomalies detected: {anomalies_str}
    Confidence: {confidence:.2f}
    """
    
    return add_text_to_vector_db(
        text=text.strip(),
        doc_type="vision",
        doc_id=analysis_id,
        extra_metadata={
            "asset_id": analysis_data.get("asset_id", ""),
            "plant_id": analysis_data.get("plant_id", ""),
            "confidence": confidence,
        },
    )


@_safe_index
def index_rules(rules_dir: str = None) -> int:
    """
    Index all rule files into vector DB.
    
    Args:
        rules_dir: Path to rules directory (default: from settings)
    
    Returns:
        Number of rules indexed
    """
    from pathlib import Path
    from .config import get_settings
    
    if rules_dir is None:
        settings = get_settings()
        rules_path = Path(settings.diagnosis_rules_path)
        if not rules_path.is_absolute():
            project_root = Path(__file__).resolve().parent.parent
            rules_path = project_root / rules_path
        rules_dir = str(rules_path)
    
    rules_path = Path(rules_dir)
    if not rules_path.exists():
        return 0
    
    count = 0
    for rule_file in rules_path.glob("*.md"):
        try:
            content = rule_file.read_text(encoding="utf-8")
            rule_name = rule_file.stem
            
            # Use filename hash as doc_id
            doc_id = hash(rule_name) % (2**31)
            
            add_text_to_vector_db(
                text=content,
                doc_type="rule",
                doc_id=doc_id,
                extra_metadata={
                    "rule_name": rule_name,
                    "file_path": str(rule_file),
                },
            )
            count += 1
        except Exception as e:
            print(f"[Vector Index] Failed to index rule {rule_file}: {e}")
    
    return count
