"""3D pump model renderer using PyVista.

Geometry proportions are driven by the same physical parameters used in the
simulation (Reeh et al. 2023 pump model, Darcy-Weisbach pipe, IEEE PHM / ISO 20816
bearing). References are English literature; see simulator-service/README.md.
"""

import sys
from pathlib import Path

_project_root = Path(__file__).parent.parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from typing import Optional, Dict, Any, Tuple

import pyvista as pv
import numpy as np

from shared_lib.models import TelemetrySignals


def _color_name_to_rgb(name: str) -> Tuple[float, float, float]:
    """Convert color name to (r,g,b) in [0,1] for VTK."""
    try:
        c = pv.Color(name)
        return c.float_rgb
    except Exception:
        pass
    # Fallback for common names
    rgb = {
        "green": (0, 1, 0),
        "yellow": (1, 1, 0),
        "orange": (1, 0.65, 0),
        "red": (1, 0, 0),
        "lightblue": (0.68, 0.85, 1),
        "blue": (0, 0, 1),
        "steelblue": (0.27, 0.51, 0.71),
        "silver": (0.75, 0.75, 0.75),
        "gray": (0.5, 0.5, 0.5),
        "darkgray": (0.41, 0.41, 0.41),
    }
    return rgb.get(name.lower(), (0.5, 0.5, 0.5))


def _default_pump_config() -> Dict[str, Any]:
    """Default config matching main.load_pump_config() for consistent proportions."""
    return {
        "pump": {"nominal_rpm": 2950.0, "nominal_flow_m3h": 100.0, "nominal_head_m": 50.0, "nominal_efficiency": 0.75},
        "pipe": {"pipe_length_m": 100.0, "pipe_diameter_m": 0.2, "pipe_roughness_mm": 0.1, "fitting_loss_coefficient": 2.5, "static_head_m": 10.0},
        "bearing": {"base_vibration_mm_s": 2.0, "base_bearing_temp_c": 45.0, "ambient_temp_c": 25.0},
        "motor": {"voltage_v": 400.0, "motor_efficiency": 0.92, "power_factor": 0.85, "no_load_current_a": 5.0},
    }


class PumpRenderer:
    """
    3D pump system renderer.
    
    Geometry is scaled from the same physical parameters as the simulation:
    - Pipe radius/display length from Darcy-Weisbach pipe (pipe_diameter_m, pipe_length_m).
    - Pump body size from pump nominal flow/head (Reeh et al. 2023 style scaling).
    - Bearing size proportional to pipe (IEEE PHM / ISO 20816 context).
    Colors: vibration (ISO 20816) → pump, temperature → bearings, pressure → pipes.
    """

    # Display scale: 1 m in physics → this many units in 3D (keeps scene ~1–2 units)
    SCENE_SCALE = 2.0
    # Max pipe half-length in 3D (cap so long pipes don't dominate the view)
    PIPE_HALFLEN_CAP = 1.2

    def __init__(self, output_dir: str = "logs/visualizations", config: Optional[Dict[str, Any]] = None):
        """
        Initialize renderer.
        
        Args:
            output_dir: Directory to save screenshots
            config: Optional pump system config (pump/pipe/bearing/motor dicts).
                    If None, uses defaults consistent with load_pump_config().
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.config = config or _default_pump_config()
        
        # Create plotter (off-screen mode for server)
        self.plotter = pv.Plotter(off_screen=True, window_size=[800, 600])
        self.plotter.background_color = "white"
        
        # Create 3D model components from config
        self._create_model()
        
        # Set camera position (fixed view)
        self.plotter.camera.position = (3, 3, 2)
        self.plotter.camera.focal_point = (0, 0, 0)
        self.plotter.camera.up = (0, 0, 1)
    
    def _create_model(self):
        """Create 3D pump model components from physical config."""
        pipe_cfg = self.config.get("pipe", {})
        pump_cfg = self.config.get("pump", {})
        
        D = float(pipe_cfg.get("pipe_diameter_m", 0.2))
        L_pipe_m = float(pipe_cfg.get("pipe_length_m", 100.0))
        Q_N = float(pump_cfg.get("nominal_flow_m3h", 100.0))
        H_N = float(pump_cfg.get("nominal_head_m", 50.0))
        
        s = self.SCENE_SCALE
        # Pipe radius from Darcy-Weisbach pipe diameter (physics-consistent)
        pipe_r = (D / 2.0) * s
        # Display length: proportional to pipe length, capped
        pipe_half_len = min(L_pipe_m * 0.012, self.PIPE_HALFLEN_CAP)
        
        # Pump casing: scale with flow/head (Reeh et al. style nominal point)
        # Proportional to (Q^0.5, H^0.25) roughly; keep aspect ~1:2
        size_factor = (Q_N / 100.0) ** 0.4 * (1.0 + 0.2 * (H_N / 50.0))
        pump_r = max(0.15, 2.0 * pipe_r * size_factor)
        pump_h = 2.0 * pump_r
        
        # Bearings (proportional to pipe/shaft context)
        bearing_r = 0.5 * pipe_r
        
        # Centers from geometry
        pump_center_z = 0.0
        inlet_center_x = -pump_r - pipe_half_len
        outlet_center_x = pump_r + pipe_half_len
        
        # Pump body (main cylinder)
        self.pump_body = pv.Cylinder(
            radius=pump_r,
            height=pump_h,
            center=(0, 0, pump_center_z),
            direction=(0, 0, 1),
        )
        
        # Inlet pipe (horizontal)
        self.inlet_pipe = pv.Cylinder(
            radius=pipe_r,
            height=2.0 * pipe_half_len,
            center=(inlet_center_x, 0, 0),
            direction=(1, 0, 0),
        )
        
        # Outlet pipe (horizontal)
        self.outlet_pipe = pv.Cylinder(
            radius=pipe_r,
            height=2.0 * pipe_half_len,
            center=(outlet_center_x, 0, 0),
            direction=(1, 0, 0),
        )
        
        # Bearing 1 (top) and 2 (bottom)
        self.bearing_top = pv.Sphere(radius=bearing_r, center=(0, 0, pump_center_z + pump_h / 2.0))
        self.bearing_bottom = pv.Sphere(radius=bearing_r, center=(0, 0, pump_center_z - pump_h / 2.0))
        
        # Motor (box on top, proportional to pump)
        m = 0.5 * pump_r
        self.motor = pv.Box(
            bounds=(-m, m, -m, m, pump_center_z + pump_h / 2.0, pump_center_z + pump_h / 2.0 + 2 * m),
        )
        
        # Add all meshes to plotter
        self.plotter.add_mesh(self.pump_body, color="steelblue", name="pump_body")
        self.plotter.add_mesh(self.inlet_pipe, color="silver", name="inlet_pipe")
        self.plotter.add_mesh(self.outlet_pipe, color="silver", name="outlet_pipe")
        self.plotter.add_mesh(self.bearing_top, color="gray", name="bearing_top")
        self.plotter.add_mesh(self.bearing_bottom, color="gray", name="bearing_bottom")
        self.plotter.add_mesh(self.motor, color="darkgray", name="motor")
    
    def _set_actor_color(self, name: str, color_name: str) -> None:
        """Set existing actor color by name (avoids PyVista _actors/replace_actor bug)."""
        ren = self.plotter.renderer
        actors = getattr(ren, "actors", None) or getattr(ren, "_actors", None)
        if not isinstance(actors, dict):
            return
        actor = actors.get(name)
        if actor is not None:
            r, g, b = _color_name_to_rgb(color_name)
            actor.GetProperty().SetColor(r, g, b)
    
    def _get_color_for_vibration(self, vibration_rms: float) -> str:
        """
        Map vibration to color.
        
        ISO 20816 thresholds:
        - < 2.8 mm/s: green (good)
        - 2.8-7.1: yellow (acceptable)
        - 7.1-18: orange (unsatisfactory)
        - > 18: red (unacceptable)
        """
        if vibration_rms < 2.8:
            return "green"
        elif vibration_rms < 7.1:
            return "yellow"
        elif vibration_rms < 18.0:
            return "orange"
        else:
            return "red"
    
    def _get_color_for_temperature(self, temp_c: float) -> str:
        """
        Map temperature to color.
        
        - < 50°C: blue (cool)
        - 50-70°C: green (normal)
        - 70-85°C: yellow (warning)
        - > 85°C: red (critical)
        """
        if temp_c < 50:
            return "lightblue"
        elif temp_c < 70:
            return "green"
        elif temp_c < 85:
            return "yellow"
        else:
            return "red"
    
    def _get_color_for_pressure(self, pressure_bar: float) -> str:
        """
        Map pressure to color.
        
        - Normal: blue
        - High: orange/red
        """
        if pressure_bar < 8:
            return "lightblue"
        elif pressure_bar < 15:
            return "blue"
        elif pressure_bar < 20:
            return "orange"
        else:
            return "red"
    
    def render(self, signals: TelemetrySignals, output_path: Optional[Path] = None) -> Path:
        """
        Render 3D model with colors based on sensor values.
        
        Args:
            signals: TelemetrySignals object
            output_path: Optional output path (defaults to timestamped filename)
            
        Returns:
            Path to saved screenshot
        """
        # Update colors by setting actor properties (avoids add_mesh replace → _actors bug in newer PyVista)
        pump_color = self._get_color_for_vibration(signals.vibration_rms)
        bearing_color = self._get_color_for_temperature(signals.bearing_temp_c)
        pipe_color = self._get_color_for_pressure(signals.pressure_bar)
        self._set_actor_color("pump_body", pump_color)
        self._set_actor_color("bearing_top", bearing_color)
        self._set_actor_color("bearing_bottom", bearing_color)
        self._set_actor_color("inlet_pipe", pipe_color)
        self._set_actor_color("outlet_pipe", pipe_color)
        
        # Generate output filename
        if output_path is None:
            from datetime import datetime
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = self.output_dir / f"pump_{timestamp}.png"
        
        # Render screenshot
        self.plotter.screenshot(str(output_path))
        
        return output_path
    
    def close(self):
        """Close plotter."""
        self.plotter.close()
