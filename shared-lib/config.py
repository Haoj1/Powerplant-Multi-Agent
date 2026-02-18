"""Configuration management using environment variables."""

from functools import lru_cache
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",  # ignore unknown env vars so they don't cause ValidationError
    )

    # MQTT Configuration
    mqtt_host: str = "localhost"
    mqtt_port: int = 1883
    mqtt_username: Optional[str] = None
    mqtt_password: Optional[str] = None
    
    # MQTT Topics
    mqtt_topic_telemetry: str = "telemetry"
    mqtt_topic_alerts: str = "alerts"
    mqtt_topic_diagnosis: str = "diagnosis"
    mqtt_topic_tickets: str = "tickets"
    mqtt_topic_feedback: str = "feedback"
    
    # GitHub Configuration (for Agent C)
    github_token: Optional[str] = None
    github_repo: Optional[str] = None
    
    # Logging
    log_dir: str = "logs"

    # SQLite (for querying and dashboard; JSONL logs are kept as-is)
    sqlite_path: str = "data/monitoring.db"
    # Only write telemetry to DB every N seconds (0 = every sim step). Reduces DB rows when sim is high-frequency.
    db_telemetry_interval_sec: float = 0.0

    # Simulator Configuration
    simulator_frequency_hz: float = 1.0
    
    # Agent Monitor Configuration
    monitor_window_sec: int = 120
    
    # VLM Configuration (for multimodal vision)
    vlm_provider: str = "claude"  # "claude" or "openai"
    anthropic_api_key: Optional[str] = None
    openai_api_key: Optional[str] = None
    vision_frequency_sec: int = 5  # Generate vision description every N seconds
    
    # MQTT Topics (extended)
    mqtt_topic_vision: str = "vision"  # Vision descriptions
    
    # DeepSeek (optional, for Agent B / LLM)
    deepseek_api_key: Optional[str] = None
    deepseek_base_url: Optional[str] = None

    # Agent B (Diagnosis)
    diagnosis_rules_path: str = "agent-diagnosis/rules"
    # Min seconds between producing diagnoses (global cooldown to prevent pile-up)
    diagnosis_cooldown_sec: float = 20.0

    # Agent C (Review Queue)
    ticket_cooldown_sec: float = 30.0  # Max one review_request per asset per N sec


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
