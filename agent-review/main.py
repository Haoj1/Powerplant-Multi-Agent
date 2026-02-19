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
from fastapi import Body, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse


class ChatAskRequest(BaseModel):
    question: str
    session_id: Optional[int] = None
    conversation_history: list = []

from shared_lib.config import get_settings

try:
    from shared_lib import db as shared_db
except ImportError:
    shared_db = None

try:
    from shared_lib.vector_indexing import index_feedback, index_chat_message, index_vision_analysis
except ImportError:
    index_feedback = None
    index_chat_message = None
    index_vision_analysis = None

from agent.agent import run_review_chat_stream


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
async def get_review_requests(status: str = "pending", asset_id: Optional[str] = None, limit: int = 50):
    """List review requests (default: pending)."""
    if not shared_db:
        raise HTTPException(503, "Database not available")
    rows = shared_db.query_review_requests(status=status, limit=limit)
    if asset_id:
        rows = [r for r in rows if r.get("asset_id") == asset_id]
    return {"success": True, "data": rows}


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
async def get_alerts(asset_id: Optional[str] = None, limit: int = 50):
    """List alerts with linked diagnosis and ticket."""
    if not shared_db:
        raise HTTPException(503, "Database not available")
    rows = shared_db.query_alerts_with_diagnosis_and_ticket(asset_id=asset_id, limit=limit)
    return {"success": True, "data": rows}


@app.get("/api/telemetry")
async def get_telemetry(asset_id: str, since_ts: Optional[str] = None, limit: int = 100):
    """Get telemetry for an asset."""
    if not shared_db:
        raise HTTPException(503, "Database not available")
    rows = shared_db.query_telemetry(asset_id=asset_id, since_ts=since_ts, limit=limit)
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
        try:
            messages = [
                {"role": "user" if i % 2 == 0 else "assistant", "content": m.get("content", m) if isinstance(m, dict) else str(m)}
                for i, m in enumerate(history)
            ]
            messages.append({"role": "user", "content": question})
            async for event in run_review_chat_stream(messages, session_id_out):
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


# --- Approve / Reject ---

class ReviewActionBody(BaseModel):
    notes: str = ""
    create_salesforce_case: bool = False


@app.post("/api/review/{review_id}/approve")
async def approve_review(review_id: int, body: Optional[ReviewActionBody] = Body(None)):
    """Approve review request. Placeholder - Salesforce creation to be added."""
    if not shared_db:
        raise HTTPException(503, "Database not available")
    b = body or ReviewActionBody()
    
    # Get review request details
    review_req = None
    try:
        requests = shared_db.query_review_requests(status="pending", limit=1000)
        review_req = next((r for r in requests if r["id"] == review_id), None)
    except Exception:
        pass
    
    shared_db.update_review_request_status(review_id, "approved")
    
    # Index feedback if review request found
    if review_req and index_feedback:
        try:
            diagnosis_id = review_req.get("diagnosis_id")
            diagnosis = shared_db.get_diagnosis_by_id(diagnosis_id) if diagnosis_id else None
            
            # Create feedback entry (ticket_id placeholder - will be updated when ticket is created)
            from shared_lib.utils import get_current_timestamp
            feedback_id = hash(f"{review_id}_{get_current_timestamp()}") % (2**31)
            
            index_feedback(feedback_id, {
                "asset_id": review_req.get("asset_id", ""),
                "plant_id": review_req.get("plant_id", ""),
                "review_decision": "approved",
                "final_root_cause": diagnosis.get("root_cause") if diagnosis else "",
                "original_root_cause": diagnosis.get("root_cause") if diagnosis else "",
                "notes": b.notes,
                "ticket_id": "PENDING",  # Will be updated when ticket is created
            })
        except Exception:
            pass  # Fail silently
    
    return {"success": True, "message": "Approved", "review_id": review_id}


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
