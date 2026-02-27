# Sensor Drift (Long Duration)

## Root Cause
sensor_drift

## Symptoms
- Single-signal anomaly > 120s
- Other correlated signals (flow, pressure, current) appear normal
- Likely drift rather than physical fault

## Related Signals
All signals - typically pressure_bar, flow_m3h, temp_c, bearing_temp_c, vibration_rms, rpm, motor_current_a, valve_open_pct

## Detection Hints
- Use get_telemetry_window to check if only one signal is anomalous for > 120s
- Cross-check: other correlated signals should be consistent

## Recommended Actions
- Cross-check drifted signal against redundant instruments or manual readings
- Schedule sensor calibration
- Review sensor history for drift pattern
- Replace sensor if calibration fails

## Impact
Low to Medium - can cause false alerts or hide real faults
