"""
Motor current model based on shaft power.

Standard electrical engineering: P = √3 * U * I * cos(φ) * η
"""

import math


class MotorModel:
    """
    Motor current model based on shaft power.
    
    Computes motor current from shaft power using standard electrical equations.
    """
    
    def __init__(self, config: dict):
        """
        Initialize motor model.
        
        Args:
            config: Dictionary with motor parameters:
                - voltage_v: Line voltage (V)
                - motor_efficiency: Motor efficiency (0-1)
                - power_factor: Power factor cos(φ) (0-1)
                - no_load_current_a: No-load current (A)
        """
        self.U = config.get("voltage_v", 400.0)  # 400V three-phase
        self.eta_motor = config.get("motor_efficiency", 0.92)
        self.cos_phi = config.get("power_factor", 0.85)
        self.I_no_load = config.get("no_load_current_a", 5.0)
    
    def compute_current(self, P_shaft_kW: float) -> float:
        """
        Compute motor current from shaft power.
        
        P_electrical = P_shaft / η_motor
        I = P_electrical / (√3 * U * cos(φ))
        
        Args:
            P_shaft_kW: Shaft power (kW)
            
        Returns:
            Motor current (A)
        """
        if P_shaft_kW <= 0:
            return self.I_no_load
        
        # Electrical power required
        P_electrical_kW = P_shaft_kW / self.eta_motor
        
        # Current from three-phase power equation
        I_load = (P_electrical_kW * 1000.0) / (math.sqrt(3) * self.U * self.cos_phi)
        
        # Total current = no-load + load current
        I_total = self.I_no_load + I_load
        
        return max(self.I_no_load, I_total)
