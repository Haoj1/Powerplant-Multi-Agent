"""Agent Review (Agent D) - API for review queue, chat with ReAct, approve/reject."""

import json
import sys
from pathlib import Path

_project_root = Path(__file__).parent.parent
_agent_dir = Path(__file__).parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))
if str(_agent_dir) not in sys.path:
    sys.path.insert(0, str(_agent_dir))

try:
    from dotenv import load_dotenv
    if (_project_root / ".env").exists():
        load_dotenv(_project_root / ".env")
except Exception:
    pass

from datetime import datetime
from typing import Optional

from pydantic import BaseModel
from fastapi import Body, File, FastAPI, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse


class ChatAskRequest(BaseModel):
    question: str
    session_id: Optional[int] = None
    conversation_history: list = []
    alert_id: Optional[int] = None  # when set with mode=diagnosis_assistant, use diagnosis-assistant prompt
    mode: Optional[str] = None  # "diagnosis_assistant" for alert modal chat

from shared_lib.config import get_settings

try:
    from shared_lib import db as shared_db
except ImportError:
    shared_db = None

try:
    from shared_lib.vector_indexing import index_feedback, index_chat_message, index_vision_analysis, index_ticket
except ImportError:
    index_feedback = None
    index_chat_message = None
    index_vision_analysis = None
    index_ticket = None

try:
    from shared_lib.integrations import get_ticket_connector
except ImportError:
    get_ticket_connector = None

from agent.agent import run_review_chat_stream
from agent.prompts import build_diagnosis_assistant_prompt


app = FastAPI(
    title="Agent Review",
    description="Review queue, chat with ReAct, approve/reject diagnoses",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

settings = get_settings()


# --- Read API routes ---

@app.get("/api/review-requests")
async def get_review_requests(
    status: str = "pending",
    asset_id: Optional[str] = None,
    limit: int = 20,
    offset: int = 0,
):
    """List review requests with pagination. Use status='' for all statuses."""
    if not shared_db:
        raise HTTPException(503, "Database not available")
    status_filter = status if (status and status.strip()) else ""
    rows, total = shared_db.query_review_requests_paginated(
        status=status_filter, limit=limit, offset=offset, asset_id=asset_id
    )
    return {"success": True, "data": rows, "total": total}


@app.get("/api/diagnosis/{diagnosis_id}")
async def get_diagnosis(diagnosis_id: int):
    """Get diagnosis by id."""
    if not shared_db:
        raise HTTPException(503, "Database not available")
    d = shared_db.get_diagnosis_by_id(diagnosis_id)
    if not d:
        raise HTTPException(404, "Diagnosis not found")
    return {"success": True, "data": d}


@app.get("/api/alerts")
async def get_alerts(
    asset_id: Optional[str] = None,
    severity: Optional[str] = None,
    limit: int = 20,
    offset: int = 0,
):
    """List alerts with pagination. severity: warning | critical (optional)."""
    if not shared_db:
        raise HTTPException(503, "Database not available")
    rows, total = shared_db.query_alerts_with_diagnosis_and_ticket_paginated(
        asset_id=asset_id, severity=severity, limit=limit, offset=offset
    )
    return {"success": True, "data": rows, "total": total}


@app.get("/api/alerts/{alert_id}")
async def get_alert_detail(alert_id: int):
    """Get one alert and its linked diagnosis (if any) for the alert modal."""
    if not shared_db:
        raise HTTPException(503, "Database not available")
    alert = shared_db.get_alert_by_id(alert_id)
    if not alert:
        raise HTTPException(404, "Alert not found")
    diagnosis = shared_db.get_diagnosis_by_alert_id(alert_id)
    in_review_queue = False
    if diagnosis:
        rr = shared_db.get_review_request_by_diagnosis_id(diagnosis["id"], status="pending")
        in_review_queue = rr is not None
    return {"success": True, "alert": alert, "diagnosis": diagnosis, "in_review_queue": in_review_queue}


class CreateDiagnosisBody(BaseModel):
    root_cause: str
    confidence: float = 0.9
    impact: str = ""
    recommended_actions: Optional[list] = None
    evidence: Optional[list] = None


@app.post("/api/alerts/{alert_id}/generate-diagnosis")
async def generate_diagnosis_for_alert(alert_id: int):
    """Generate diagnosis in one shot (no ReAct loop). Returns diagnosis text. Does not save to DB."""
    if not shared_db:
        raise HTTPException(503, "Database not available")
    from agent.agent import generate_diagnosis_one_shot
    text = generate_diagnosis_one_shot(alert_id)
    return {"success": True, "diagnosis_text": text}


@app.post("/api/alerts/{alert_id}/diagnosis")
async def create_diagnosis_for_alert(alert_id: int, body: CreateDiagnosisBody):
    """Create a diagnosis for an alert (e.g. from the alert modal after agent generated one)."""
    if not shared_db:
        raise HTTPException(503, "Database not available")
    alert = shared_db.get_alert_by_id(alert_id)
    if not alert:
        raise HTTPException(404, "Alert not found")
    ts = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
    diag_id = shared_db.insert_diagnosis(
        ts=ts,
        plant_id=alert.get("plant_id") or "",
        asset_id=alert.get("asset_id") or "",
        root_cause=body.root_cause,
        confidence=body.confidence,
        impact=body.impact or "",
        recommended_actions=body.recommended_actions,
        evidence=body.evidence,
        alert_id=alert_id,
    )
    return {"success": True, "diagnosis_id": diag_id}


@app.post("/api/diagnosis/{diagnosis_id}/add-to-review")
async def add_diagnosis_to_review_queue(diagnosis_id: int):
    """Add a diagnosis to the Review Queue (create review_request). Idempotent: if already in queue, returns existing."""
    if not shared_db:
        raise HTTPException(503, "Database not available")
    existing = shared_db.get_review_request_by_diagnosis_id(diagnosis_id, status="pending")
    if existing:
        return {"success": True, "review_id": existing["id"], "already_in_queue": True}
    diagnosis = shared_db.get_diagnosis_by_id(diagnosis_id)
    if not diagnosis:
        raise HTTPException(404, "Diagnosis not found")
    ts = diagnosis.get("ts") or datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
    review_id = shared_db.insert_review_request(
        diagnosis_id=diagnosis_id,
        plant_id=diagnosis.get("plant_id") or "",
        asset_id=diagnosis.get("asset_id") or "",
        ts=ts,
        status="pending",
    )
    return {"success": True, "review_id": review_id, "already_in_queue": False}


@app.get("/api/telemetry")
async def get_telemetry(
    asset_id: str,
    since_ts: Optional[str] = None,
    until_ts: Optional[str] = None,
    limit: int = 100,
):
    """Get telemetry for an asset, optionally in time range [since_ts, until_ts]."""
    if not shared_db:
        raise HTTPException(503, "Database not available")
    rows = shared_db.query_telemetry(
        asset_id=asset_id, since_ts=since_ts, until_ts=until_ts, limit=limit
    )
    return {"success": True, "data": rows}


# --- Chat API ---

@app.get("/api/chat/sessions")
async def list_chat_sessions(limit: int = 20):
    """List chat sessions."""
    if not shared_db:
        raise HTTPException(503, "Database not available")
    rows = shared_db.list_chat_sessions(limit=limit)
    return {"success": True, "sessions": rows}


@app.get("/api/chat/sessions/{session_id}")
async def get_chat_session(session_id: int):
    """Get session with messages and steps."""
    if not shared_db:
        raise HTTPException(503, "Database not available")
    session = shared_db.get_chat_session_with_messages(session_id)
    if not session:
        raise HTTPException(404, "Session not found")
    return {"success": True, "conversation_history": session.get("messages", []), "session": session}


@app.post("/api/chat/sessions/{session_id}/delete")
async def delete_chat_session(session_id: int):
    """Delete a chat session and all its messages."""
    if not shared_db:
        raise HTTPException(503, "Database not available")
    deleted = shared_db.delete_chat_session(session_id)
    if not deleted:
        raise HTTPException(404, "Session not found")
    return {"success": True}


@app.post("/api/chat/ask")
async def chat_ask(request: ChatAskRequest):
    """
    Chat with ReAct agent. Returns SSE stream: data: {type, step?|answer?|error?}
    """
    question = request.question.strip()
    if not question:
        raise HTTPException(400, "question is required")
    session_id = request.session_id
    history = request.conversation_history or []

    async def generate():
        session_id_out = session_id
        if not shared_db:
            yield f"data: {json.dumps({'type': 'error', 'error': 'Database not available'})}\n\n"
            return
        if session_id_out is None:
            session_id_out = shared_db.insert_chat_session(preview=question[:200])
        shared_db.insert_chat_message(session_id_out, "user", question)
        msg_id = shared_db.insert_chat_message(session_id_out, "assistant", "")
        shared_db.update_chat_session(session_id_out, preview=question[:200])
        step_order = 0
        system_prompt_override = None
        if request.mode == "diagnosis_assistant" and request.alert_id and shared_db:
            alert = shared_db.get_alert_by_id(request.alert_id)
            if alert:
                # Normalize for prompt: get_alert_by_id returns "id", list returns "alert_id"
                if "alert_id" not in alert:
                    alert["alert_id"] = alert.get("id")
                system_prompt_override = build_diagnosis_assistant_prompt(alert)
        try:
            messages = [
                {"role": "user" if i % 2 == 0 else "assistant", "content": m.get("content", m) if isinstance(m, dict) else str(m)}
                for i, m in enumerate(history)
            ]
            messages.append({"role": "user", "content": question})
            recursion_limit = 25 if request.mode == "diagnosis_assistant" else 15
            async for event in run_review_chat_stream(messages, session_id_out, system_prompt_override=system_prompt_override, recursion_limit=recursion_limit):
                if event.get("type") == "step":
                    step = event.get("step", {})
                    step_order += 1
                    shared_db.insert_chat_step(
                        msg_id,
                        step.get("step_type", "thought"),
                        step.get("step_order", step_order),
                        step.get("tool_name"),
                        json.dumps(step.get("tool_args")) if step.get("tool_args") else None,
                        step.get("content"),
                        step.get("raw_result"),
                    )
                    yield f"data: {json.dumps({'type': 'step', 'step': step}, default=str)}\n\n"
                elif event.get("type") == "result":
                    answer = event.get("answer", "")
                    shared_db.update_chat_message_content(msg_id, answer)
                    shared_db.update_chat_session(session_id_out, preview=question[:200])
                    # Index chat message to vector DB for RAG
                    if index_chat_message:
                        try:
                            # Get tools used from steps
                            tools_used = []
                            if shared_db:
                                import sqlite3
                                from shared_lib.config import get_settings
                                db_path = get_settings().sqlite_path
                                if not Path(db_path).is_absolute():
                                    db_path = _project_root / db_path
                                conn = sqlite3.connect(str(db_path))
                                try:
                                    steps = conn.execute(
                                        "SELECT tool_name FROM chat_steps WHERE message_id = ? AND tool_name IS NOT NULL",
                                        (msg_id,)
                                    ).fetchall()
                                    tools_used = [s[0] for s in steps if s[0]]
                                finally:
                                    conn.close()
                            
                            index_chat_message(msg_id, {
                                "role": "assistant",
                                "content": answer,
                                "session_id": session_id_out,
                                "tools_used": tools_used,
                                "context": question,
                            })
                        except Exception:
                            pass  # Fail silently
                    yield f"data: {json.dumps({'type': 'result', 'success': True, 'answer': answer, 'session_id': session_id_out}, default=str)}\n\n"
                elif event.get("type") == "error":
                    yield f"data: {json.dumps({'type': 'error', 'error': event.get('error', '')})}\n\n"
        except Exception as e:
            import traceback
            traceback.print_exc()
            yield f"data: {json.dumps({'type': 'error', 'error': str(e)})}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# --- Troubleshooting Rules (Scenario Management) ---

class CreateRuleFromTextBody(BaseModel):
    text: str


@app.get("/api/rules")
async def get_rules():
    """List all troubleshooting rules (used by Agent B for diagnosis)."""
    try:
        from rules_service import list_rules
        rules = list_rules()
        return {"success": True, "rules": rules}
    except Exception as e:
        raise HTTPException(500, str(e))


@app.get("/api/rules/{name}")
async def get_rule_detail(name: str):
    """Get full content of a troubleshooting rule by name."""
    try:
        from rules_service import get_rule_content
        content = get_rule_content(name)
        if content is None:
            raise HTTPException(404, f"Rule '{name}' not found")
        return {"success": True, "name": name, "content": content}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, str(e))


@app.post("/api/rules/create-from-text")
async def create_rule_from_text(body: CreateRuleFromTextBody):
    """Parse natural language into a troubleshooting rule and save it."""
    if not (body.text or "").strip():
        raise HTTPException(400, "text is required")
    try:
        from rules_service import parse_text_to_rule, save_rule
        rule = parse_text_to_rule(body.text.strip())
        filename = save_rule(rule)
        return {"success": True, "filename": filename, "rule": rule}
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(500, str(e))


@app.post("/api/rules/create-from-flowchart")
async def create_rule_from_flowchart(file: UploadFile = File(...)):
    """Parse flowchart image into a troubleshooting rule and save it."""
    if not file.filename or not file.filename.lower().endswith((".png", ".jpg", ".jpeg", ".webp")):
        raise HTTPException(400, "Please upload a PNG, JPG, or WebP image")
    import tempfile
    import os
    suffix = Path(file.filename).suffix or ".png"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name
    try:
        from rules_service import parse_flowchart_to_rule, save_rule
        rule = parse_flowchart_to_rule(tmp_path)
        filename = save_rule(rule)
        return {"success": True, "filename": filename, "rule": rule}
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(500, str(e))
    finally:
        try:
            os.unlink(tmp_path)
        except Exception:
            pass


@app.delete("/api/rules/{name}")
async def delete_rule(name: str):
    """Delete a troubleshooting rule by name."""
    try:
        from rules_service import delete_rule as do_delete
        if do_delete(name):
            return {"success": True}
        raise HTTPException(404, f"Rule '{name}' not found")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, str(e))


# --- Approve / Reject ---

class ReviewActionBody(BaseModel):
    notes: str = ""
    create_salesforce_case: bool = False


class ApproveWithCaseBody(BaseModel):
    notes: str = ""
    case: Optional[dict] = None  # { subject, description, priority }


# Fallback picklist values when Salesforce is not configured or describe fails
DEFAULT_CASE_PICKLISTS = {
    "status": ["New", "Working", "Escalated", "Closed"],
    "priority": ["High", "Medium", "Low"],
    "origin": ["Web", "Phone", "Email", "Internal"],
    "type": ["Problem", "Question", "Feature Request"],
    "reason": ["Performance", "Installation", "Other"],
}


@app.get("/api/salesforce/case-picklists")
async def get_case_picklists():
    """Get Case picklist values from Salesforce (Status, Priority, Origin, Type, Reason)."""
    if not get_ticket_connector:
        return {"success": True, "picklists": DEFAULT_CASE_PICKLISTS}
    connector = get_ticket_connector()
    if not connector or not hasattr(connector, "get_case_picklists"):
        return {"success": True, "picklists": DEFAULT_CASE_PICKLISTS}
    try:
        picklists = connector.get_case_picklists()
        # Merge with defaults so we always have options (SF may omit some fields)
        merged = {}
        for key, default_vals in DEFAULT_CASE_PICKLISTS.items():
            sf_vals = picklists.get(key) or []
            merged[key] = sf_vals if sf_vals else default_vals
        return {"success": True, "picklists": merged}
    except Exception:
        return {"success": True, "picklists": DEFAULT_CASE_PICKLISTS}


@app.get("/api/review/{review_id}/approve-assistant")
async def get_approve_assistant(review_id: int):
    """Run approve assistant: analyze diagnosis, fetch similar SF cases, suggest Case form."""
    from agent.agent import run_approve_assistant
    result = run_approve_assistant(review_id)
    # Include picklists so frontend gets them in one request
    picklists = dict(DEFAULT_CASE_PICKLISTS)
    if get_ticket_connector:
        connector = get_ticket_connector()
        if connector and hasattr(connector, "get_case_picklists"):
            try:
                pl = connector.get_case_picklists()
                for key, default_vals in DEFAULT_CASE_PICKLISTS.items():
                    sf_vals = pl.get(key) or []
                    picklists[key] = sf_vals if sf_vals else default_vals
            except Exception:
                pass
    result["picklists"] = picklists
    return {"success": True, **result}


@app.post("/api/review/{review_id}/approve-with-case")
async def approve_with_case(review_id: int, body: ApproveWithCaseBody):
    """Approve review and create Salesforce Case with provided form fields."""
    if not shared_db:
        raise HTTPException(503, "Database not available")
    b = body or ApproveWithCaseBody()
    review_req = None
    try:
        requests = shared_db.query_review_requests(status="pending", limit=1000)
        review_req = next((r for r in requests if r["id"] == review_id), None)
    except Exception:
        pass
    if not review_req:
        raise HTTPException(404, "Review request not found")
    shared_db.update_review_request_status(review_id, "approved")
    diagnosis_id = review_req.get("diagnosis_id")
    diagnosis = shared_db.get_diagnosis_by_id(diagnosis_id) if diagnosis_id else None
    asset_id = review_req.get("asset_id") or ""
    plant_id = review_req.get("plant_id") or ""
    ticket_id_used = "PENDING"
    case_data = b.case or {}
    subject = case_data.get("subject") or f"Diagnosis approval"
    description = case_data.get("description") or ""
    priority = case_data.get("priority") or ""
    status = case_data.get("status") or "New"
    origin = case_data.get("origin") or "Web"
    case_type = case_data.get("type") or ""
    reason = case_data.get("reason") or ""
    if get_ticket_connector and (subject or description):
        connector = get_ticket_connector()
        if connector and diagnosis:
            try:
                result = connector.create_case(
                    subject=subject,
                    description=description or f"Asset: {asset_id}, Plant: {plant_id}. Root cause: {diagnosis.get('root_cause', '')}",
                    asset_id=asset_id,
                    plant_id=plant_id,
                    diagnosis_id=diagnosis_id,
                    root_cause=diagnosis.get("root_cause", ""),
                    priority=priority,
                    status=status,
                    origin=origin,
                    type=case_type,
                    reason=reason,
                )
                ticket_id_used = result.ticket_id
                from shared_lib.utils import get_current_timestamp
                ts_str = get_current_timestamp().isoformat()
                shared_db.insert_ticket(
                    ts=ts_str,
                    plant_id=plant_id,
                    asset_id=asset_id,
                    ticket_id=result.ticket_id,
                    title=result.title or subject,
                    body=result.body or description,
                    status="open",
                    diagnosis_id=diagnosis_id,
                    url=result.url,
                )
                if index_ticket:
                    try:
                        index_ticket(result.ticket_id, {
                            "title": result.title or subject,
                            "body": result.body or description,
                            "status": "open",
                            "asset_id": asset_id,
                            "plant_id": plant_id,
                            "diagnosis_id": diagnosis_id,
                        })
                    except Exception:
                        pass
            except Exception as e:
                raise HTTPException(500, f"Salesforce create failed: {e}")
    if index_feedback and review_req:
        try:
            from shared_lib.utils import get_current_timestamp
            feedback_id = hash(f"{review_id}_{get_current_timestamp()}") % (2**31)
            index_feedback(feedback_id, {
                "review_id": review_id,
                "diagnosis_id": diagnosis_id,
                "asset_id": asset_id,
                "plant_id": plant_id,
                "review_decision": "approved",
                "notes": b.notes,
                "ticket_id": ticket_id_used,
            })
        except Exception:
            pass
    return {"success": True, "message": "Approved", "review_id": review_id, "ticket_id": ticket_id_used}


@app.post("/api/review/{review_id}/approve")
async def approve_review(review_id: int, body: Optional[ReviewActionBody] = Body(None)):
    """Approve review request. Optionally create Salesforce Case when create_salesforce_case=True."""
    if not shared_db:
        raise HTTPException(503, "Database not available")
    b = body or ReviewActionBody()

    from shared_lib.utils import get_current_timestamp
    review_req = None
    try:
        requests = shared_db.query_review_requests(status="pending", limit=1000)
        review_req = next((r for r in requests if r["id"] == review_id), None)
    except Exception:
        pass

    shared_db.update_review_request_status(review_id, "approved")

    ticket_id_used = "PENDING"
    if review_req:
        diagnosis_id = review_req.get("diagnosis_id")
        diagnosis = shared_db.get_diagnosis_by_id(diagnosis_id) if diagnosis_id else None
        asset_id = review_req.get("asset_id", "")
        plant_id = review_req.get("plant_id", "")

        if b.create_salesforce_case and get_ticket_connector:
            connector = get_ticket_connector()
            if connector and diagnosis:
                try:
                    subject = f"Diagnosis approval: {diagnosis.get('root_cause', 'unknown')}"
                    description = f"Asset: {asset_id}, Plant: {plant_id}. Root cause: {diagnosis.get('root_cause', '')}. Notes: {b.notes}"
                    result = connector.create_case(
                        subject=subject,
                        description=description,
                        asset_id=asset_id,
                        plant_id=plant_id,
                        diagnosis_id=diagnosis_id,
                        root_cause=diagnosis.get("root_cause", ""),
                    )
                    ticket_id_used = result.ticket_id
                    ts_str = get_current_timestamp().isoformat()
                    shared_db.insert_ticket(
                        ts=ts_str,
                        plant_id=plant_id,
                        asset_id=asset_id,
                        ticket_id=result.ticket_id,
                        title=result.title or subject,
                        body=result.body or description,
                        status="open",
                        diagnosis_id=diagnosis_id,
                        url=result.url,
                    )
                    if index_ticket:
                        try:
                            index_ticket(result.ticket_id, {
                                "title": result.title or subject,
                                "body": result.body or description,
                                "status": "open",
                                "asset_id": asset_id,
                                "plant_id": plant_id,
                                "diagnosis_id": diagnosis_id,
                            })
                        except Exception:
                            pass
                except Exception as e:
                    ticket_id_used = "PENDING"

        if index_feedback:
            try:
                feedback_id = hash(f"{review_id}_{get_current_timestamp()}") % (2**31)
                index_feedback(feedback_id, {
                    "asset_id": asset_id,
                    "plant_id": plant_id,
                    "review_decision": "approved",
                    "final_root_cause": diagnosis.get("root_cause", "") if diagnosis else "",
                    "original_root_cause": diagnosis.get("root_cause", "") if diagnosis else "",
                    "notes": b.notes,
                    "ticket_id": ticket_id_used,
                })
            except Exception:
                pass

    return {"success": True, "message": "Approved", "review_id": review_id, "ticket_id": ticket_id_used}


class RejectBody(BaseModel):
    notes: str = ""


@app.post("/api/review/{review_id}/reject")
async def reject_review(review_id: int, body: Optional[RejectBody] = Body(None)):
    """Reject review request."""
    if not shared_db:
        raise HTTPException(503, "Database not available")
    
    # Get review request details
    review_req = None
    try:
        requests = shared_db.query_review_requests(status="pending", limit=1000)
        review_req = next((r for r in requests if r["id"] == review_id), None)
    except Exception:
        pass
    
    b = body or RejectBody()
    shared_db.update_review_request_status(review_id, "rejected")
    
    # Index feedback
    if review_req and index_feedback:
        try:
            diagnosis_id = review_req.get("diagnosis_id")
            diagnosis = shared_db.get_diagnosis_by_id(diagnosis_id) if diagnosis_id else None
            
            from shared_lib.utils import get_current_timestamp
            feedback_id = hash(f"{review_id}_{get_current_timestamp()}") % (2**31)
            
            index_feedback(feedback_id, {
                "asset_id": review_req.get("asset_id", ""),
                "plant_id": review_req.get("plant_id", ""),
                "review_decision": "rejected",
                "final_root_cause": "",
                "original_root_cause": diagnosis.get("root_cause") if diagnosis else "",
                "notes": b.notes,
                "ticket_id": "REJECTED",
            })
        except Exception:
            pass  # Fail silently
    
    return {"success": True, "message": "Rejected", "review_id": review_id}


# --- Health ---

@app.get("/health")
async def health():
    return {"status": "healthy", "service": "agent-review"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8005)
