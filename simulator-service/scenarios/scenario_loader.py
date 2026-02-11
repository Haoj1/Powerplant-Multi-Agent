"""Scenario JSON loader and validator."""

import json
from typing import Dict, Any
from pathlib import Path


class ScenarioLoader:
    """Load and validate scenario JSON files."""
    
    @staticmethod
    def load_from_file(file_path: str) -> Dict[str, Any]:
        """
        Load scenario from JSON file.
        
        Args:
            file_path: Path to scenario JSON file
            
        Returns:
            Scenario dictionary
        """
        with open(file_path, 'r', encoding='utf-8') as f:
            scenario = json.load(f)
        return ScenarioLoader.validate(scenario)
    
    @staticmethod
    def load_from_dict(scenario_dict: Dict[str, Any]) -> Dict[str, Any]:
        """
        Load scenario from dictionary.
        
        Args:
            scenario_dict: Scenario dictionary
            
        Returns:
            Validated scenario dictionary
        """
        return ScenarioLoader.validate(scenario_dict)
    
    @staticmethod
    def validate(scenario: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate scenario structure.
        
        Args:
            scenario: Scenario dictionary
            
        Returns:
            Validated scenario dictionary
            
        Raises:
            ValueError: If scenario is invalid
        """
        # Required fields
        required_fields = ["name", "duration_sec"]
        for field in required_fields:
            if field not in scenario:
                raise ValueError(f"Missing required field: {field}")
        
        # Set defaults
        scenario.setdefault("version", "1.0")
        scenario.setdefault("seed", None)
        scenario.setdefault("initial_conditions", {})
        scenario.setdefault("faults", [])
        scenario.setdefault("setpoints", [])
        
        # Validate initial conditions
        initial = scenario["initial_conditions"]
        initial.setdefault("rpm", 2950.0)
        initial.setdefault("valve_open_pct", 60.0)
        
        # Validate faults
        for fault in scenario["faults"]:
            if "type" not in fault:
                raise ValueError("Fault missing 'type' field")
            if "start_time_sec" not in fault:
                raise ValueError("Fault missing 'start_time_sec' field")
            fault.setdefault("params", {})
        
        # Validate setpoints
        for setpoint in scenario["setpoints"]:
            if "time_sec" not in setpoint:
                raise ValueError("Setpoint missing 'time_sec' field")
        
        return scenario
