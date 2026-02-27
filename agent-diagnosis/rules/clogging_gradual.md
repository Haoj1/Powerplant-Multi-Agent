# Clogging (Gradual)

## Root Cause
clogging

## Symptoms
- Flow and pressure both low over time
- Gradual reduction (not sudden drop)
- Valve may appear fully open but effective flow is limited

## Related Signals
flow_m3h, pressure_bar, motor_current_a, valve_open_pct

## Detection Hints
- Use get_telemetry_window(asset_id, 60) to see gradual decline
- Flow and pressure move together (both low)

## Recommended Actions
- Inspect suction strainer and inlet piping for debris
- Check impeller for clogging or wear
- Verify pipe condition and potential blockages
- Consider backflushing or chemical cleaning if applicable

## Impact
Medium to High - reduces efficiency and capacity
