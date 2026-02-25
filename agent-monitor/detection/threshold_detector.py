"""Threshold-based anomaly detection with optional sliding window, trend, and duration."""

from datetime import datetime, timezone
from typing import Optional, TYPE_CHECKING

from shared_lib.models import (
    Telemetry,
    AlertEvent,
    AlertDetail,
    Severity,
)

if TYPE_CHECKING:
    from .telemetry_buffer import TelemetryBuffer


# Default thresholds (aligned with ISO 20816 and typical pump limits)
# Based on actual healthy baseline data: vibration ~2.0 mm/s, bearing_temp ~45-60°C, pressure ~5-6 bar, current ~30-32 A
DEFAULT_THRESHOLDS = {
    "vibration_rms": {"warning": 7.1, "critical": 18.0},  # ISO 20816
    "bearing_temp_c": {"warning": 70.0, "critical": 85.0},
    "pressure_bar": {"warning_high": 18.0, "critical_high": 25.0},
    "motor_current_a": {"warning_high": 38.0, "critical_high": 45.0},
    "temp_c": {"warning_high": 80.0, "critical_high": 95.0},
    "flow_m3h": {"warning_low": 80.0, "critical_low": 50.0},  # P1: nominal ~100 m³/h
    "rpm": {"min": 1400.0, "max": 1600.0},  # P1: normal ~1500 rpm
}

# Valve-flow mismatch: valve > 80% but flow < 50% nominal (50 m³/h)
VALVE_FLOW_MISMATCH = {"valve_min_pct": 80.0, "flow_max_m3h": 50.0}

# Slopes (unit per second). "high" = alert when slope >= threshold; "low" = alert when slope <= threshold
DEFAULT_SLOPE_THRESHOLDS = {
    "vibration_rms": {"warning": 0.03, "critical": 0.08},
    "bearing_temp_c": {"warning": 0.1, "critical": 0.3},
    "flow_m3h": {"warning": -2.0, "critical": -5.0, "side": "low", "window_sec": 10},  # P2: sudden drop
    "pressure_bar": {"warning": 0.5, "critical": 1.0, "window_sec": 10},  # P2: sudden spike
    "motor_current_a": {"warning": 0.3, "critical": 0.8, "window_sec": 5},  # P2: current surge
}


class ThresholdDetector:
    """
    Detects anomalies when signals exceed configured thresholds.
    Uses warning/critical levels; critical takes precedence.
    With buffer: supports duration (sustained breach) and slope (trend) checks.
    """

    def __init__(
        self,
        thresholds: Optional[dict] = None,
        slope_thresholds: Optional[dict] = None,
        min_duration_sec: int = 0,
        window_sec: int = 60,
    ):
        self.thresholds = thresholds or DEFAULT_THRESHOLDS.copy()
        self.slope_thresholds = slope_thresholds or DEFAULT_SLOPE_THRESHOLDS.copy()
        self.min_duration_sec = min_duration_sec
        self.window_sec = window_sec

    def detect(
        self,
        telemetry: Telemetry,
        buffer: Optional["TelemetryBuffer"] = None,
    ) -> Optional[AlertEvent]:
        """
        Check telemetry signals against thresholds.
        With buffer: only alert if duration >= min_duration_sec; add slope-based alerts.
        Returns an AlertEvent if any threshold is breached, else None.
        """
        alerts = []
        max_severity = None
        signals_dict = telemetry.signals.model_dump()

        def _add_evidence(evidence: dict, signal_name: str, side: str = "high") -> dict:
            if buffer and signal_name in signals_dict:
                w = evidence.get("window_sec", self.window_sec)
                stats = buffer.compute_stats(telemetry.asset_id, signal_name, w)
                thr_val = evidence.get("threshold")
                if thr_val is not None:
                    dur = buffer.duration_above_threshold(
                        telemetry.asset_id, signal_name, thr_val, side, w
                    )
                    key = "duration_above_threshold" if side == "high" else "duration_below_threshold"
                    evidence[key] = round(dur, 1)
                evidence["window_sec"] = w
                if stats.get("mean") is not None:
                    evidence["mean"] = round(stats["mean"], 3)
                if stats.get("std") is not None:
                    evidence["std"] = round(stats["std"], 3)
                if stats.get("slope") is not None:
                    evidence["slope"] = round(stats["slope"], 5)
            return evidence

        for signal_name, value in signals_dict.items():
            if signal_name not in self.thresholds:
                continue

            rule = self.thresholds[signal_name]
            evidence_base = {"value": value, "side": "high"}

            # Duration check: skip threshold alert if buffer says we haven't sustained long enough
            side = "low" if "critical_low" in rule or "warning_low" in rule else "high"
            min_dur = 15 if signal_name == "flow_m3h" else (10 if signal_name == "rpm" else self.min_duration_sec)
            if buffer and min_dur > 0:
                thr_val = rule.get("critical") or rule.get("critical_high") or rule.get("critical_low")
                if thr_val is not None:
                    dur = buffer.duration_above_threshold(
                        telemetry.asset_id, signal_name, thr_val, side, self.window_sec
                    )
                    if dur < min_dur:
                        continue
                thr_warn = rule.get("warning") or rule.get("warning_high") or rule.get("warning_low")
                if thr_warn is not None:
                    in_range = (value <= thr_warn and value > (thr_val or -float("inf"))) if side == "low" else (value >= thr_warn and value < (thr_val or float("inf")))
                    if in_range:
                        dur_warn = buffer.duration_above_threshold(
                            telemetry.asset_id, signal_name, thr_warn, side, self.window_sec
                        )
                        if dur_warn < min_dur:
                            continue

            # Low-side thresholds (e.g. flow_m3h)
            if "critical_low" in rule:
                if value <= rule["critical_low"]:
                    ev = _add_evidence({**evidence_base, "threshold": rule["critical_low"], "side": "low"}, signal_name, "low")
                    alerts.append(
                        AlertDetail(
                            signal=signal_name,
                            score=float(value),
                            method="threshold",
                            window_sec=self.window_sec,
                            evidence=ev,
                        )
                    )
                    max_severity = Severity.CRITICAL
                elif value <= rule.get("warning_low", rule["critical_low"] * 1.5):
                    ev = _add_evidence({**evidence_base, "threshold": rule.get("warning_low"), "side": "low"}, signal_name, "low")
                    alerts.append(
                        AlertDetail(
                            signal=signal_name,
                            score=float(value),
                            method="threshold",
                            window_sec=self.window_sec,
                            evidence=ev,
                        )
                    )
                    if max_severity != Severity.CRITICAL:
                        max_severity = Severity.WARNING

            # Range thresholds (rpm: min, max)
            if "min" in rule and "max" in rule:
                if value < rule["min"] or value > rule["max"]:
                    if buffer and min_dur > 0:
                        thr = rule["min"] if value < rule["min"] else rule["max"]
                        side_rpm = "low" if value < rule["min"] else "high"
                        dur = buffer.duration_above_threshold(
                            telemetry.asset_id, signal_name, thr, side_rpm, self.window_sec
                        )
                        if dur < min_dur:
                            continue
                    thr = rule["min"] if value < rule["min"] else rule["max"]
                    ev_side = "low" if value < rule["min"] else "high"
                    ev = _add_evidence({"value": value, "threshold": thr, "side": "range"}, signal_name, ev_side)
                    ev["min_rpm"] = rule["min"]
                    ev["max_rpm"] = rule["max"]
                    alerts.append(
                        AlertDetail(
                            signal=signal_name,
                            score=float(value),
                            method="threshold",
                            window_sec=self.window_sec,
                            evidence=ev,
                        )
                    )
                    if max_severity != Severity.CRITICAL:
                        max_severity = Severity.WARNING

            # High-side thresholds (e.g. vibration, temperature)
            if "critical" in rule and "critical_high" not in rule:
                if value >= rule["critical"]:
                    ev = _add_evidence({**evidence_base, "threshold": rule["critical"]}, signal_name)
                    alerts.append(
                        AlertDetail(
                            signal=signal_name,
                            score=float(value),
                            method="threshold",
                            window_sec=self.window_sec,
                            evidence=ev,
                        )
                    )
                    max_severity = Severity.CRITICAL
                elif value >= rule.get("warning", rule["critical"] * 0.5):
                    ev = _add_evidence({**evidence_base, "threshold": rule.get("warning")}, signal_name)
                    alerts.append(
                        AlertDetail(
                            signal=signal_name,
                            score=float(value),
                            method="threshold",
                            window_sec=self.window_sec,
                            evidence=ev,
                        )
                    )
                    if max_severity != Severity.CRITICAL:
                        max_severity = Severity.WARNING

            # Optional high-side with separate warning_high/critical_high keys
            if "critical_high" in rule:
                if value >= rule["critical_high"]:
                    ev = _add_evidence({**evidence_base, "threshold": rule["critical_high"]}, signal_name)
                    alerts.append(
                        AlertDetail(
                            signal=signal_name,
                            score=float(value),
                            method="threshold",
                            window_sec=self.window_sec,
                            evidence=ev,
                        )
                    )
                    max_severity = Severity.CRITICAL
                elif value >= rule.get("warning_high", rule["critical_high"] * 0.8):
                    ev = _add_evidence({**evidence_base, "threshold": rule.get("warning_high")}, signal_name)
                    alerts.append(
                        AlertDetail(
                            signal=signal_name,
                            score=float(value),
                            method="threshold",
                            window_sec=self.window_sec,
                            evidence=ev,
                        )
                    )
                    if max_severity != Severity.CRITICAL:
                        max_severity = Severity.WARNING

        # Valve-flow mismatch (P1 combination)
        if buffer and "valve_open_pct" in signals_dict and "flow_m3h" in signals_dict:
            v_min = VALVE_FLOW_MISMATCH["valve_min_pct"]
            f_max = VALVE_FLOW_MISMATCH["flow_max_m3h"]
            if signals_dict["valve_open_pct"] >= v_min and signals_dict["flow_m3h"] <= f_max:
                dur = buffer.duration_valve_flow_mismatch(telemetry.asset_id, v_min, f_max, 60)
                if dur >= 20:
                    alerts.append(
                        AlertDetail(
                            signal="valve_flow_mismatch",
                            score=float(signals_dict["flow_m3h"]),
                            method="combination",
                            window_sec=60,
                            evidence={
                                "valve_open_pct": round(signals_dict["valve_open_pct"], 1),
                                "flow_m3h": round(signals_dict["flow_m3h"], 2),
                                "duration_sec": round(dur, 1),
                                "valve_min_pct": v_min,
                                "flow_max_m3h": f_max,
                            },
                        )
                    )
                    if max_severity != Severity.CRITICAL:
                        max_severity = Severity.WARNING

        # Slope-based alerts (trend: gradual increase or sudden drop)
        if buffer and self.slope_thresholds:
            for signal_name, slope_rule in self.slope_thresholds.items():
                if signal_name not in signals_dict:
                    continue
                w = slope_rule.get("window_sec", self.window_sec)
                stats = buffer.compute_stats(telemetry.asset_id, signal_name, w)
                slope = stats.get("slope")
                if slope is None or len(buffer.get_window(telemetry.asset_id, signal_name, w)) < 2:
                    continue
                side = slope_rule.get("side", "high")
                crit = slope_rule.get("critical")
                warn = slope_rule.get("warning")
                triggered_crit = (slope >= crit) if side == "high" else (slope <= crit) if crit is not None else False
                triggered_warn = (slope >= warn) if side == "high" else (slope <= warn) if warn is not None else False
                if triggered_crit and crit is not None:
                    alerts.append(
                        AlertDetail(
                            signal=signal_name,
                            score=float(slope),
                            method="slope",
                            window_sec=w,
                            evidence={
                                "slope": round(slope, 5),
                                "window_sec": w,
                                "unit_per_sec": "trend",
                                "threshold": crit,
                                "side": side,
                            },
                        )
                    )
                    max_severity = Severity.CRITICAL
                elif triggered_warn and warn is not None:
                    alerts.append(
                        AlertDetail(
                            signal=signal_name,
                            score=float(slope),
                            method="slope",
                            window_sec=w,
                            evidence={
                                "slope": round(slope, 5),
                                "window_sec": w,
                                "unit_per_sec": "trend",
                                "threshold": warn,
                                "side": side,
                            },
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
