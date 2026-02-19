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

# Add project root so shared_lib package can be imported
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

try:
    from shared_lib.models import Telemetry, TelemetrySignals, TelemetryTruth, FaultType
    from shared_lib.config import get_settings
    from shared_lib.utils import get_current_timestamp, generate_id

    print("✅ All shared_lib modules loaded successfully")

    # Test model instantiation
    from datetime import datetime, timezone

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
    settings = get_settings()
    print(f"✅ Settings loaded: MQTT_HOST={settings.mqtt_host}, MQTT_PORT={settings.mqtt_port}")

    # Test utilities
    timestamp = get_current_timestamp()
    test_id = generate_id()
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
