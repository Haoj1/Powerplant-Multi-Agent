"""Pydantic models for all message types in the multi-agent system."""

from datetime import datetime
from enum import Enum
from typing import List, Optional, Dict, Any

from pydantic import BaseModel, Field


class FaultType(str, Enum):
    """Fault types that can occur in the system."""
    NONE = "none"
    BEARING_WEAR = "bearing_wear"
    CLOGGING = "clogging"
    VALVE_STUCK = "valve_stuck"
    SENSOR_DRIFT = "sensor_drift"
    SENSOR_STUCK = "sensor_stuck"
    NOISE_BURST = "noise_burst"
    UNKNOWN = "unknown"


class Severity(str, Enum):
    """Alert severity levels."""
    WARNING = "warning"
    CRITICAL = "critical"


class RootCause(str, Enum):
    """Root cause types for diagnosis."""
    BEARING_WEAR = "bearing_wear"
    CLOGGING = "clogging"
    VALVE_STUCK = "valve_stuck"
    SENSOR_DRIFT = "sensor_drift"
    UNKNOWN = "unknown"


class Impact(str, Enum):
    """Impact levels for diagnosis."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class TicketSystem(str, Enum):
    """Ticket system types."""
    GITHUB = "github"
    LOCAL = "local"


class ReviewDecision(str, Enum):
    """Review decision types."""
    APPROVED = "approved"
    EDITED = "edited"
    REJECTED = "rejected"
    CLOSED = "closed"


# ============================================================================
# Telemetry Model
# ============================================================================

class TelemetrySignals(BaseModel):
    """Sensor signals from the pump."""
    pressure_bar: float = Field(..., description="Pressure in bar")
    flow_m3h: float = Field(..., description="Flow rate in m³/h")
    temp_c: float = Field(..., description="Temperature in Celsius")
    bearing_temp_c: float = Field(..., description="Bearing temperature in Celsius")
    vibration_rms: float = Field(..., description="Vibration RMS value")
    rpm: float = Field(..., description="RPM")
    motor_current_a: float = Field(..., description="Motor current in Amperes")
    valve_open_pct: float = Field(..., description="Valve open percentage")


class TelemetryTruth(BaseModel):
    """Ground truth for telemetry (for evaluation)."""
    fault: FaultType = Field(default=FaultType.NONE, description="Active fault type")
    severity: float = Field(default=0.0, ge=0.0, le=1.0, description="Fault severity 0-1")


class Telemetry(BaseModel):
    """Telemetry message from simulator."""
    ts: datetime = Field(..., description="Timestamp")
    plant_id: str = Field(..., description="Plant identifier")
    asset_id: str = Field(..., description="Asset identifier (e.g., pump01)")
    signals: TelemetrySignals = Field(..., description="Sensor signals")
    truth: TelemetryTruth = Field(..., description="Ground truth")


# ============================================================================
# Alert Models
# ============================================================================

class AlertDetail(BaseModel):
    """Details of a single alert."""
    signal: str = Field(..., description="Signal name that triggered alert")
    score: float = Field(..., description="Anomaly score")
    method: str = Field(..., description="Detection method (e.g., zscore, threshold)")
    window_sec: int = Field(..., description="Window size in seconds")
    evidence: Dict[str, Any] = Field(default_factory=dict, description="Additional evidence")


class AlertEvent(BaseModel):
    """Alert event from Agent A (monitor)."""
    ts: datetime = Field(..., description="Timestamp")
    plant_id: str = Field(..., description="Plant identifier")
    asset_id: str = Field(..., description="Asset identifier")
    severity: Severity = Field(..., description="Alert severity")
    alerts: List[AlertDetail] = Field(..., description="List of alert details")


# ============================================================================
# Diagnosis Models
# ============================================================================

class DiagnosisEvidence(BaseModel):
    """Evidence for a diagnosis rule."""
    rule: str = Field(..., description="Rule name that matched")
    details: Dict[str, Any] = Field(default_factory=dict, description="Rule-specific details")


class DiagnosisReport(BaseModel):
    """Diagnosis report from Agent B."""
    ts: datetime = Field(..., description="Timestamp")
    plant_id: str = Field(..., description="Plant identifier")
    asset_id: str = Field(..., description="Asset identifier")
    root_cause: RootCause = Field(..., description="Identified root cause")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score 0-1")
    impact: Impact = Field(..., description="Impact level")
    recommended_actions: List[str] = Field(default_factory=list, description="Recommended actions")
    evidence: List[DiagnosisEvidence] = Field(default_factory=list, description="Evidence from rules")


# ============================================================================
# Ticket Model
# ============================================================================

class Ticket(BaseModel):
    """Ticket created by Agent C."""
    ts: datetime = Field(..., description="Timestamp")
    plant_id: str = Field(..., description="Plant identifier")
    asset_id: str = Field(..., description="Asset identifier")
    ticket_system: TicketSystem = Field(..., description="Ticket system used")
    ticket_id: str = Field(..., description="Ticket ID")
    url: Optional[str] = Field(None, description="Ticket URL")


# ============================================================================
# Feedback Model
# ============================================================================

class Feedback(BaseModel):
    """Feedback from Agent D (human review)."""
    ts: datetime = Field(..., description="Timestamp")
    plant_id: str = Field(..., description="Plant identifier")
    asset_id: str = Field(..., description="Asset identifier")
    ticket_id: str = Field(..., description="Ticket ID being reviewed")
    review_decision: ReviewDecision = Field(..., description="Review decision")
    final_root_cause: Optional[str] = Field(None, description="Final root cause after review")
    notes: Optional[str] = Field(None, description="Review notes")
