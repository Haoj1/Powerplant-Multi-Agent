"""ReAct diagnosis agent setup and inference."""

import json
import re
from datetime import datetime
from typing import Any, Dict, Optional

from shared_lib.config import get_settings
from shared_lib.models import DiagnosisReport, RootCause, Impact

from .prompts import DIAGNOSIS_SYSTEM_PROMPT, build_user_prompt
from .tools import get_diagnosis_tools


def _make_llm():
    """Create LLM instance. Prefer DeepSeek (OpenAI-compatible), fallback to OpenAI."""
    settings = get_settings()
    try:
        from langchain_openai import ChatOpenAI
        if settings.deepseek_api_key and settings.deepseek_base_url:
            return ChatOpenAI(
                model="deepseek-chat",
                api_key=settings.deepseek_api_key,
                base_url=settings.deepseek_base_url,
                temperature=0,
            )
        if settings.openai_api_key:
            return ChatOpenAI(
                model="gpt-4o-mini",
                api_key=settings.openai_api_key,
                temperature=0,
            )
    except ImportError:
        pass
    raise RuntimeError(
        "No LLM configured. Set DEEPSEEK_API_KEY and DEEPSEEK_BASE_URL, or OPENAI_API_KEY."
    )


def create_diagnosis_agent():
    """Create the ReAct agent with tools."""
    from langgraph.prebuilt import create_react_agent
    llm = _make_llm()
    tools = get_diagnosis_tools()
    return create_react_agent(llm, tools)


def _parse_final_answer(text: str) -> Optional[Dict[str, Any]]:
    """Extract JSON from agent output. Handles markdown code blocks."""
    text = text.strip()
    # Try ```json ... ``` blocks first
    for block in re.finditer(r'```(?:json)?\s*([\s\S]*?)```', text):
        try:
            return json.loads(block.group(1).strip())
        except json.JSONDecodeError:
            continue
    # Find brace-balanced JSON object containing "root_cause"
    start = text.find('{')
    while start >= 0:
        depth = 0
        for i, c in enumerate(text[start:], start):
            if c == '{':
                depth += 1
            elif c == '}':
                depth -= 1
                if depth == 0:
                    try:
                        obj = json.loads(text[start : i + 1])
                        if "root_cause" in obj:
                            return obj
                    except json.JSONDecodeError:
                        pass
                    break
        start = text.find('{', start + 1)
    return None


def _build_alert_summary(alert_payload: dict) -> str:
    """Build a short summary of the alert for the prompt."""
    ts = alert_payload.get("ts", "")
    asset_id = alert_payload.get("asset_id", "")
    severity = alert_payload.get("severity", "")
    alerts = alert_payload.get("alerts", [])
    lines = [f"asset_id={asset_id}, ts={ts}, severity={severity}"]
    for a in alerts:
        sig = a.get("signal", "")
        score = a.get("score")
        method = a.get("method", "")
        ev = a.get("evidence", {})
        lines.append(f"  - signal={sig}, score={score}, method={method}, evidence={ev}")
    return "\n".join(lines)


def run_diagnosis(alert_payload: dict) -> Optional[DiagnosisReport]:
    """
    Run the ReAct agent to diagnose the given alert.
    Returns DiagnosisReport or None on failure.
    """
    from langchain_core.messages import HumanMessage, SystemMessage
    agent = create_diagnosis_agent()
    alert_summary = _build_alert_summary(alert_payload)
    user_prompt = build_user_prompt(alert_summary)
    messages = [
        SystemMessage(content=DIAGNOSIS_SYSTEM_PROMPT),
        HumanMessage(content=user_prompt),
    ]
    config = {"recursion_limit": 15}
    result = agent.invoke({"messages": messages}, config)
    if not result or "messages" not in result:
        return None
    last_msg = result["messages"][-1]
    content = getattr(last_msg, "content", "") or ""
    parsed = _parse_final_answer(content)
    if not parsed:
        return None
    try:
        rc = parsed.get("root_cause", "unknown")
        root_cause = RootCause(rc) if rc in [e.value for e in RootCause] else RootCause.UNKNOWN
        impact_val = parsed.get("impact", "medium")
        impact = Impact(impact_val) if impact_val in [e.value for e in Impact] else Impact.MEDIUM
        ts = alert_payload.get("ts")
        if isinstance(ts, str):
            try:
                ts = datetime.fromisoformat(ts.replace("Z", "+00:00"))
            except Exception:
                ts = datetime.now()
        elif not isinstance(ts, datetime):
            ts = datetime.now()
        return DiagnosisReport(
            ts=ts,
            plant_id=alert_payload.get("plant_id", ""),
            asset_id=alert_payload.get("asset_id", ""),
            root_cause=root_cause,
            confidence=float(parsed.get("confidence", 0.5)),
            impact=impact,
            recommended_actions=parsed.get("recommended_actions") or [],
            evidence=[
                {"rule": e.get("rule", ""), "details": e.get("details", {})}
                for e in parsed.get("evidence", [])
            ],
        )
    except Exception:
        return None
