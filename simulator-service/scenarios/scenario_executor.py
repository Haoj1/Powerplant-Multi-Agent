"""Scenario execution engine."""

import random
import numpy as np
from typing import Dict, Any, Optional, Callable
from datetime import datetime, timezone

import sys
from pathlib import Path

# Add project root to path for shared-lib imports
project_root = Path(__file__).parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from shared_lib.models import Telemetry, TelemetrySignals, TelemetryTruth, FaultType
from shared_lib.utils import get_current_timestamp

# Import from parent package (simulator-service)
from models import PumpModel, PipeSystemModel, BearingModel, MotorModel
from faults import FaultInjector


class ScenarioExecutor:
    """
    Executes scenario JSON with reproducible results.
    
    Uses fixed seed for reproducibility.
    """
    
    def __init__(self, scenario: Dict[str, Any], pump_config: Dict[str, Any]):
        """
        Initialize scenario executor.
        
        Args:
            scenario: Scenario dictionary
            pump_config: Pump system configuration
        """
        self.scenario = scenario
        self.seed = scenario.get("seed")
        
        # Set random seed for reproducibility
        if self.seed is not None:
            random.seed(self.seed)
            np.random.seed(self.seed)
        
        # Initialize physical models
        self.pump = PumpModel(pump_config.get("pump", {}))
        self.pipe = PipeSystemModel(pump_config.get("pipe", {}))
        self.bearing = BearingModel(pump_config.get("bearing", {}))
        self.motor = MotorModel(pump_config.get("motor", {}))
        
        # Initialize fault injector
        self.fault_injector = FaultInjector()
        self.fault_injector.register_models(
            pump_model=self.pump,
            pipe_model=self.pipe,
            bearing_model=self.bearing,
            motor_model=self.motor
        )
        
        # Load faults from scenario
        for fault_def in scenario.get("faults", []):
            self.fault_injector.inject_fault(
                fault_def["type"],
                fault_def["start_time_sec"],
                fault_def.get("params", {})
            )
        
        # Current state
        self.current_time = 0.0
        self.rpm = scenario["initial_conditions"].get("rpm", 2950.0)
        self.valve_open_pct = scenario["initial_conditions"].get("valve_open_pct", 60.0)
        self.running = False
        
        # Setpoints (time-ordered)
        self.setpoints = sorted(
            scenario.get("setpoints", []),
            key=lambda x: x["time_sec"]
        )
        self.setpoint_index = 0
    
    def step(self, dt: float) -> Optional[Telemetry]:
        """
        Execute one simulation step.
        
        Args:
            dt: Time step (seconds)
            
        Returns:
            Telemetry object or None if simulation ended
        """
        if not self.running:
            return None
        
        # Check if scenario ended
        if self.current_time >= self.scenario["duration_sec"]:
            self.running = False
            return None
        
        # Update setpoints
        self._update_setpoints()
        
        # Update faults
        self.fault_injector.update_faults(self.current_time, dt)
        
        # Apply valve faults
        valve_command = self.valve_open_pct
        valve_actual = self.fault_injector.apply_valve_faults(valve_command)
        
        # Solve operating point: H_pump(Q) = H_system(Q)
        Q, H = self.pump.solve_operating_point(
            self.rpm,
            valve_actual,
            self.pipe.compute_system_head
        )
        
        # Compute pump efficiency and power
        eta = self.pump.compute_efficiency(Q, self.rpm)
        P_shaft = self.pump.compute_power(Q, H, eta)
        
        # Compute motor current
        I_motor = self.motor.compute_current(P_shaft)
        
        # Compute bearing signals
        load_factor = P_shaft / 10.0  # Normalize load (simplified)
        vibration_rms = self.bearing.compute_vibration(load_factor)
        bearing_temp = self.bearing.compute_bearing_temperature(load_factor)
        
        # Compute fluid temperature (simplified: increases with power)
        fluid_temp = 25.0 + (P_shaft * 0.5)  # Base temp + power effect
        
        # True physical signals
        true_signals = {
            "pressure_bar": H * 0.1,  # 1 bar ≈ 10 m head
            "flow_m3h": Q,
            "temp_c": fluid_temp,
            "bearing_temp_c": bearing_temp,
            "vibration_rms": vibration_rms,
            "rpm": self.rpm,
            "motor_current_a": I_motor,
            "valve_open_pct": valve_actual,
        }
        
        # Apply sensor faults
        sensor_signals = self.fault_injector.apply_sensor_faults(true_signals)
        
        # Get ground truth
        truth_dict = self.fault_injector.get_ground_truth()
        fault_type = FaultType[truth_dict["fault"].upper()] if truth_dict["fault"] != "none" else FaultType.NONE
        
        # Create telemetry
        telemetry = Telemetry(
            ts=get_current_timestamp(),
            plant_id="plant01",
            asset_id="pump01",
            signals=TelemetrySignals(
                pressure_bar=sensor_signals["pressure_bar"],
                flow_m3h=sensor_signals["flow_m3h"],
                temp_c=sensor_signals["temp_c"],
                bearing_temp_c=sensor_signals["bearing_temp_c"],
                vibration_rms=sensor_signals["vibration_rms"],
                rpm=sensor_signals["rpm"],
                motor_current_a=sensor_signals["motor_current_a"],
                valve_open_pct=sensor_signals["valve_open_pct"],
            ),
            truth=TelemetryTruth(
                fault=fault_type,
                severity=truth_dict["severity"],
            ),
        )
        
        # Advance time
        self.current_time += dt
        
        return telemetry
    
    def _update_setpoints(self):
        """Update setpoints based on current time."""
        while (self.setpoint_index < len(self.setpoints) and
               self.current_time >= self.setpoints[self.setpoint_index]["time_sec"]):
            setpoint = self.setpoints[self.setpoint_index]
            
            if "rpm" in setpoint:
                self.rpm = setpoint["rpm"]
            if "valve_open_pct" in setpoint:
                self.valve_open_pct = setpoint["valve_open_pct"]
            
            self.setpoint_index += 1
    
    def start(self):
        """Start scenario execution."""
        self.running = True
        self.current_time = 0.0
        self.setpoint_index = 0
        
        # Reset models
        self.fault_injector.clear_all_faults()
        
        # Re-inject faults
        for fault_def in self.scenario.get("faults", []):
            self.fault_injector.inject_fault(
                fault_def["type"],
                fault_def["start_time_sec"],
                fault_def.get("params", {})
            )
    
    def stop(self):
        """Stop scenario execution."""
        self.running = False
    
    def get_status(self) -> Dict[str, Any]:
        """Get current execution status."""
        return {
            "running": self.running,
            "current_time_sec": self.current_time,
            "duration_sec": self.scenario["duration_sec"],
            "progress_pct": (self.current_time / self.scenario["duration_sec"] * 100) if self.scenario["duration_sec"] > 0 else 0.0,
            "rpm": self.rpm,
            "valve_open_pct": self.valve_open_pct,
        }
