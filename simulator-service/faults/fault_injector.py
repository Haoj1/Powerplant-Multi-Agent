"""Fault injection engine for simulator."""

from typing import Dict, List, Any, Optional
from datetime import datetime

from .fault_types import (
    BaseFault,
    BearingWearFault,
    CloggingFault,
    ValveStuckFault,
    SensorDriftFault,
    SensorStuckFault,
    NoiseBurstFault,
)


class FaultInjector:
    """
    Fault injection engine with physical mechanisms.
    
    Manages all active faults and applies them to physical models and sensor readings.
    """
    
    def __init__(self):
        """Initialize fault injector."""
        self.active_faults: List[BaseFault] = []
        self.models: Dict[str, Any] = {}
    
    def register_models(
        self,
        pump_model=None,
        pipe_model=None,
        bearing_model=None,
        motor_model=None
    ):
        """Register physical models for fault injection."""
        if pump_model:
            self.models["pump"] = pump_model
        if pipe_model:
            self.models["pipe"] = pipe_model
        if bearing_model:
            self.models["bearing"] = bearing_model
        if motor_model:
            self.models["motor"] = motor_model
    
    def inject_fault(self, fault_type: str, start_time: float, params: Dict[str, Any]):
        """
        Inject a fault into the system.
        
        Args:
            fault_type: Type of fault (bearing_wear, clogging, valve_stuck, etc.)
            start_time: Time when fault starts (seconds from scenario start)
            params: Fault-specific parameters
        """
        fault_map = {
            "bearing_wear": BearingWearFault,
            "clogging": CloggingFault,
            "valve_stuck": ValveStuckFault,
            "sensor_drift": SensorDriftFault,
            "sensor_stuck": SensorStuckFault,
            "noise_burst": NoiseBurstFault,
        }
        
        fault_class = fault_map.get(fault_type)
        if fault_class:
            fault = fault_class(start_time, params)
            self.active_faults.append(fault)
        else:
            raise ValueError(f"Unknown fault type: {fault_type}")
    
    def update_faults(self, current_time: float, dt: float):
        """
        Update all active faults.
        
        Args:
            current_time: Current simulation time (seconds)
            dt: Time step (seconds)
        """
        for fault in self.active_faults:
            fault.activate(current_time)
            fault.update(current_time, dt, self.models)
    
    def apply_valve_faults(self, valve_command: float) -> float:
        """
        Apply valve-related faults to valve command.
        
        Args:
            valve_command: Desired valve position (%)
            
        Returns:
            Actual valve position after fault application (%)
        """
        valve_actual = valve_command
        
        for fault in self.active_faults:
            if isinstance(fault, ValveStuckFault):
                valve_actual = fault.apply_valve_command(valve_actual)
        
        return valve_actual
    
    def apply_sensor_faults(self, signals: Dict[str, float]) -> Dict[str, float]:
        """
        Apply sensor faults to sensor readings.
        
        Args:
            signals: Dictionary of signal_name -> true_value
            
        Returns:
            Dictionary of signal_name -> sensor_reading (after faults)
        """
        sensor_signals = signals.copy()
        
        for fault in self.active_faults:
            if isinstance(fault, (SensorDriftFault, SensorStuckFault, NoiseBurstFault)):
                for signal_name in sensor_signals:
                    sensor_signals[signal_name] = fault.apply_sensor_reading(
                        signal_name, sensor_signals[signal_name]
                    )
        
        return sensor_signals
    
    def get_ground_truth(self) -> Dict[str, Any]:
        """
        Get ground truth information for all active faults.
        
        Returns:
            Dictionary with fault information and overall severity
        """
        active_faults_info = []
        max_severity = 0.0
        primary_fault = "none"
        
        for fault in self.active_faults:
            if fault.active:
                fault_info = fault.get_ground_truth()
                active_faults_info.append(fault_info)
                severity = fault.get_severity()
                if severity > max_severity:
                    max_severity = severity
                    primary_fault = fault.fault_type
        
        return {
            "fault": primary_fault,
            "severity": max_severity,
            "faults": active_faults_info,
        }
    
    def clear_all_faults(self):
        """Clear all faults and reset models."""
        self.active_faults.clear()
        
        # Reset models to healthy state
        if "pipe" in self.models:
            self.models["pipe"].reset_clogging()
        if "bearing" in self.models:
            self.models["bearing"].reset_wear()
