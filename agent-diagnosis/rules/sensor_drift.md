# Sensor Drift

## Root Cause
sensor_drift

## Symptoms
- One or more signals drift gradually from expected values
- Other correlated signals (e.g. flow, pressure, current) appear inconsistent with drifted signal
- May trigger threshold alerts despite physically normal operation

## Related Signals
All signals - typically pressure_bar, flow_m3h, temp_c, bearing_temp_c, vibration_rms, rpm, motor_current_a, valve_open_pct

## Variants
- **Long duration**: Single-signal anomaly > 120s, others normal (likely drift not fault)

## Recommended Actions
- Cross-check drifted signal against redundant instruments or manual readings
- Schedule sensor calibration
- Review sensor history for drift pattern
- Replace sensor if calibration fails

## Time/Trend Hints
- Use get_telemetry_window to check if only one signal is anomalous for > 120s
- Cross-check: other correlated signals (flow, pressure, current) should be consistent

## Impact
Low to Medium - can cause false alerts or hide real faults
