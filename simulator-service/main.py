"""Simulator service - generates telemetry data and publishes to MQTT."""

import asyncio
import threading
import time
from typing import Optional, Dict, Any
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel

import sys
from pathlib import Path

# Add project root to path for shared-lib imports
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from shared_lib.config import get_settings
from shared_lib.utils import append_jsonl, ensure_log_dir

from scenarios import ScenarioLoader, ScenarioExecutor
from mqtt import MQTTPublisher


app = FastAPI(
    title="Simulator Service",
    description="Generates telemetry data for powerplant assets",
    version="0.1.0",
)

# Global state
settings = get_settings()
executor: Optional[ScenarioExecutor] = None
mqtt_publisher: Optional[MQTTPublisher] = None
simulation_thread: Optional[threading.Thread] = None
running = False


class ScenarioRequest(BaseModel):
    """Request model for loading scenario."""
    scenario: Dict[str, Any]


class SetpointRequest(BaseModel):
    """Request model for setting setpoints."""
    rpm: Optional[float] = None
    valve_open_pct: Optional[float] = None


def load_pump_config() -> Dict[str, Any]:
    """Load pump configuration from YAML or use defaults."""
    # For now, use default configuration
    # TODO: Load from config/pump_config.yaml if exists
    return {
        "pump": {
            "nominal_rpm": 2950.0,
            "nominal_flow_m3h": 100.0,
            "nominal_head_m": 50.0,
            "nominal_efficiency": 0.75,
        },
        "pipe": {
            "pipe_length_m": 100.0,
            "pipe_diameter_m": 0.2,
            "pipe_roughness_mm": 0.1,
            "fitting_loss_coefficient": 2.5,
            "static_head_m": 10.0,
        },
        "bearing": {
            "base_vibration_mm_s": 2.0,
            "base_bearing_temp_c": 45.0,
            "ambient_temp_c": 25.0,
        },
        "motor": {
            "voltage_v": 400.0,
            "motor_efficiency": 0.92,
            "power_factor": 0.85,
            "no_load_current_a": 5.0,
        },
    }


def simulation_loop():
    """Main simulation loop running in background thread."""
    global executor, mqtt_publisher, running
    
    if not executor or not mqtt_publisher:
        return
    
    frequency_hz = settings.simulator_frequency_hz
    dt = 1.0 / frequency_hz
    
    # Ensure log directory exists
    log_dir = ensure_log_dir(settings.log_dir)
    telemetry_log_path = log_dir / "telemetry.jsonl"
    
    while running and executor:
        try:
            # Execute one simulation step
            telemetry = executor.step(dt)
            
            if telemetry is None:
                # Simulation ended
                running = False
                break
            
            # Publish to MQTT
            try:
                mqtt_publisher.publish_telemetry(telemetry)
            except Exception as e:
                print(f"Warning: MQTT publish error: {e}")
            
            # Log to file
            try:
                append_jsonl(telemetry_log_path, telemetry.model_dump())
            except Exception as e:
                print(f"Warning: Log write error: {e}")
            
            # Sleep to maintain frequency
            time.sleep(dt)
            
        except Exception as e:
            print(f"Error in simulation loop: {e}")
            running = False
            break


@app.on_event("startup")
async def startup_event():
    """Initialize MQTT publisher on startup."""
    global mqtt_publisher
    try:
        mqtt_publisher = MQTTPublisher(settings)
        mqtt_publisher.connect()
    except Exception as e:
        print(f"Warning: Could not connect to MQTT broker: {e}")
        print("Simulator will run but telemetry will not be published")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    global mqtt_publisher, running
    running = False
    if mqtt_publisher:
        mqtt_publisher.disconnect()


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "simulator-service",
        "mqtt_connected": mqtt_publisher.connected if mqtt_publisher else False,
    }


@app.get("/status")
async def status():
    """Get simulator status."""
    global executor, running
    
    if executor:
        status_dict = executor.get_status()
        status_dict["running"] = running
        return status_dict
    else:
        return {
            "status": "stopped",
            "scenario_loaded": False,
            "running": False,
        }


@app.post("/scenario/load")
async def load_scenario(request: ScenarioRequest):
    """Load a scenario."""
    global executor, running
    
    try:
        # Validate scenario
        scenario = ScenarioLoader.load_from_dict(request.scenario)
        
        # Load pump configuration
        pump_config = load_pump_config()
        
        # Create executor
        executor = ScenarioExecutor(scenario, pump_config)
        
        return {
            "status": "loaded",
            "scenario_name": scenario["name"],
            "duration_sec": scenario["duration_sec"],
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/scenario/start")
async def start_scenario():
    """Start scenario execution."""
    global executor, running, simulation_thread
    
    if not executor:
        raise HTTPException(status_code=400, detail="No scenario loaded")
    
    if running:
        raise HTTPException(status_code=400, detail="Simulation already running")
    
    # Start executor
    executor.start()
    running = True
    
    # Start simulation thread
    simulation_thread = threading.Thread(target=simulation_loop, daemon=True)
    simulation_thread.start()
    
    return {"status": "started"}


@app.post("/scenario/stop")
async def stop_scenario():
    """Stop scenario execution."""
    global running, executor
    
    if not running:
        return {"status": "already_stopped"}
    
    running = False
    
    if executor:
        executor.stop()
    
    return {"status": "stopped"}


@app.post("/scenario/reset")
async def reset_scenario():
    """Reset scenario to beginning."""
    global executor, running
    
    running = False
    
    if executor:
        executor.stop()
        executor.current_time = 0.0
        executor.setpoint_index = 0
    
    return {"status": "reset"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
