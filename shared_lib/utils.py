"""Utility functions for the multi-agent system."""

import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict


def get_current_timestamp() -> datetime:
    """Get current UTC timestamp."""
    return datetime.now(timezone.utc)


def generate_id() -> str:
    """Generate a unique ID."""
    return str(uuid.uuid4())


def ensure_log_dir(log_dir: str) -> Path:
    """Ensure log directory exists."""
    log_path = Path(log_dir)
    log_path.mkdir(parents=True, exist_ok=True)
    return log_path


def append_jsonl(file_path: Path, data: Dict[str, Any]) -> None:
    """
    Append a JSON object to a JSONL file.
    
    Args:
        file_path: Path to the JSONL file
        data: Dictionary to append (will be serialized to JSON)
    """
    ensure_log_dir(file_path.parent)
    
    with open(file_path, "a", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, default=str)
        f.write("\n")


def format_mqtt_topic(base_topic: str, asset_id: str) -> str:
    """
    Format MQTT topic with asset ID.
    
    Args:
        base_topic: Base topic (e.g., "telemetry")
        asset_id: Asset identifier (e.g., "pump01")
    
    Returns:
        Formatted topic (e.g., "telemetry/pump01")
    """
    return f"{base_topic}/{asset_id}"
