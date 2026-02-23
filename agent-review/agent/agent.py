"""ReAct review agent with streaming support."""

from datetime import datetime, timedelta

from shared_lib.config import get_settings

from .prompts import REVIEW_SYSTEM_PROMPT
from .tools import get_review_tools, _get_db, _get_rules_dir


def _make_llm():
    """Create LLM (DeepSeek or OpenAI)."""
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


def create_review_agent():
    """Create ReAct agent with review tools."""
    from langgraph.prebuilt import create_react_agent
    llm = _make_llm()
    tools = get_review_tools()
    return create_react_agent(llm, tools)


async def run_review_chat_stream(messages_input: list, session_id: int | None = None, system_prompt_override: str | None = None, recursion_limit: int = 15):
    """
    Run the review agent with streaming. Yields SSE-like dicts:
    - {"type": "step", "step": {"step_type": "thought"|"tool_call"|"tool_result", ...}}
    - {"type": "result", "answer": str, "session_id": int}
    - {"type": "error", "error": str}
    If system_prompt_override is set, use it instead of REVIEW_SYSTEM_PROMPT (e.g. for diagnosis assistant).
    """
    from langchain_core.messages import HumanMessage, SystemMessage
    try:
        agent = create_review_agent()
        msgs = []
        if not any(m.get("role") == "system" for m in messages_input if isinstance(m, dict)):
            prompt = (system_prompt_override or REVIEW_SYSTEM_PROMPT)
            msgs.append(SystemMessage(content=prompt))
        for m in messages_input:
            if isinstance(m, dict):
                r = m.get("role", "")
                c = m.get("content", "")
                if r == "user":
                    msgs.append(HumanMessage(content=c))
                elif r == "assistant":
                    from langchain_core.messages import AIMessage
                    msgs.append(AIMessage(content=c))
            else:
                msgs.append(m)

        config = {"recursion_limit": recursion_limit}
        steps = []
        step_order = 0
        answer = ""
        last_state = None

        async for chunk in agent.astream(
            {"messages": msgs},
            config=config,
            stream_mode="updates",
        ):
            for node_name, node_output in chunk.items():
                last_state = node_output
                if "messages" in node_output:
                    for msg in node_output["messages"]:
                        msg_type = type(msg).__name__
                        if "ToolMessage" in msg_type:
                            step_order += 1
                            content = getattr(msg, "content", "") or ""
                            step = {
                                "step_type": "tool_result",
                                "step_order": step_order,
                                "tool_name": None,
                                "content": content[:500] + "..." if len(content) > 500 else content,
                                "raw_result": content,
                            }
                            steps.append(step)
                            yield {"type": "step", "step": step}
                        elif "AIMessage" in msg_type:
                            content = getattr(msg, "content", "") or ""
                            tool_calls = getattr(msg, "tool_calls", []) or []
                            if tool_calls:
                                # Emit planning/reasoning as thought first (ReAct-style)
                                if content and content.strip():
                                    step_order += 1
                                    step = {
                                        "step_type": "thought",
                                        "step_order": step_order,
                                        "content": content.strip(),
                                    }
                                    steps.append(step)
                                    yield {"type": "step", "step": step}
                                for tc in tool_calls:
                                    step_order += 1
                                    name = tc.get("name", "")
                                    args = tc.get("args", {})
                                    step = {
                                        "step_type": "tool_call",
                                        "step_order": step_order,
                                        "tool_name": name,
                                        "tool_args": args,
                                        "content": f"Calling {name}",
                                    }
                                    steps.append(step)
                                    yield {"type": "step", "step": step}
                            else:
                                if content:
                                    step_order += 1
                                    step = {
                                        "step_type": "thought",
                                        "step_order": step_order,
                                        "content": content,
                                    }
                                    steps.append(step)
                                    yield {"type": "step", "step": step}
                                    answer = content

        if not answer and last_state and "messages" in last_state:
            for m in reversed(last_state["messages"]):
                if "AIMessage" in type(m).__name__ and not getattr(m, "tool_calls", None):
                    c = getattr(m, "content", "") or ""
                    if c:
                        answer = c
                        break

        yield {"type": "result", "answer": answer, "steps": steps, "session_id": session_id}
    except Exception as e:
        import traceback
        traceback.print_exc()
        yield {"type": "error", "error": str(e)}


def generate_diagnosis_one_shot(alert_id: int) -> str:
    """
    Generate diagnosis in one LLM call (no ReAct loop). Fetches alert, telemetry, rules
    from DB/files, then asks LLM to produce diagnosis. Reliable and does not get interrupted.
    """
    db = _get_db()
    if not db:
        return "Database not available."
    alert = db.get_alert_by_id(alert_id)
    if not alert:
        return f"Alert {alert_id} not found."
    asset_id = alert.get("asset_id") or ""
    alert_ts = alert.get("ts") or ""
    signal = alert.get("signal") or ""
    severity = alert.get("severity") or ""

    # Time window: 1 hour before/after alert
    since_ts = until_ts = None
    if alert_ts:
        try:
            if "T" in str(alert_ts):
                dt = datetime.fromisoformat(str(alert_ts).replace("Z", "+00:00"))
            else:
                dt = datetime.strptime(str(alert_ts)[:19], "%Y-%m-%d %H:%M:%S")
            since_dt = dt - timedelta(hours=1)
            until_dt = dt + timedelta(hours=1)
            since_ts = since_dt.strftime("%Y-%m-%dT%H:%M:%SZ")
            until_ts = until_dt.strftime("%Y-%m-%dT%H:%M:%SZ")
        except Exception:
            pass

    # Fetch telemetry
    telemetry_text = "No telemetry data."
    if asset_id:
        try:
            rows = db.query_telemetry(asset_id=asset_id, since_ts=since_ts, until_ts=until_ts, limit=50)
            if rows:
                lines = []
                for r in rows[:15]:
                    ts = r.get("ts", "")
                    p, f, t, bt, v = r.get("pressure_bar"), r.get("flow_m3h"), r.get("temp_c"), r.get("bearing_temp_c"), r.get("vibration_rms")
                    rpm, cur, valve = r.get("rpm"), r.get("motor_current_a"), r.get("valve_open_pct")
                    fault = r.get("fault", "")
                    lines.append(
                        f"{ts} | P={p:.2f if p is not None else 0} F={f:.2f if f is not None else 0} "
                        f"T={t:.2f if t is not None else 0} BT={bt:.2f if bt is not None else 0} "
                        f"Vib={v:.2f if v is not None else 0} RPM={rpm:.1f if rpm is not None else 0} "
                        f"I={cur:.2f if cur is not None else 0} Valve={valve:.1f if valve is not None else 0} fault={fault}"
                    )
                telemetry_text = "\n".join(lines) if lines else "No telemetry rows."
            else:
                telemetry_text = "No telemetry found for this time range."
        except Exception as e:
            telemetry_text = f"Telemetry query error: {e}"

    # Fetch rules
    rules_text = "No rules found."
    rules_dir = _get_rules_dir()
    if rules_dir.exists():
        kw = (signal or "pump fault").lower()
        results = []
        for f in sorted(rules_dir.glob("*.md")):
            try:
                content = f.read_text(encoding="utf-8")
                if kw in content.lower() or any(k in content.lower() for k in kw.split()):
                    results.append(f"--- {f.stem} ---\n{content}")
            except Exception:
                pass
        if results:
            rules_text = "\n\n".join(results[:3])

    prompt = f"""You are a diagnosis assistant for industrial pump monitoring. Based on the following data, produce a clear diagnosis.

**Alert:**
- id={alert_id} asset_id={asset_id} signal={signal} severity={severity} ts={alert_ts}

**Telemetry (sensor data around alert time):**
{telemetry_text}

**Relevant rules:**
{rules_text}

Provide a diagnosis with:
1. **Root cause** - What likely caused this alert
2. **Impact** - Potential consequences
3. **Recommended actions** - What the operator should do

Be concise. Answer in English unless the user's question was in another language."""

    try:
        llm = _make_llm()
        from langchain_core.messages import HumanMessage
        response = llm.invoke([HumanMessage(content=prompt)])
        content = getattr(response, "content", "") or ""
        return content.strip() or "No diagnosis generated."
    except Exception as e:
        import traceback
        traceback.print_exc()
        return f"LLM error: {e}"


def run_approve_assistant(review_id: int) -> dict:
    """
    Run approve assistant: fetch diagnosis, query similar SF cases, use LLM to analyze
    and suggest Case form. Returns { analysis, similar_cases, suggested_case }.
    """
    db = _get_db()
    if not db:
        return {"error": "Database not available", "similar_cases": [], "suggested_case": {}}
    requests = db.query_review_requests(status="pending", limit=1000)
    review_req = next((r for r in requests if r["id"] == review_id), None)
    if not review_req:
        return {"error": "Review request not found", "similar_cases": [], "suggested_case": {}}
    diagnosis_id = review_req.get("diagnosis_id")
    diagnosis = db.get_diagnosis_by_id(diagnosis_id) if diagnosis_id else None
    if not diagnosis:
        return {"error": "Diagnosis not found", "similar_cases": [], "suggested_case": {}}
    asset_id = review_req.get("asset_id") or ""
    plant_id = review_req.get("plant_id") or ""
    root_cause = diagnosis.get("root_cause") or ""

    similar_cases = []
    try:
        from shared_lib.integrations import get_ticket_connector
        from datetime import datetime, timedelta
        connector = get_ticket_connector()
        if connector and hasattr(connector, "query_cases"):
            since = (datetime.utcnow() - timedelta(days=90)).strftime("%Y-%m-%dT%H:%M:%SZ")
            kw = " ".join((root_cause or "pump fault").split()[:5])
            similar_cases = connector.query_cases(
                asset_id=asset_id or None,
                keywords=kw or None,
                created_since=since,
                limit=10,
            )
    except Exception as e:
        similar_cases = []

    cases_text = "\n".join(
        f"- {c.get('subject', '')} | {c.get('priority', '')} | {c.get('url', '')}"
        for c in similar_cases[:5]
    ) if similar_cases else "No similar cases found."

    prompt = f"""You are an approve assistant. A diagnosis is being approved and a Salesforce Case will be created.

**Diagnosis:**
- Asset: {asset_id} Plant: {plant_id}
- Root cause: {root_cause}
- Impact: {diagnosis.get('impact', '')}
- Recommended actions: {diagnosis.get('recommended_actions', [])}

**Recent similar Salesforce Cases:**
{cases_text}

Tasks:
1. Brief analysis (1-2 sentences): any similar cases to reference?
2. Suggest a Case form: subject (short, include asset), description (concise summary), priority (High/Medium/Low), status (New/Working/Escalated/Closed), origin (Web/Phone/Email/Internal), type (Problem/Question/Feature Request or empty), reason (Performance/Installation/Other or empty).

Return JSON only:
{{"analysis": "your brief analysis", "suggested_case": {{"subject": "...", "description": "...", "priority": "High", "status": "New", "origin": "Web", "type": "Problem", "reason": ""}}}}"""

    try:
        llm = _make_llm()
        from langchain_core.messages import HumanMessage
        response = llm.invoke([HumanMessage(content=prompt)])
        content = (getattr(response, "content", "") or "").strip()
        import json
        if "```" in content:
            for block in content.split("```"):
                block = block.strip()
                if block.startswith("json"):
                    block = block[4:].strip()
                try:
                    data = json.loads(block)
                    return {
                        "analysis": data.get("analysis", ""),
                        "similar_cases": similar_cases,
                        "suggested_case": data.get("suggested_case", {
                            "subject": f"[{asset_id}] {root_cause[:80]}" if asset_id else root_cause[:80],
                            "description": f"Asset: {asset_id}, Plant: {plant_id}. Root cause: {root_cause}",
                            "priority": "Medium",
                            "status": "New",
                            "origin": "Web",
                            "type": "",
                            "reason": "",
                        }),
                    }
                except json.JSONDecodeError:
                    pass
        try:
            data = json.loads(content)
            sug = data.get("suggested_case", {})
            sug.setdefault("status", "New")
            sug.setdefault("origin", "Web")
            sug.setdefault("type", "")
            sug.setdefault("reason", "")
            return {
                "analysis": data.get("analysis", ""),
                "similar_cases": similar_cases,
                "suggested_case": sug,
            }
        except json.JSONDecodeError:
            pass
        return {
            "analysis": content[:500] if content else "No analysis.",
            "similar_cases": similar_cases,
            "suggested_case": {
                "subject": f"[{asset_id}] {root_cause[:80]}" if asset_id else root_cause[:80],
                "description": f"Asset: {asset_id}, Plant: {plant_id}. Root cause: {root_cause}",
                "priority": "Medium",
                "status": "New",
                "origin": "Web",
                "type": "",
                "reason": "",
            },
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {
            "error": str(e),
            "analysis": "",
            "similar_cases": similar_cases,
            "suggested_case": {
                "subject": f"[{asset_id}] {root_cause[:80]}" if asset_id else root_cause[:80],
                "description": f"Asset: {asset_id}, Plant: {plant_id}. Root cause: {root_cause}",
                "priority": "Medium",
            },
        }
