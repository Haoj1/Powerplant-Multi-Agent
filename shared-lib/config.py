"""Configuration management using environment variables."""

from functools import lru_cache
from typing import Optional

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
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
    
    # Simulator Configuration
    simulator_frequency_hz: float = 1.0
    
    # Agent Monitor Configuration
    monitor_window_sec: int = 120
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
