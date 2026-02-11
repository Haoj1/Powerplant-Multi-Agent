"""
Pipe system resistance model using Darcy-Weisbach equation.

Reference:
Darcy-Weisbach equation: h_f = f * (L/D) * (V²/(2g))
Standard fluid mechanics textbook (e.g., White, F.M. Fluid Mechanics)
"""

import math
from typing import Callable


class PipeSystemModel:
    """
    Pipe system resistance model based on Darcy-Weisbach equation.
    
    Models system head loss including pipe friction and fittings.
    Supports clogging fault through increased resistance.
    """
    
    def __init__(self, config: dict):
        """
        Initialize pipe system model.
        
        Args:
            config: Dictionary with pipe parameters:
                - pipe_length_m: Pipe length (m)
                - pipe_diameter_m: Pipe diameter (m)
                - pipe_roughness_mm: Pipe roughness (mm)
                - fitting_loss_coefficient: Sum of K values for fittings
                - static_head_m: Static head (elevation difference) (m)
        """
        self.L = config.get("pipe_length_m", 100.0)
        self.D = config.get("pipe_diameter_m", 0.2)  # 200mm diameter
        self.epsilon = config.get("pipe_roughness_mm", 0.1) / 1000.0  # Convert to m
        self.K_fittings = config.get("fitting_loss_coefficient", 2.5)
        self.H_static = config.get("static_head_m", 10.0)
        
        # Compute base resistance coefficient
        self.R_base = self._compute_base_resistance()
        
        # Current resistance (can be modified by clogging fault)
        self.R_current = self.R_base
        
        # Clogging factor (1.0 = no clogging, >1.0 = clogged)
        self.clogging_factor = 1.0
    
    def _compute_base_resistance(self) -> float:
        """
        Compute base system resistance coefficient.
        
        Based on Darcy-Weisbach equation.
        System head: H = R * Q² + H_static
        
        Returns:
            Resistance coefficient R (s²/m⁵)
        """
        A = math.pi * (self.D / 2.0) ** 2  # Pipe cross-sectional area (m²)
        g = 9.81  # Gravity (m/s²)
        
        # Friction factor (simplified: assume turbulent flow, f ≈ 0.02)
        # For more accuracy, could use Colebrook-White equation or Moody diagram
        f = 0.02
        
        # Pipe friction resistance: R_pipe = f * (L/D) / (2*g*A²)
        R_pipe = f * (self.L / self.D) / (2 * g * A ** 2)
        
        # Fittings resistance: R_fittings = K / (2*g*A²)
        R_fittings = self.K_fittings / (2 * g * A ** 2)
        
        return R_pipe + R_fittings
    
    def compute_system_head(self, Q: float) -> float:
        """
        Compute system head required for given flow rate.
        
        H_system = R * Q² + H_static
        
        Args:
            Q: Flow rate (m³/h)
            
        Returns:
            System head (m)
        """
        Q_m3s = Q / 3600.0  # Convert m³/h to m³/s
        H_dynamic = self.R_current * (Q_m3s ** 2)
        return H_dynamic + self.H_static
    
    def set_clogging_resistance(self, clogging_factor: float):
        """
        Set clogging resistance factor.
        
        Fault mechanism: clogging → effective diameter decreases → resistance increases
        R_clogged = R_base * clogging_factor
        
        Args:
            clogging_factor: Resistance multiplier (1.0 = no clogging, >1.0 = clogged)
        """
        self.clogging_factor = max(1.0, clogging_factor)
        self.R_current = self.R_base * self.clogging_factor
    
    def get_resistance(self) -> float:
        """Get current resistance coefficient."""
        return self.R_current
    
    def reset_clogging(self):
        """Reset clogging to normal (no fault)."""
        self.clogging_factor = 1.0
        self.R_current = self.R_base
