"""Simulator service - generates telemetry data and publishes to MQTT."""

import sys
from pathlib import Path

# Add project root and simulator-service to path for imports
_project_root = Path(__file__).parent.parent
_simulator_dir = Path(__file__).parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))
if str(_simulator_dir) not in sys.path:
    sys.path.insert(0, str(_simulator_dir))

# Load .env from project root so API keys are found regardless of cwd
try:
    from dotenv import load_dotenv
    _env_path = _project_root / ".env"
    if _env_path.exists():
        load_dotenv(_env_path)
except Exception:
    pass

import asyncio
import threading
import time
from typing import Optional, Dict, Any, Tuple

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from shared_lib.config import get_settings
from shared_lib.utils import append_jsonl, ensure_log_dir

try:
    from shared_lib import db as shared_db
except ImportError:
    shared_db = None

from scenarios import ScenarioLoader, ScenarioExecutor
from mqtt import MQTTPublisher
from mqtt.vision_publisher import VisionPublisher
from visualization import PumpRenderer
from shared_lib.models import VisionImageReady
from shared_lib.utils import get_current_timestamp


app = FastAPI(
    title="Simulator Service",
    description="Generates telemetry data for powerplant assets",
    version="0.1.0",
)

# Global state
settings = get_settings()
executor: Optional[ScenarioExecutor] = None
mqtt_publisher: Optional[MQTTPublisher] = None
vision_publisher: Optional[VisionPublisher] = None
renderer: Optional[PumpRenderer] = None
simulation_thread: Optional[threading.Thread] = None
running = False
last_vision_time = 0.0
current_sim_time = 0.0
# Vision must run on main thread (macOS PyVista/VTK); sim thread only enqueues.
_vision_pending: Optional[Tuple[Any, float]] = None  # (telemetry, sim_time) or None
_vision_lock = threading.Lock()


class ScenarioRequest(BaseModel):
    """Request model for loading scenario."""
    scenario: Dict[str, Any]


def load_pump_config() -> Dict[str, Any]:
    """Load pump configuration (defaults)."""
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
    global executor, mqtt_publisher, vision_publisher, renderer, running, last_vision_time, _vision_pending

    if not executor:
        return

    frequency_hz = settings.simulator_frequency_hz
    dt = 1.0 / frequency_hz
    vision_interval = settings.vision_frequency_sec

    log_dir = ensure_log_dir(settings.log_dir)
    telemetry_log_path = log_dir / "telemetry.jsonl"
    global current_sim_time
    current_sim_time = 0.0

    while running and executor:
        try:
            telemetry = executor.step(dt)

            if telemetry is None:
                running = False
                break

            current_sim_time += dt

            # Publish telemetry
            if mqtt_publisher and mqtt_publisher.connected:
                try:
                    mqtt_publisher.publish_telemetry(telemetry)
                except Exception as e:
                    print(f"Warning: MQTT publish error: {e}")

            # Log telemetry (JSONL kept as-is)
            try:
                append_jsonl(telemetry_log_path, telemetry.model_dump())
            except Exception as e:
                print(f"Warning: Log write error: {e}")
            # SQLite (for querying/dashboard)
            if shared_db:
                try:
                    s = telemetry.signals
                    t = telemetry.truth
                    shared_db.insert_telemetry(
                        ts=str(telemetry.ts), plant_id=telemetry.plant_id, asset_id=telemetry.asset_id,
                        pressure_bar=s.pressure_bar, flow_m3h=s.flow_m3h, temp_c=s.temp_c,
                        bearing_temp_c=s.bearing_temp_c, vibration_rms=s.vibration_rms, rpm=s.rpm,
                        motor_current_a=s.motor_current_a, valve_open_pct=s.valve_open_pct,
                        fault=t.fault.value if hasattr(t.fault, "value") else str(t.fault), severity=t.severity,
                    )
                except Exception as e:
                    print(f"Warning: DB telemetry write error: {e}")

            # Enqueue vision work for main thread (macOS: PyVista/VTK must run on main thread)
            if (renderer and vision_publisher and
                current_sim_time - last_vision_time >= vision_interval):
                with _vision_lock:
                    _vision_pending = (telemetry, current_sim_time)
                last_vision_time = current_sim_time

            time.sleep(dt)

        except Exception as e:
            print(f"Error in simulation loop: {e}")
            running = False
            break


def _run_vision_pipeline(telemetry):  # runs on main thread (required by PyVista on macOS)
    """Render 3D and publish image path only. No VLM here; agents call VLM when they need to reason."""
    global vision_publisher, renderer
    if not (renderer and vision_publisher):
        return
    try:
        image_path = renderer.render(telemetry.signals)
        msg = VisionImageReady(
            ts=get_current_timestamp(),
            plant_id=telemetry.plant_id,
            asset_id=telemetry.asset_id,
            image_path=str(image_path),
        )
        vision_publisher.publish_image_ready(msg)
        if shared_db:
            try:
                shared_db.insert_vision_image(
                    ts=str(msg.ts), plant_id=telemetry.plant_id, asset_id=telemetry.asset_id,
                    image_path=str(image_path),
                )
            except Exception as e:
                print(f"Warning: DB vision_images write error: {e}")
        print(f"[Simulator] Vision image saved and path published to vision/{telemetry.asset_id}")
    except Exception as e:
        import traceback
        print(f"Warning: Vision render/publish error: {e}")
        traceback.print_exc()


async def _vision_worker():
    """Background task: run vision pipeline on main thread when work is enqueued."""
    global _vision_pending
    while True:
        await asyncio.sleep(1.0)
        with _vision_lock:
            data = _vision_pending
            _vision_pending = None
        if data:
            telemetry, _ = data
            _run_vision_pipeline(telemetry)


@app.on_event("startup")
async def startup_event():
    """Initialize MQTT publisher and renderer. VLM is not used here; agents call VLM when needed."""
    global mqtt_publisher, vision_publisher, renderer
    
    # Initialize MQTT publisher
    try:
        mqtt_publisher = MQTTPublisher(settings)
        mqtt_publisher.connect()
    except Exception as e:
        print(f"Warning: Could not connect to MQTT broker: {e}")
        print("Simulator will run but telemetry will not be published")
        mqtt_publisher = None
    
    # Initialize vision publisher (uses same MQTT client)
    if mqtt_publisher and mqtt_publisher.connected:
        vision_publisher = VisionPublisher(
            mqtt_client=mqtt_publisher.client,
            vision_topic_prefix=settings.mqtt_topic_vision,
            log_dir=settings.log_dir,
        )
    
    # Initialize 3D renderer (geometry from same physical config as simulation)
    try:
        pump_config = load_pump_config()
        renderer = PumpRenderer(
            output_dir=f"{settings.log_dir}/visualizations",
            config=pump_config,
        )
        print("[Simulator] 3D renderer initialized (image path published to vision/*; VLM is called by agents when needed)")
    except Exception as e:
        print(f"Warning: Could not initialize 3D renderer: {e}")
        renderer = None

    # Start vision worker (render only; no VLM in simulator)
    asyncio.create_task(_vision_worker())


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    global mqtt_publisher, renderer, running
    running = False
    if mqtt_publisher:
        mqtt_publisher.disconnect()
    if renderer:
        renderer.close()


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
        scenario = ScenarioLoader.load_from_dict(request.scenario)
        pump_config = load_pump_config()
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

    executor.start()
    running = True

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
    global executor, running, last_vision_time, current_sim_time

    running = False
    if executor:
        executor.stop()
        executor.current_time = 0.0
        executor.setpoint_index = 0
    
    last_vision_time = 0.0
    current_sim_time = 0.0

    return {"status": "reset"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
