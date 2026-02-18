# Sensor Drift

## Root Cause
sensor_drift

## Symptoms
- One or more signals drift gradually from expected values
- Other correlated signals (e.g. flow, pressure, current) appear inconsistent with drifted signal
- May trigger threshold alerts despite physically normal operation

## Related Signals
All signals - typically pressure_bar, flow_m3h, temp_c, bearing_temp_c, vibration_rms, rpm, motor_current_a, valve_open_pct

## Recommended Actions
- Cross-check drifted signal against redundant instruments or manual readings
- Schedule sensor calibration
- Review sensor history for drift pattern
- Replace sensor if calibration fails

## Impact
Low to Medium - can cause false alerts or hide real faults
