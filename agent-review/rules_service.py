"""
Rules service: parse natural language or flowchart to troubleshooting rules, save to rules/*.md.
Used by Agent B (diagnosis) via query_rules.
"""

import json
import re
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional

from shared_lib.config import get_settings


def _get_rules_dir() -> Path:
    settings = get_settings()
    rules_path = Path(settings.diagnosis_rules_path)
    if not rules_path.is_absolute():
        project_root = Path(__file__).resolve().parent.parent
        rules_path = project_root / rules_path
    rules_path.mkdir(parents=True, exist_ok=True)
    return rules_path


def _make_llm():
    """Create LLM for text parsing."""
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
    raise RuntimeError("No LLM configured. Set DEEPSEEK_API_KEY or OPENAI_API_KEY.")


TEXT_TO_RULE_PROMPT = """You are a troubleshooting rule extractor for industrial pump monitoring.

The user will provide a natural language description of a fault scenario and how to troubleshoot it.

Extract and return JSON only (no markdown, no explanation):
{
  "root_cause": "short_id",
  "symptoms": ["symptom 1", "symptom 2"],
  "related_signals": "comma_separated_signal_names",
  "recommended_actions": ["action 1", "action 2"],
  "impact": "brief impact description"
}

Rules:
- root_cause: use snake_case identifier (e.g. bearing_wear, clogging, valve_stuck, sensor_drift)
- symptoms: list of observable symptoms (e.g. "Elevated vibration_rms", "Reduced flow_m3h")
- related_signals: signal names like vibration_rms, bearing_temp_c, flow_m3h, pressure_bar, motor_current_a, rpm, valve_open_pct, temp_c
- recommended_actions: actionable steps for the operator
- impact: severity (e.g. "High - can lead to failure if unaddressed")

Return ONLY valid JSON, no other text."""

FLOWCHART_TO_RULE_PROMPT = """This image is a troubleshooting flowchart for industrial pump/equipment diagnosis.

Extract the decision logic and convert it into a single troubleshooting rule. Identify:
1. The main fault/root cause (use snake_case: bearing_wear, clogging, valve_stuck, etc.)
2. Symptoms or conditions that lead to this diagnosis
3. Related sensor/signal names (vibration_rms, bearing_temp_c, flow_m3h, pressure_bar, motor_current_a, rpm, valve_open_pct, temp_c)
4. Recommended actions for the operator
5. Impact/severity

Return JSON only (no markdown, no explanation):
{
  "root_cause": "short_id",
  "symptoms": ["symptom 1", "symptom 2"],
  "related_signals": "comma_separated_signal_names",
  "recommended_actions": ["action 1", "action 2"],
  "impact": "brief impact description"
}

If the flowchart has multiple branches leading to different root causes, pick the primary one or combine into one rule. Return ONLY valid JSON."""


def _parse_llm_json(content: str) -> Optional[Dict[str, Any]]:
    """Extract JSON from LLM/VLM response (may be wrapped in ```json ... ```)."""
    content = (content or "").strip()
    # Try raw parse first
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        pass
    # Try code block
    for block in re.split(r"```\w*\s*", content):
        block = block.strip()
        if block.startswith("{"):
            try:
                return json.loads(block)
            except json.JSONDecodeError:
                pass
    # Try to find JSON object
    match = re.search(r"\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}", content, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            pass
    return None


def parse_text_to_rule(text: str) -> Dict[str, Any]:
    """
    Parse natural language description into structured rule.
    Returns dict with root_cause, symptoms, related_signals, recommended_actions, impact.
    Raises ValueError on parse failure.
    """
    if not (text or "").strip():
        raise ValueError("Text cannot be empty")
    llm = _make_llm()
    from langchain_core.messages import HumanMessage
    response = llm.invoke([HumanMessage(content=f"{TEXT_TO_RULE_PROMPT}\n\nUser input:\n{text.strip()}")])
    content = getattr(response, "content", "") or ""
    data = _parse_llm_json(content)
    if not data:
        raise ValueError(f"Could not parse rule from LLM response: {content[:200]}...")
    return _normalize_rule(data)


def parse_flowchart_to_rule(image_path: str) -> Dict[str, Any]:
    """
    Parse flowchart image into structured rule using VLM.
    image_path: path to PNG/JPEG file.
    Returns dict with root_cause, symptoms, related_signals, recommended_actions, impact.
    Raises ValueError on parse failure.
    """
    from shared_lib.vision import analyze_image
    result = analyze_image(image_path=image_path, question=FLOWCHART_TO_RULE_PROMPT)
    if not result or "not found" in result.lower() or "error" in result.lower():
        raise ValueError(result or "VLM analysis failed")
    data = _parse_llm_json(result)
    if not data:
        raise ValueError(f"Could not parse rule from VLM response: {result[:200]}...")
    return _normalize_rule(data)


def _normalize_rule(data: Dict[str, Any]) -> Dict[str, Any]:
    """Ensure rule has required fields with defaults."""
    root_cause = str(data.get("root_cause") or "unknown").strip().lower().replace(" ", "_")
    symptoms = data.get("symptoms")
    if isinstance(symptoms, str):
        symptoms = [s.strip() for s in symptoms.split(",") if s.strip()]
    symptoms = list(symptoms) if symptoms else ["See rule description"]
    related = data.get("related_signals")
    if isinstance(related, list):
        related = ", ".join(str(s) for s in related)
    related = str(related or "").strip() or "vibration_rms, bearing_temp_c, flow_m3h, pressure_bar"
    actions = data.get("recommended_actions")
    if isinstance(actions, str):
        actions = [a.strip() for a in actions.split(",") if a.strip()]
    actions = list(actions) if actions else ["Inspect equipment", "Review telemetry"]
    impact = str(data.get("impact") or "Medium - requires investigation").strip()
    return {
        "root_cause": root_cause,
        "symptoms": symptoms,
        "related_signals": related,
        "recommended_actions": actions,
        "impact": impact,
    }


def rule_to_markdown(rule: Dict[str, Any], title: Optional[str] = None) -> str:
    """Convert rule dict to markdown string matching agent-diagnosis/rules/*.md format."""
    title = title or rule.get("root_cause", "rule").replace("_", " ").title()
    lines = [
        f"# {title}",
        "",
        "## Root Cause",
        rule.get("root_cause", "unknown"),
        "",
        "## Symptoms",
    ]
    for s in rule.get("symptoms", []):
        lines.append(f"- {s}")
    lines.extend([
        "",
        "## Related Signals",
        rule.get("related_signals", ""),
        "",
        "## Recommended Actions",
    ])
    for a in rule.get("recommended_actions", []):
        lines.append(f"- {a}")
    lines.extend([
        "",
        "## Impact",
        rule.get("impact", ""),
        "",
    ])
    return "\n".join(lines)


def save_rule(rule: Dict[str, Any], name: Optional[str] = None) -> str:
    """
    Save rule to rules/*.md. Returns the filename (without path).
    name: optional filename stem (e.g. "bearing_wear"). If not provided, uses root_cause.
    """
    stem = (name or rule.get("root_cause", "rule")).strip().lower().replace(" ", "_")
    stem = re.sub(r"[^\w\-]", "_", stem) or "rule"
    rules_dir = _get_rules_dir()
    path = rules_dir / f"{stem}.md"
    # Avoid overwriting: if exists, append _1, _2, etc.
    counter = 0
    while path.exists():
        counter += 1
        path = rules_dir / f"{stem}_{counter}.md"
    content = rule_to_markdown(rule, title=stem.replace("_", " ").title())
    path.write_text(content, encoding="utf-8")
    return path.name


def list_rules() -> List[Dict[str, Any]]:
    """List all rules (markdown files) in the rules directory."""
    rules_dir = _get_rules_dir()
    out = []
    for f in sorted(rules_dir.glob("*.md")):
        try:
            content = f.read_text(encoding="utf-8")
            # Extract title (first # line) and root_cause
            title = f.stem.replace("_", " ").title()
            root_cause = ""
            for line in content.split("\n"):
                if line.strip().startswith("## Root Cause"):
                    idx = content.find("\n", content.find(line)) + 1
                    next_line = content[idx:content.find("\n", idx) if content.find("\n", idx) > 0 else len(content)]
                    root_cause = next_line.strip()
                    break
            out.append({
                "name": f.stem,
                "filename": f.name,
                "title": title,
                "root_cause": root_cause or f.stem,
            })
        except Exception:
            out.append({"name": f.stem, "filename": f.name, "title": f.stem, "root_cause": f.stem})
    return out


def get_rule_content(name: str) -> Optional[str]:
    """Get full markdown content of a rule by name (filename stem). Returns None if not found."""
    rules_dir = _get_rules_dir()
    path = rules_dir / f"{name}.md"
    if not path.exists():
        return None
    return path.read_text(encoding="utf-8")


def delete_rule(name: str) -> bool:
    """Delete a rule by name (filename stem). Returns True if deleted."""
    rules_dir = _get_rules_dir()
    path = rules_dir / f"{name}.md"
    if path.exists():
        path.unlink()
        return True
    return False
