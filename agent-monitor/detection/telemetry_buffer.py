"""In-memory sliding window buffer for recent telemetry per asset."""

from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any

from shared_lib.models import Telemetry


@dataclass
class BufferedPoint:
    """Single telemetry point with timestamp."""
    ts: datetime
    signals: Dict[str, float]


class TelemetryBuffer:
    """
    Maintains a per-asset sliding window of recent telemetry.
    Used by Agent A for trend/duration detection.
    """

    def __init__(self, window_sec: int = 120, max_points_per_asset: int = 200):
        self.window_sec = window_sec
        self.max_points_per_asset = max_points_per_asset
        self._buffers: Dict[str, List[BufferedPoint]] = defaultdict(list)

    def push(self, telemetry: Telemetry) -> None:
        """Append telemetry to the asset's buffer and trim old points."""
        asset_id = telemetry.asset_id
        ts = telemetry.ts
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        signals_dict = telemetry.signals.model_dump()
        self._buffers[asset_id].append(BufferedPoint(ts=ts, signals=signals_dict))
        self._trim(asset_id, ts)

    def _trim(self, asset_id: str, now: datetime) -> None:
        """Remove points older than window_sec."""
        cutoff = now - timedelta(seconds=self.window_sec)
        buf = self._buffers[asset_id]
        while buf and buf[0].ts < cutoff:
            buf.pop(0)
        while len(buf) > self.max_points_per_asset:
            buf.pop(0)

    def get_window(
        self,
        asset_id: str,
        signal: str,
        window_sec: Optional[int] = None,
        now: Optional[datetime] = None,
    ) -> List[tuple]:
        """
        Return [(ts, value), ...] for the signal in ascending time order.
        Uses points within window_sec of `now` (default: latest ts in buffer).
        """
        buf = self._buffers.get(asset_id, [])
        if not buf:
            return []
        w = window_sec or self.window_sec
        if now is None:
            now = buf[-1].ts
        if now.tzinfo is None:
            now = now.replace(tzinfo=timezone.utc)
        cutoff = now - timedelta(seconds=w)
        points = [(p.ts, p.signals.get(signal)) for p in buf if p.ts >= cutoff and signal in p.signals]
        points = [(t, v) for t, v in points if v is not None]
        return sorted(points, key=lambda x: x[0])

    def compute_stats(
        self,
        asset_id: str,
        signal: str,
        window_sec: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Compute mean, std, slope for the signal over the window."""
        points = self.get_window(asset_id, signal, window_sec)
        if len(points) < 2:
            return {"mean": None, "std": None, "slope": None, "count": len(points)}
        values = [v for _, v in points]
        n = len(values)
        mean = sum(values) / n
        variance = sum((x - mean) ** 2 for x in values) / n if n > 0 else 0
        std = variance ** 0.5
        # Linear regression slope (value per second)
        t0 = points[0][0].timestamp()
        slope = 0.0
        if n >= 2 and points[-1][0].timestamp() > t0:
            t_last = points[-1][0].timestamp()
            dt = t_last - t0
            slope = (values[-1] - values[0]) / dt if dt > 0 else 0.0
        return {"mean": mean, "std": std, "slope": slope, "count": n}

    def duration_above_threshold(
        self,
        asset_id: str,
        signal: str,
        threshold: float,
        side: str = "high",
        window_sec: Optional[int] = None,
    ) -> float:
        """
        Return seconds the signal has been above (or below) threshold in the window.
        side: "high" = count when value >= threshold, "low" = count when value <= threshold.
        """
        points = self.get_window(asset_id, signal, window_sec)
        if not points:
            return 0.0
        total_sec = 0.0
        for i in range(len(points)):
            t, v = points[i]
            above = (side == "high" and v >= threshold) or (side == "low" and v <= threshold)
            if above:
                if i + 1 < len(points):
                    total_sec += (points[i + 1][0] - t).total_seconds()
                else:
                    total_sec += 0  # last point: no interval to add
        return total_sec

    def duration_valve_flow_mismatch(
        self,
        asset_id: str,
        valve_min_pct: float,
        flow_max_m3h: float,
        window_sec: Optional[int] = None,
    ) -> float:
        """Return seconds valve_open_pct >= valve_min_pct AND flow_m3h <= flow_max_m3h in the window."""
        buf = self._buffers.get(asset_id, [])
        if not buf:
            return 0.0
        w = window_sec or self.window_sec
        now = buf[-1].ts
        if now.tzinfo is None:
            now = now.replace(tzinfo=timezone.utc)
        cutoff = now - timedelta(seconds=w)
        total_sec = 0.0
        for i, p in enumerate(buf):
            if p.ts < cutoff:
                continue
            valve = p.signals.get("valve_open_pct")
            flow = p.signals.get("flow_m3h")
            if valve is None or flow is None:
                continue
            if valve >= valve_min_pct and flow <= flow_max_m3h:
                if i + 1 < len(buf) and buf[i + 1].ts >= cutoff:
                    dt = (buf[i + 1].ts - p.ts).total_seconds()
                    total_sec += dt
        return total_sec
