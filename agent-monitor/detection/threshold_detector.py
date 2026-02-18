"""Threshold-based anomaly detection."""

from datetime import datetime, timezone
from typing import Optional

from shared_lib.models import (
    Telemetry,
    AlertEvent,
    AlertDetail,
    Severity,
)


# Default thresholds (aligned with ISO 20816 and typical pump limits)
# Note: Lowered for easier testing - adjust based on your pump's normal operating range
DEFAULT_THRESHOLDS = {
    "vibration_rms": {"warning": 7.1, "critical": 18.0},
    "bearing_temp_c": {"warning": 70.0, "critical": 85.0},
    "pressure_bar": {"warning_high": 8.0, "critical_high": 12.0},  # Lowered for testing
    "motor_current_a": {"warning_high": 15.0, "critical_high": 20.0},  # Lowered for testing
    "temp_c": {"warning_high": 80.0, "critical_high": 95.0},
}


class ThresholdDetector:
    """
    Detects anomalies when signals exceed configured thresholds.
    Uses warning/critical levels; critical takes precedence.
    """

    def __init__(self, thresholds: Optional[dict] = None):
        self.thresholds = thresholds or DEFAULT_THRESHOLDS.copy()

    def detect(self, telemetry: Telemetry) -> Optional[AlertEvent]:
        """
        Check telemetry signals against thresholds.
        Returns an AlertEvent if any threshold is breached, else None.
        """
        alerts = []
        max_severity = None

        signals_dict = telemetry.signals.model_dump()

        for signal_name, value in signals_dict.items():
            if signal_name not in self.thresholds:
                continue

            rule = self.thresholds[signal_name]

            # High-side thresholds (e.g. vibration, temperature)
            if "critical" in rule and "critical_high" not in rule:
                if value >= rule["critical"]:
                    alerts.append(
                        AlertDetail(
                            signal=signal_name,
                            score=float(value),
                            method="threshold",
                            window_sec=0,
                            evidence={"value": value, "threshold": rule["critical"], "side": "high"},
                        )
                    )
                    max_severity = Severity.CRITICAL
                elif value >= rule.get("warning", rule["critical"] * 0.5):
                    alerts.append(
                        AlertDetail(
                            signal=signal_name,
                            score=float(value),
                            method="threshold",
                            window_sec=0,
                            evidence={"value": value, "threshold": rule.get("warning"), "side": "high"},
                        )
                    )
                    if max_severity != Severity.CRITICAL:
                        max_severity = Severity.WARNING

            # Optional high-side with separate warning_high/critical_high keys
            if "critical_high" in rule:
                if value >= rule["critical_high"]:
                    alerts.append(
                        AlertDetail(
                            signal=signal_name,
                            score=float(value),
                            method="threshold",
                            window_sec=0,
                            evidence={"value": value, "threshold": rule["critical_high"], "side": "high"},
                        )
                    )
                    max_severity = Severity.CRITICAL
                elif value >= rule.get("warning_high", rule["critical_high"] * 0.8):
                    alerts.append(
                        AlertDetail(
                            signal=signal_name,
                            score=float(value),
                            method="threshold",
                            window_sec=0,
                            evidence={"value": value, "threshold": rule.get("warning_high"), "side": "high"},
                        )
                    )
                    if max_severity != Severity.CRITICAL:
                        max_severity = Severity.WARNING

        if not alerts:
            return None

        return AlertEvent(
            ts=datetime.now(timezone.utc),
            plant_id=telemetry.plant_id,
            asset_id=telemetry.asset_id,
            severity=max_severity or Severity.WARNING,
            alerts=alerts,
        )
