"""ReAct review agent with streaming support."""

from shared_lib.config import get_settings

from .prompts import REVIEW_SYSTEM_PROMPT
from .tools import get_review_tools


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


async def run_review_chat_stream(messages_input: list, session_id: int | None = None):
    """
    Run the review agent with streaming. Yields SSE-like dicts:
    - {"type": "step", "step": {"step_type": "thought"|"tool_call"|"tool_result", ...}}
    - {"type": "result", "answer": str, "session_id": int}
    - {"type": "error", "error": str}
    """
    from langchain_core.messages import HumanMessage, SystemMessage
    try:
        agent = create_review_agent()
        msgs = []
        if not any(m.get("role") == "system" for m in messages_input if isinstance(m, dict)):
            msgs.append(SystemMessage(content=REVIEW_SYSTEM_PROMPT))
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

        config = {"recursion_limit": 15}
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
