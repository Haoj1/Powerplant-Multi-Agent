# Valve Stuck

## Root Cause
valve_stuck

## Symptoms
- valve_open_pct does not change when commanded
- Flow or pressure may not respond to valve position commands
- Discrepancy between commanded and actual flow

## Related Signals
valve_open_pct, flow_m3h, pressure_bar

## Variants
- **Duration**: valve vs flow mismatch > 20s (valve high but flow low)
- **Command response**: valve_open_pct unchanged while flow/pressure change

## Recommended Actions
- Verify valve actuator and position feedback
- Check for mechanical binding or debris in valve
- Inspect valve seals and stem
- Manual override test if safe to do so

## Time/Trend Hints
- Use get_telemetry_window(asset_id, 60) to compare valve_open_pct vs flow_m3h over time
- Valve stuck: valve position unchanged while flow/pressure change, sustained > 20s
- valve_flow_mismatch alert: valve > 80% but flow < 50 m³/h for > 20s

## Impact
Medium - limits process control and may cause over/under delivery
