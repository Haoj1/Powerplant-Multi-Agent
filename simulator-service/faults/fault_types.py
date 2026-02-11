"""Fault type implementations with physical mechanisms."""

from datetime import datetime
from typing import Dict, Any, Optional
import random
import math


class BaseFault:
    """Base class for all fault types."""
    
    def __init__(self, fault_type: str, start_time: float, params: Dict[str, Any]):
        self.fault_type = fault_type
        self.start_time = start_time
        self.params = params
        self.active = False
    
    def activate(self, current_time: float):
        """Activate fault if start time reached."""
        if current_time >= self.start_time:
            self.active = True
    
    def update(self, current_time: float, dt: float, models: Dict[str, Any]):
        """Update fault state (to be implemented by subclasses)."""
        pass
    
    def get_ground_truth(self) -> Dict[str, Any]:
        """Get ground truth information for this fault."""
        return {
            "fault": self.fault_type,
            "active": self.active,
            "severity": self.get_severity(),
        }
    
    def get_severity(self) -> float:
        """Get fault severity (0.0-1.0)."""
        return 1.0 if self.active else 0.0


class BearingWearFault(BaseFault):
    """
    Bearing wear fault - chronic degradation.
    
    Physical mechanism: wear level increases linearly over time
    Effects: vibration ↑, bearing temperature ↑
    """
    
    def __init__(self, start_time: float, params: Dict[str, Any]):
        super().__init__("bearing_wear", start_time, params)
        self.rate_per_sec = params.get("rate_per_sec", 0.0001)
        self.elapsed_time = 0.0
    
    def update(self, current_time: float, dt: float, models: Dict[str, Any]):
        if current_time >= self.start_time:
            self.active = True
            self.elapsed_time += dt
            bearing_model = models.get("bearing")
            if bearing_model:
                bearing_model.update_wear(self.rate_per_sec, dt)
    
    def get_severity(self) -> float:
        if not self.active:
            return 0.0
        # Severity = min(1.0, elapsed_time * rate)
        return min(1.0, self.elapsed_time * self.rate_per_sec * 10.0)


class CloggingFault(BaseFault):
    """
    Clogging fault - increased pipe resistance.
    
    Physical mechanism: effective pipe diameter decreases → resistance increases
    Effects: flow ↓, pressure ↑, motor current ↑
    """
    
    def __init__(self, start_time: float, params: Dict[str, Any]):
        super().__init__("clogging", start_time, params)
        
        # Can be step change or ramp
        if "resistance_factor" in params:
            self.mode = "step"
            self.resistance_factor = params["resistance_factor"]
        elif "ramp_rate" in params:
            self.mode = "ramp"
            self.ramp_rate = params["ramp_rate"]  # per second
            self.current_factor = 1.0
        else:
            self.mode = "step"
            self.resistance_factor = 1.5  # Default: 50% increase
    
    def update(self, current_time: float, dt: float, models: Dict[str, Any]):
        if current_time >= self.start_time:
            self.active = True
            pipe_model = models.get("pipe")
            
            if pipe_model:
                if self.mode == "step":
                    pipe_model.set_clogging_resistance(self.resistance_factor)
                elif self.mode == "ramp":
                    self.current_factor += self.ramp_rate * dt
                    pipe_model.set_clogging_resistance(self.current_factor)
    
    def get_severity(self) -> float:
        if not self.active:
            return 0.0
        
        if self.mode == "step":
            # Severity based on resistance increase
            return min(1.0, (self.resistance_factor - 1.0) / 2.0)
        else:
            # Severity based on current factor
            return min(1.0, (self.current_factor - 1.0) / 2.0)


class ValveStuckFault(BaseFault):
    """
    Valve stuck fault - valve position fixed.
    
    Physical mechanism: valve actuator fails → valve position cannot change
    Effects: flow unresponsive to valve commands
    """
    
    def __init__(self, start_time: float, params: Dict[str, Any]):
        super().__init__("valve_stuck", start_time, params)
        self.stuck_value = params.get("stuck_value", 50.0)  # %
        self.valve_command_override = None
    
    def apply_valve_command(self, valve_command: float) -> float:
        """
        Override valve command with stuck value.
        
        Args:
            valve_command: Desired valve position (%)
            
        Returns:
            Actual valve position (%)
        """
        if self.active:
            return self.stuck_value
        return valve_command
    
    def update(self, current_time: float, dt: float, models: Dict[str, Any]):
        if current_time >= self.start_time:
            self.active = True
    
    def get_severity(self) -> float:
        return 1.0 if self.active else 0.0


class SensorDriftFault(BaseFault):
    """
    Sensor drift fault - sensor reading drifts over time.
    
    Physical mechanism: sensor calibration drift or bias
    Effects: sensor reading = true_value + drift_offset
    """
    
    def __init__(self, start_time: float, params: Dict[str, Any]):
        super().__init__("sensor_drift", start_time, params)
        self.signal_name = params.get("signal", "pressure_bar")
        self.drift_rate = params.get("drift_rate", 0.01)  # per second
        self.drift_offset = 0.0
        self.elapsed_time = 0.0
    
    def apply_sensor_reading(self, signal_name: str, true_value: float) -> float:
        """
        Apply drift to sensor reading.
        
        Args:
            signal_name: Name of the signal
            true_value: True physical value
            
        Returns:
            Drifted sensor reading
        """
        if self.active and signal_name == self.signal_name:
            return true_value + self.drift_offset
        return true_value
    
    def update(self, current_time: float, dt: float, models: Dict[str, Any]):
        if current_time >= self.start_time:
            self.active = True
            self.elapsed_time += dt
            self.drift_offset = self.drift_rate * self.elapsed_time
    
    def get_severity(self) -> float:
        if not self.active:
            return 0.0
        # Severity increases with drift magnitude
        return min(1.0, abs(self.drift_offset) / 10.0)


class SensorStuckFault(BaseFault):
    """
    Sensor stuck fault - sensor reading frozen at last value.
    
    Physical mechanism: sensor failure → reading stuck
    Effects: sensor reading = constant value
    """
    
    def __init__(self, start_time: float, params: Dict[str, Any]):
        super().__init__("sensor_stuck", start_time, params)
        self.signal_name = params.get("signal", "pressure_bar")
        self.stuck_value: Optional[float] = None
        self.last_value: Optional[float] = None
    
    def apply_sensor_reading(self, signal_name: str, true_value: float) -> float:
        """
        Apply stuck fault to sensor reading.
        
        Args:
            signal_name: Name of the signal
            true_value: True physical value
            
        Returns:
            Stuck sensor reading
        """
        if signal_name == self.signal_name:
            if not self.active:
                # Before fault: record last value
                self.last_value = true_value
                return true_value
            else:
                # After fault: return stuck value
                if self.stuck_value is None:
                    self.stuck_value = self.last_value if self.last_value is not None else true_value
                return self.stuck_value
        
        return true_value
    
    def update(self, current_time: float, dt: float, models: Dict[str, Any]):
        if current_time >= self.start_time:
            self.active = True
    
    def get_severity(self) -> float:
        return 1.0 if self.active else 0.0


class NoiseBurstFault(BaseFault):
    """
    Noise burst fault - sensor noise suddenly increases.
    
    Physical mechanism: sensor interference or electrical noise
    Effects: sensor reading = true_value + large_noise
    """
    
    def __init__(self, start_time: float, params: Dict[str, Any]):
        super().__init__("noise_burst", start_time, params)
        self.signal_name = params.get("signal", "vibration_rms")
        self.noise_amplitude = params.get("noise_amplitude", 5.0)
        self.duration_sec = params.get("duration_sec", 10.0)
        self.elapsed_time = 0.0
        self.random_seed = params.get("seed", None)
        if self.random_seed:
            random.seed(self.random_seed)
    
    def apply_sensor_reading(self, signal_name: str, true_value: float) -> float:
        """
        Apply noise burst to sensor reading.
        
        Args:
            signal_name: Name of the signal
            true_value: True physical value
            
        Returns:
            Noisy sensor reading
        """
        if self.active and signal_name == self.signal_name:
            if self.elapsed_time < self.duration_sec:
                noise = random.gauss(0, self.noise_amplitude)
                return true_value + noise
        return true_value
    
    def update(self, current_time: float, dt: float, models: Dict[str, Any]):
        if current_time >= self.start_time:
            self.active = True
            self.elapsed_time += dt
    
    def get_severity(self) -> float:
        if not self.active:
            return 0.0
        if self.elapsed_time >= self.duration_sec:
            return 0.0  # Fault ended
        return 1.0
