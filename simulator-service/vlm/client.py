"""VLM client for analyzing pump visualization images."""

import sys
from pathlib import Path
from typing import Optional
from dataclasses import dataclass
import base64
import os

_project_root = Path(__file__).parent.parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from shared_lib.config import get_settings


@dataclass
class VisionDescription:
    """Vision analysis result from VLM."""
    description: str
    anomalies_detected: list[str]
    confidence: float


class VLMClient:
    """
    Vision Language Model client.
    
    Supports Claude Vision (Anthropic) and OpenAI GPT-4V.
    Analyzes pump visualization images and returns text descriptions.
    """

    def __init__(self, provider: str = "claude", api_key: Optional[str] = None):
        """
        Initialize VLM client.
        
        Args:
            provider: "claude" or "openai"
            api_key: API key (if None, reads from settings)
        """
        self.provider = provider.lower()
        settings = get_settings()
        
        if provider == "claude":
            try:
                import anthropic
                self.api_key = api_key or getattr(settings, "anthropic_api_key", None) or os.getenv("ANTHROPIC_API_KEY")
                if not self.api_key:
                    raise ValueError("ANTHROPIC_API_KEY not found. Set it in .env file.")
                self.client = anthropic.Anthropic(api_key=self.api_key)
                # Sonnet 3.5 retired Oct 2025; use Sonnet 4.5 (vision-capable)
                self.claude_model = os.getenv("ANTHROPIC_VISION_MODEL", "claude-sonnet-4-5-20250929")
            except ImportError:
                raise ImportError("anthropic package not installed. Run: pip install anthropic")
        
        elif provider == "openai":
            try:
                import openai
                self.api_key = api_key or getattr(settings, "openai_api_key", None) or os.getenv("OPENAI_API_KEY")
                if not self.api_key:
                    raise ValueError("OPENAI_API_KEY not found. Set it in .env file.")
                self.client = openai.OpenAI(api_key=self.api_key)
            except ImportError:
                raise ImportError("openai package not installed. Run: pip install openai")
        
        else:
            raise ValueError(f"Unknown provider: {provider}. Use 'claude' or 'openai'")
    
    def analyze_image(self, image_path: Path, context: Optional[str] = None) -> VisionDescription:
        """
        Analyze pump visualization image and return description.
        
        Args:
            image_path: Path to PNG image
            context: Optional context (e.g., current sensor values)
            
        Returns:
            VisionDescription with analysis
        """
        # Read image and encode as base64
        with open(image_path, "rb") as f:
            image_data = base64.b64encode(f.read()).decode("utf-8")
        
        # Build prompt
        prompt = self._build_prompt(context)
        
        if self.provider == "claude":
            return self._analyze_claude(image_data, prompt)
        else:  # openai
            return self._analyze_openai(image_path, prompt)
    
    def _build_prompt(self, context: Optional[str]) -> str:
        """Build prompt for VLM."""
        base_prompt = """Analyze this 3D visualization of an industrial pump system.

Describe:
1. The overall state of the pump (colors indicate health: green=normal, yellow=warning, orange/red=problem)
2. Any visible anomalies (e.g., red/orange components)
3. The condition of key components (pump body, bearings, pipes, motor)

Be concise and focus on actionable observations."""
        
        if context:
            prompt = f"{base_prompt}\n\nContext: {context}"
        else:
            prompt = base_prompt
        
        return prompt
    
    def _analyze_claude(self, image_data: str, prompt: str) -> VisionDescription:
        """Analyze using Claude Vision."""
        message = self.client.messages.create(
            model=getattr(self, "claude_model", "claude-sonnet-4-5-20250929"),
            max_tokens=500,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": "image/png",
                                "data": image_data,
                            },
                        },
                        {
                            "type": "text",
                            "text": prompt,
                        },
                    ],
                }
            ],
        )
        
        description_text = message.content[0].text
        
        # Extract anomalies (simple heuristic: look for keywords)
        anomalies = []
        text_lower = description_text.lower()
        if "red" in text_lower or "critical" in text_lower:
            anomalies.append("high_vibration_or_temperature")
        if "orange" in text_lower or "warning" in text_lower:
            anomalies.append("elevated_conditions")
        
        return VisionDescription(
            description=description_text,
            anomalies_detected=anomalies,
            confidence=0.8 if anomalies else 0.9,
        )
    
    def _analyze_openai(self, image_path: Path, prompt: str) -> VisionDescription:
        """Analyze using OpenAI GPT-4V."""
        import base64
        with open(image_path, "rb") as f:
            image_b64 = base64.b64encode(f.read()).decode()
        
        response = self.client.chat.completions.create(
            model="gpt-4o",  # or gpt-4-vision-preview
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{image_b64}"
                            },
                        },
                    ],
                }
            ],
            max_tokens=500,
        )
        
        description_text = response.choices[0].message.content
        
        anomalies = []
        text_lower = description_text.lower()
        if "red" in text_lower or "critical" in text_lower:
            anomalies.append("high_vibration_or_temperature")
        if "orange" in text_lower or "warning" in text_lower:
            anomalies.append("elevated_conditions")
        
        return VisionDescription(
            description=description_text,
            anomalies_detected=anomalies,
            confidence=0.8 if anomalies else 0.9,
        )
