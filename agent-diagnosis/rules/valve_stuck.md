# Valve Stuck

## Root Cause
valve_stuck

## Symptoms
- valve_open_pct does not change when commanded
- Flow or pressure may not respond to valve position commands
- Discrepancy between commanded and actual flow

## Related Signals
valve_open_pct, flow_m3h, pressure_bar

## Recommended Actions
- Verify valve actuator and position feedback
- Check for mechanical binding or debris in valve
- Inspect valve seals and stem
- Manual override test if safe to do so

## Impact
Medium - limits process control and may cause over/under delivery
