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
from datetime import datetime, timezone
from typing import Optional, Dict, Any, Tuple

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

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
from shared_lib.models import VisionImageReady, AlertEvent, AlertDetail, Severity
from shared_lib.utils import get_current_timestamp


app = FastAPI(
    title="Simulator Service",
    description="Generates telemetry data for powerplant assets",
    version="0.1.0",
)

# Global state
settings = get_settings()
executors: Dict[str, ScenarioExecutor] = {}  # asset_id -> executor
mqtt_publisher: Optional[MQTTPublisher] = None
vision_publisher: Optional[VisionPublisher] = None
renderer: Optional[PumpRenderer] = None
simulation_threads: Dict[str, threading.Thread] = {}  # asset_id -> thread
running: Dict[str, bool] = {}  # asset_id -> running status
last_vision_time: Dict[str, float] = {}  # asset_id -> last vision time
current_sim_time: Dict[str, float] = {}  # asset_id -> current sim time
# Vision must run on main thread (macOS PyVista/VTK); sim thread only enqueues.
_vision_pending: Optional[Tuple[Any, float]] = None  # (telemetry, sim_time) or None
_vision_lock = threading.Lock()
_executors_lock = threading.Lock()  # Lock for executors dict


class ScenarioRequest(BaseModel):
    """Request model for loading scenario."""
    scenario: Dict[str, Any]


class TriggerAlertRequest(BaseModel):
    """Request model for manually triggering an alert."""
    asset_id: str = Field(..., description="Asset ID (e.g., pump01)")
    plant_id: str = Field(default="plant01", description="Plant ID")
    signal: str = Field(..., description="Signal name (e.g., vibration_rms, bearing_temp_c)")
    severity: str = Field(default="warning", description="Severity: warning or critical")
    score: float = Field(default=3.5, description="Anomaly score")
    method: str = Field(default="manual", description="Detection method")
    evidence: Dict[str, Any] = Field(default_factory=dict, description="Additional evidence")


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


def simulation_loop(asset_id: str):
    """Main simulation loop running in background thread for a specific asset."""
    global executors, mqtt_publisher, vision_publisher, renderer, running, last_vision_time, _vision_pending, current_sim_time

    with _executors_lock:
        executor = executors.get(asset_id)
        if not executor:
            return

    frequency_hz = settings.simulator_frequency_hz
    dt = 1.0 / frequency_hz
    vision_interval = settings.vision_frequency_sec
    db_interval = getattr(settings, "db_telemetry_interval_sec", 0.0) or 0.0

    log_dir = ensure_log_dir(settings.log_dir)
    telemetry_log_path = log_dir / "telemetry.jsonl"
    
    if asset_id not in current_sim_time:
        current_sim_time[asset_id] = 0.0
    if asset_id not in last_vision_time:
        last_vision_time[asset_id] = 0.0
    
    last_db_telemetry_time = -1.0

    while running.get(asset_id, False) and executor:
        try:
            telemetry = executor.step(dt)

            if telemetry is None:
                running = False
                break

            current_sim_time[asset_id] += dt

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
            # SQLite (for querying/dashboard); optional sampling when db_telemetry_interval_sec > 0
            if shared_db and (db_interval <= 0 or current_sim_time[asset_id] - last_db_telemetry_time >= db_interval):
                if db_interval > 0:
                    last_db_telemetry_time = current_sim_time[asset_id]
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
                current_sim_time[asset_id] - last_vision_time[asset_id] >= vision_interval):
                with _vision_lock:
                    _vision_pending = (telemetry, current_sim_time[asset_id])
                last_vision_time[asset_id] = current_sim_time[asset_id]

            time.sleep(dt)

        except Exception as e:
            print(f"Error in simulation loop for {asset_id}: {e}")
            running[asset_id] = False
            break
    
    # Cleanup when loop exits
    with _executors_lock:
        if asset_id in simulation_threads:
            del simulation_threads[asset_id]


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
    global mqtt_publisher, renderer, running, executors
    running.clear()
    with _executors_lock:
        for executor in executors.values():
            executor.stop()
        executors.clear()
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
async def status(asset_id: Optional[str] = None):
    """Get simulator status for all assets or a specific asset."""
    global executors, running, current_sim_time
    
    with _executors_lock:
        if asset_id:
            # Single asset status
            executor = executors.get(asset_id)
            if executor:
                status_dict = executor.get_status()
                status_dict["running"] = running.get(asset_id, False)
                status_dict["asset_id"] = asset_id
                status_dict["current_time"] = current_sim_time.get(asset_id, 0.0)
                return status_dict
            else:
                return {
                    "status": "not_loaded",
                    "asset_id": asset_id,
                    "scenario_loaded": False,
                    "running": False,
                }
        else:
            # All assets status
            all_status = []
            for aid, executor in executors.items():
                status_dict = executor.get_status()
                status_dict["asset_id"] = aid
                status_dict["running"] = running.get(aid, False)
                status_dict["current_time"] = current_sim_time.get(aid, 0.0)
                all_status.append(status_dict)
            return {
                "assets": all_status,
                "total_assets": len(executors),
            }


@app.post("/scenario/load")
async def load_scenario(request: ScenarioRequest):
    """Load a scenario for an asset. Asset ID is read from scenario JSON."""
    global executors, running

    try:
        scenario = ScenarioLoader.load_from_dict(request.scenario)
        asset_id = scenario.get("asset_id", "pump01")
        plant_id = scenario.get("plant_id", "plant01")
        
        # Stop existing scenario for this asset if running
        if asset_id in running and running[asset_id]:
            running[asset_id] = False
            if asset_id in executors:
                executors[asset_id].stop()
        
        pump_config = load_pump_config()
        executor = ScenarioExecutor(scenario, pump_config)
        
        with _executors_lock:
            executors[asset_id] = executor
            if asset_id not in current_sim_time:
                current_sim_time[asset_id] = 0.0
            if asset_id not in last_vision_time:
                last_vision_time[asset_id] = 0.0

        return {
            "status": "loaded",
            "asset_id": asset_id,
            "plant_id": plant_id,
            "scenario_name": scenario["name"],
            "duration_sec": scenario["duration_sec"],
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/scenario/start/{asset_id}")
async def start_scenario(asset_id: str):
    """Start scenario execution for a specific asset."""
    global executors, running, simulation_threads

    with _executors_lock:
        executor = executors.get(asset_id)
        if not executor:
            raise HTTPException(status_code=404, detail=f"No scenario loaded for asset {asset_id}")

        if running.get(asset_id, False):
            raise HTTPException(status_code=400, detail=f"Simulation already running for asset {asset_id}")

        executor.start()
        running[asset_id] = True

        thread = threading.Thread(target=simulation_loop, args=(asset_id,), daemon=True)
        thread.start()
        simulation_threads[asset_id] = thread

    return {"status": "started", "asset_id": asset_id}


@app.post("/scenario/stop/{asset_id}")
async def stop_scenario(asset_id: str):
    """Stop scenario execution for a specific asset."""
    global running, executors

    with _executors_lock:
        if not running.get(asset_id, False):
            return {"status": "already_stopped", "asset_id": asset_id}

        running[asset_id] = False
        if asset_id in executors:
            executors[asset_id].stop()

    return {"status": "stopped", "asset_id": asset_id}


@app.post("/scenario/stop")
async def stop_all_scenarios():
    """Stop all running scenarios."""
    global running, executors

    with _executors_lock:
        stopped = []
        for asset_id in list(running.keys()):
            if running[asset_id]:
                running[asset_id] = False
                if asset_id in executors:
                    executors[asset_id].stop()
                stopped.append(asset_id)

    return {"status": "stopped", "stopped_assets": stopped}


@app.post("/scenario/reset/{asset_id}")
async def reset_scenario(asset_id: str):
    """Reset scenario to beginning for a specific asset."""
    global executors, running, last_vision_time, current_sim_time

    with _executors_lock:
        executor = executors.get(asset_id)
        if not executor:
            raise HTTPException(status_code=404, detail=f"No scenario loaded for asset {asset_id}")

        running[asset_id] = False
        executor.stop()
        executor.current_time = 0.0
        executor.setpoint_index = 0
        
        last_vision_time[asset_id] = 0.0
        current_sim_time[asset_id] = 0.0

    return {"status": "reset", "asset_id": asset_id}


@app.post("/alert/trigger")
async def trigger_alert(request: TriggerAlertRequest):
    """
    Manually trigger an alert for testing purposes.
    Publishes alert to MQTT topic alerts/{asset_id} for Agent A to process.
    """
    global mqtt_publisher
    
    if not mqtt_publisher or not mqtt_publisher.connected:
        raise HTTPException(status_code=503, detail="MQTT broker not connected")
    
    try:
        # Create alert event
        severity_enum = Severity.WARNING if request.severity.lower() == "warning" else Severity.CRITICAL
        
        alert = AlertEvent(
            ts=datetime.now(timezone.utc),
            plant_id=request.plant_id,
            asset_id=request.asset_id,
            severity=severity_enum,
            alerts=[
                AlertDetail(
                    signal=request.signal,
                    score=request.score,
                    method=request.method,
                    window_sec=0,  # Manual trigger
                    evidence=request.evidence,
                )
            ],
        )
        
        # Publish to MQTT (same topic format as Agent A uses)
        from mqtt import AlertPublisher
        alert_publisher = AlertPublisher(
            mqtt_client=mqtt_publisher.client,
            alerts_topic_prefix=settings.mqtt_topic_alerts,
            log_dir=settings.log_dir,
        )
        
        # Publish alert
        alert_publisher.publish(alert, append_jsonl)
        
        return {
            "status": "triggered",
            "asset_id": request.asset_id,
            "signal": request.signal,
            "severity": request.severity,
            "mqtt_topic": f"{settings.mqtt_topic_alerts}/{request.asset_id}",
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to trigger alert: {e}")


@app.get("/scenarios")
async def list_scenarios():
    """List all loaded scenarios."""
    global executors, running, current_sim_time
    
    with _executors_lock:
        scenarios = []
        for asset_id, executor in executors.items():
            status_dict = executor.get_status()
            scenarios.append({
                "asset_id": asset_id,
                "scenario_name": status_dict.get("scenario_name", "unknown"),
                "running": running.get(asset_id, False),
                "current_time": current_sim_time.get(asset_id, 0.0),
                "duration_sec": status_dict.get("duration_sec", 0),
            })
        
        return {
            "scenarios": scenarios,
            "total": len(scenarios),
        }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
