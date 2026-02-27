# Clogging (Sudden)

## Root Cause
clogging

## Symptoms
- Flow drops sharply in 10s (negative slope)
- Sustained low flow > 15s
- Pressure may drop with flow
- Motor current may decrease or remain stable

## Related Signals
flow_m3h, pressure_bar, motor_current_a, valve_open_pct

## Detection Hints
- Use compute_slope(asset_id, "flow_m3h", 10) for sudden drop (negative slope)
- Use get_telemetry_window(asset_id, 30) to see flow/pressure evolution
- Sudden clogging: flow drop in 10s, sustained > 15s

## Recommended Actions
- Inspect suction strainer and inlet piping for debris
- Check impeller for clogging or wear
- Verify pipe condition and potential blockages
- Consider backflushing or chemical cleaning if applicable

## Impact
Medium to High - reduces efficiency and capacity
