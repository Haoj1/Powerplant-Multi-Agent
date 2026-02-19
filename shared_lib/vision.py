"""VLM image analysis for agents. Uses config (vlm_provider, API keys) to describe or answer questions about images."""

import base64
import os
from pathlib import Path
from typing import Optional


def analyze_image(
    image_path: str,
    question: Optional[str] = None,
    context: Optional[str] = None,
) -> str:
    """
    Analyze an image with the configured VLM (Claude or OpenAI) and return a text description or answer.

    Args:
        image_path: Absolute path or path relative to project root to a PNG/JPEG image.
        question: Optional question to ask about the image (e.g. "Any anomalies?"). If empty, uses default description prompt.
        context: Optional context string (e.g. current sensor values) to include in the prompt.

    Returns:
        VLM response text. On error, returns an error message string.
    """
    path = Path(image_path)
    if not path.is_absolute():
        project_root = Path(__file__).resolve().parent.parent
        path = project_root / path
    if not path.exists():
        return f"Image not found: {path}"
    if not path.is_file():
        return f"Not a file: {path}"

    try:
        with open(path, "rb") as f:
            image_data = base64.b64encode(f.read()).decode("utf-8")
    except Exception as e:
        return f"Failed to read image: {e}"

    from shared_lib.config import get_settings
    settings = get_settings()
    provider = (getattr(settings, "vlm_provider", None) or "claude").lower()

    if question and question.strip():
        prompt = question.strip()
        if context:
            prompt = f"{prompt}\n\nContext: {context}"
    else:
        base_prompt = """Analyze this image (e.g. industrial pump visualization or equipment).

Describe:
1. The overall state (colors often indicate health: green=normal, yellow=warning, orange/red=problem)
2. Any visible anomalies
3. Key components' condition

Be concise and focus on actionable observations."""
        prompt = base_prompt if not context else f"{base_prompt}\n\nContext: {context}"

    media_type = "image/png" if path.suffix.lower() in (".png",) else "image/jpeg"

    if provider == "claude":
        return _analyze_claude(settings, image_data, prompt, media_type)
    if provider == "openai":
        return _analyze_openai(settings, image_data, prompt, media_type)
    return f"Unknown VLM provider: {provider}. Set VLM_PROVIDER to 'claude' or 'openai'."


def _analyze_claude(settings, image_data: str, prompt: str, media_type: str) -> str:
    try:
        import anthropic
    except ImportError:
        return "anthropic package not installed. Run: pip install anthropic"
    api_key = getattr(settings, "anthropic_api_key", None) or os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        return "ANTHROPIC_API_KEY not set. Configure in .env for vision."
    client = anthropic.Anthropic(api_key=api_key)
    model = os.getenv("ANTHROPIC_VISION_MODEL", "claude-sonnet-4-5-20250929")
    message = client.messages.create(
        model=model,
        max_tokens=500,
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "image", "source": {"type": "base64", "media_type": media_type, "data": image_data}},
                    {"type": "text", "text": prompt},
                ],
            }
        ],
    )
    return message.content[0].text if message.content else ""


def _analyze_openai(settings, image_data: str, prompt: str, media_type: str) -> str:
    try:
        from openai import OpenAI
    except ImportError:
        return "openai package not installed. Run: pip install openai"
    api_key = getattr(settings, "openai_api_key", None) or os.getenv("OPENAI_API_KEY")
    if not api_key:
        return "OPENAI_API_KEY not set. Configure in .env for vision."
    client = OpenAI(api_key=api_key)
    url = f"data:{media_type};base64,{image_data}"
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "user", "content": [{"type": "text", "text": prompt}, {"type": "image_url", "image_url": {"url": url}}]},
        ],
        max_tokens=500,
    )
    if not response.choices:
        return ""
    return response.choices[0].message.content or ""
