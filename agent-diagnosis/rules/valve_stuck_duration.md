# Valve Stuck (Duration)

## Root Cause
valve_stuck

## Symptoms
- Valve vs flow mismatch > 20s
- valve_open_pct high (> 80%) but flow_m3h low (< 50 m³/h)
- valve_flow_mismatch alert triggered

## Related Signals
valve_open_pct, flow_m3h, pressure_bar

## Detection Hints
- Use get_telemetry_window(asset_id, 60) to compare valve_open_pct vs flow_m3h over time
- valve_flow_mismatch alert: valve > 80% but flow < 50 m³/h for > 20s

## Recommended Actions
- Verify valve actuator and position feedback
- Check for mechanical binding or debris in valve
- Inspect valve seals and stem
- Manual override test if safe to do so

## Impact
Medium - limits process control and may cause over/under delivery
