#!/usr/bin/env python3
"""Quick test script to verify Phase 0 setup."""

import sys
from pathlib import Path

# Check if dependencies are installed
try:
    import pydantic
    import fastapi
    import pydantic_settings
except ImportError as e:
    print("⚠️  Dependencies not installed yet.")
    print("   Please run: pip install -r requirements.txt")
    print(f"   Missing: {e.name}")
    sys.exit(0)

# Add shared-lib to path (using sys.path manipulation for directory with hyphen)
project_root = Path(__file__).parent
shared_lib_path = project_root / "shared-lib"
sys.path.insert(0, str(project_root))

# Import directly from files (bypassing package import issue with hyphen)
try:
    import importlib.util
    
    # Load models
    models_spec = importlib.util.spec_from_file_location("models", shared_lib_path / "models.py")
    models = importlib.util.module_from_spec(models_spec)
    models_spec.loader.exec_module(models)
    
    # Load config
    config_spec = importlib.util.spec_from_file_location("config", shared_lib_path / "config.py")
    config = importlib.util.module_from_spec(config_spec)
    config_spec.loader.exec_module(config)
    
    # Load utils
    utils_spec = importlib.util.spec_from_file_location("utils", shared_lib_path / "utils.py")
    utils = importlib.util.module_from_spec(utils_spec)
    utils_spec.loader.exec_module(utils)
    
    print("✅ All shared-lib modules loaded successfully")
    
    # Test model instantiation
    from datetime import datetime, timezone
    
    Telemetry = models.Telemetry
    TelemetrySignals = models.TelemetrySignals
    TelemetryTruth = models.TelemetryTruth
    FaultType = models.FaultType
    
    test_telemetry = Telemetry(
        ts=datetime.now(timezone.utc),
        plant_id="plant01",
        asset_id="pump01",
        signals=TelemetrySignals(
            pressure_bar=12.3,
            flow_m3h=85.1,
            temp_c=62.2,
            bearing_temp_c=71.0,
            vibration_rms=0.42,
            rpm=2950,
            motor_current_a=18.6,
            valve_open_pct=62.0,
        ),
        truth=TelemetryTruth(fault=FaultType.NONE, severity=0.0),
    )
    print("✅ Telemetry model instantiation successful")
    
    # Test settings
    settings = config.get_settings()
    print(f"✅ Settings loaded: MQTT_HOST={settings.mqtt_host}, MQTT_PORT={settings.mqtt_port}")
    
    # Test utilities
    timestamp = utils.get_current_timestamp()
    test_id = utils.generate_id()
    print(f"✅ Utilities working: timestamp={timestamp.isoformat()}, id={test_id[:8]}...")
    
    print("\n🎉 Phase 0 setup verified successfully!")
    print("\nNext steps:")
    print("1. Install dependencies: pip install -r requirements.txt")
    print("2. Copy .env.example to .env and configure")
    print("3. Start MQTT: docker-compose up -d mosquitto")
    print("4. Begin Phase 1: Implement simulator service")
    
except ImportError as e:
    print(f"❌ Import error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
