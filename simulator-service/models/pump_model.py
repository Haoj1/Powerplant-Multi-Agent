"""
Pump physical model based on Reeh et al. (2023).

Reference:
Reeh, N., Manthei, G., & Klar, P. J. (2023). Physical Modelling of the Set of 
Performance Curves for Radial Centrifugal Pumps to Determine the Flow Rate.
Applied System Innovation, 6(6), 111.
"""

import math
from typing import Tuple


class PumpModel:
    """
    Physical pump model using Euler equation and affinity laws.
    
    Based on Reeh et al. (2023) physical modeling approach.
    Uses affinity laws for variable-speed operation: Q ∝ n, H ∝ n², P ∝ n³
    """
    
    def __init__(self, config: dict):
        """
        Initialize pump model with configuration.
        
        Args:
            config: Dictionary with pump parameters:
                - nominal_rpm: Rated speed (rpm)
                - nominal_flow_m3h: Rated flow rate (m³/h)
                - nominal_head_m: Rated head (m)
                - nominal_efficiency: Rated efficiency (0-1)
                - specific_speed: Specific speed n_q (optional)
        """
        self.n_N = config.get("nominal_rpm", 2950.0)
        self.Q_N = config.get("nominal_flow_m3h", 100.0)
        self.H_N = config.get("nominal_head_m", 50.0)
        self.eta_N = config.get("nominal_efficiency", 0.75)
        
        # Compute H-Q curve coefficients (simplified quadratic model)
        # H(Q) = H_0 - a * Q², where H_0 is shutoff head
        # At rated point: H_N = H_0 - a * Q_N²
        # Assume shutoff head is 1.2 * rated head (typical for centrifugal pumps)
        self.H_shutoff = self.H_N * 1.2
        self.a_coeff = (self.H_shutoff - self.H_N) / (self.Q_N ** 2)
    
    def compute_head_flow_curve(self, rpm: float, valve_open_pct: float) -> Tuple[float, float]:
        """
        Compute H-Q curve parameters for given speed and valve position.
        
        Based on Reeh et al. (2023) and affinity laws.
        
        Args:
            rpm: Pump speed (rpm)
            valve_open_pct: Valve opening percentage (0-100)
            
        Returns:
            Tuple of (H_shutoff, Q_max) where:
            - H_shutoff: Head at zero flow (m)
            - Q_max: Maximum flow rate at this speed/valve setting (m³/h)
        """
        # Affinity law: Q ∝ n, H ∝ n²
        n_ratio = rpm / self.n_N
        
        # Valve limits maximum flow
        valve_factor = valve_open_pct / 100.0
        
        # Scaled shutoff head
        H_shutoff_scaled = self.H_shutoff * (n_ratio ** 2)
        
        # Maximum flow at this speed and valve setting
        Q_max = self.Q_N * n_ratio * valve_factor
        
        return H_shutoff_scaled, Q_max
    
    def compute_head(self, Q: float, rpm: float) -> float:
        """
        Compute pump head for given flow rate and speed.
        
        H(Q) = H_shutoff(n) - a * (Q/Q_N)² * H_N
        
        Args:
            Q: Flow rate (m³/h)
            rpm: Pump speed (rpm)
            
        Returns:
            Pump head (m)
        """
        n_ratio = rpm / self.n_N
        H_shutoff_scaled = self.H_shutoff * (n_ratio ** 2)
        
        # Quadratic H-Q relationship
        Q_ratio = Q / self.Q_N if self.Q_N > 0 else 0
        H = H_shutoff_scaled - self.a_coeff * (Q ** 2)
        
        return max(0.0, H)  # Head cannot be negative
    
    def compute_efficiency(self, Q: float, rpm: float) -> float:
        """
        Compute pump efficiency.
        
        Based on Reeh et al. (2023) efficiency model.
        Efficiency curve is typically parabolic: η(Q) = η_max * [1 - (Q-Q_opt)²/Q_opt²]
        
        Args:
            Q: Flow rate (m³/h)
            rpm: Pump speed (rpm)
            
        Returns:
            Pump efficiency (0-1)
        """
        n_ratio = rpm / self.n_N
        Q_opt = self.Q_N * n_ratio  # Best efficiency point flow (scales with speed)
        
        if Q_opt <= 0:
            return 0.3  # Minimum efficiency
        
        # Parabolic efficiency curve centered at Q_opt
        Q_deviation = (Q - Q_opt) / Q_opt
        eta = self.eta_N * (1 - Q_deviation ** 2)
        
        # Limit efficiency to reasonable range
        return max(0.3, min(eta, self.eta_N))
    
    def compute_power(self, Q: float, H: float, eta: float) -> float:
        """
        Compute pump shaft power.
        
        P = ρ * g * Q * H / η
        
        Args:
            Q: Flow rate (m³/h)
            H: Head (m)
            eta: Efficiency (0-1)
            
        Returns:
            Shaft power (kW)
        """
        if eta <= 0:
            return 0.0
        
        rho = 1000.0  # Water density (kg/m³)
        g = 9.81      # Gravity (m/s²)
        
        # Convert Q from m³/h to m³/s
        Q_m3s = Q / 3600.0
        
        # Hydraulic power: P_hyd = ρ * g * Q * H
        P_hydraulic = rho * g * Q_m3s * H  # Watts
        
        # Shaft power: P_shaft = P_hyd / η
        P_shaft = P_hydraulic / eta  # Watts
        
        return P_shaft / 1000.0  # Convert to kW
    
    def solve_operating_point(
        self, 
        rpm: float, 
        valve_open_pct: float, 
        system_head_func
    ) -> Tuple[float, float]:
        """
        Solve for operating point where pump head equals system head.
        
        Uses iterative method to find Q where H_pump(Q) = H_system(Q).
        
        Args:
            rpm: Pump speed (rpm)
            valve_open_pct: Valve opening (0-100)
            system_head_func: Function Q -> H_system (m)
            
        Returns:
            Tuple of (Q, H) at operating point
        """
        _, Q_max = self.compute_head_flow_curve(rpm, valve_open_pct)
        
        # Binary search for operating point
        Q_low = 0.0
        Q_high = Q_max
        tolerance = 0.01  # m³/h
        
        for _ in range(50):  # Max iterations
            Q_mid = (Q_low + Q_high) / 2.0
            H_pump = self.compute_head(Q_mid, rpm)
            H_system = system_head_func(Q_mid)
            
            diff = H_pump - H_system
            
            if abs(diff) < tolerance:
                return Q_mid, H_pump
            
            if diff > 0:
                Q_low = Q_mid
            else:
                Q_high = Q_mid
        
        # Return best estimate
        Q_final = (Q_low + Q_high) / 2.0
        H_final = self.compute_head(Q_final, rpm)
        return Q_final, H_final
