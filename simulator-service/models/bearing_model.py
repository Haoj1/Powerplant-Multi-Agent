"""
Bearing wear model based on vibration and temperature monitoring.

References:
- IEEE PHM: Vibration-based bearing health indicators
- ISO 20816: Mechanical vibration - Evaluation of machine vibration
- Siegel et al. (2008): Online tracking of bearing wear using wavelet packet decomposition
"""


class BearingModel:
    """
    Bearing wear model with vibration and temperature monitoring.
    
    Models bearing degradation through:
    - Vibration increase with wear (non-linear)
    - Temperature increase due to increased friction
    - ISO 20816 vibration severity classification
    """
    
    def __init__(self, config: dict):
        """
        Initialize bearing model.
        
        Args:
            config: Dictionary with bearing parameters:
                - base_vibration_mm_s: Baseline vibration RMS (mm/s)
                - base_bearing_temp_c: Baseline bearing temperature (°C)
                - ambient_temp_c: Ambient temperature (°C)
        """
        self.base_vibration_rms = config.get("base_vibration_mm_s", 2.0)  # mm/s RMS
        self.base_bearing_temp = config.get("base_bearing_temp_c", 45.0)  # °C
        self.ambient_temp = config.get("ambient_temp_c", 25.0)  # °C
        
        # Wear level: 0.0 = healthy, 1.0 = severe wear/failure
        self.wear_level = 0.0
        
        # ISO 20816 vibration severity thresholds (mm/s RMS)
        # Grade A: < 2.8 (Good)
        # Grade B: 2.8-7.1 (Acceptable)
        # Grade C: 7.1-18 (Unsatisfactory)
        # Grade D: > 18 (Unacceptable)
        self.vibration_thresholds = {
            'A': 2.8,
            'B': 7.1,
            'C': 18.0,
            'D': 45.0
        }
    
    def update_wear(self, wear_rate_per_sec: float, dt: float):
        """
        Update bearing wear level.
        
        Fault mechanism: bearing_wear → d increases linearly over time (chronic fault)
        
        Args:
            wear_rate_per_sec: Wear rate (per second)
            dt: Time step (seconds)
        """
        self.wear_level = min(1.0, self.wear_level + wear_rate_per_sec * dt)
    
    def compute_vibration(self, load_factor: float = 1.0) -> float:
        """
        Compute vibration RMS value based on wear and load.
        
        Based on IEEE PHM: vibration increases non-linearly with bearing wear.
        Model: vibration = base * (1 + d * k1 + d³ * k2) * load_factor
        
        Args:
            load_factor: Load multiplier (1.0 = nominal load)
            
        Returns:
            Vibration RMS (mm/s)
        """
        # Non-linear wear effect: linear term + cubic term (rapid increase near failure)
        wear_effect = 1.0 + self.wear_level * 2.0 + (self.wear_level ** 3) * 5.0
        
        # Load effect: vibration increases with load
        load_effect = 1.0 + 0.2 * (load_factor - 1.0)
        
        vibration_rms = self.base_vibration_rms * wear_effect * load_effect
        
        return max(0.1, vibration_rms)  # Minimum vibration
    
    def compute_bearing_temperature(self, load_factor: float = 1.0) -> float:
        """
        Compute bearing temperature based on wear and load.
        
        Based on thermal balance model:
        - Heat generation ∝ load * friction (increases with wear)
        - Heat dissipation ∝ (T_bearing - T_ambient) / thermal_resistance
        
        Args:
            load_factor: Load multiplier (1.0 = nominal load)
            
        Returns:
            Bearing temperature (°C)
        """
        # Wear increases friction → more heat generation
        # Simplified: heat_gen = load * (1 + wear * k_heat)
        heat_generation_factor = load_factor * (1.0 + self.wear_level * 3.0)
        
        # Wear degrades lubrication → worse heat dissipation (higher thermal resistance)
        thermal_resistance = 0.5 / (1.0 + self.wear_level * 0.5)
        
        # Temperature rise: ΔT = heat_gen * thermal_resistance
        temp_rise = heat_generation_factor * thermal_resistance * 20.0  # Scaling factor
        
        # Base temperature rise (even at healthy condition)
        base_temp_rise = self.base_bearing_temp - self.ambient_temp
        
        bearing_temp = self.ambient_temp + base_temp_rise + temp_rise
        
        return max(self.ambient_temp, bearing_temp)
    
    def get_vibration_severity_grade(self, vibration_rms: float) -> str:
        """
        Get ISO 20816 vibration severity grade.
        
        Args:
            vibration_rms: Vibration RMS value (mm/s)
            
        Returns:
            Severity grade: 'A', 'B', 'C', or 'D'
        """
        if vibration_rms < self.vibration_thresholds['A']:
            return 'A'
        elif vibration_rms < self.vibration_thresholds['B']:
            return 'B'
        elif vibration_rms < self.vibration_thresholds['C']:
            return 'C'
        else:
            return 'D'
    
    def get_wear_level(self) -> float:
        """Get current wear level (0.0 = healthy, 1.0 = failure)."""
        return self.wear_level
    
    def reset_wear(self):
        """Reset wear to healthy state."""
        self.wear_level = 0.0
