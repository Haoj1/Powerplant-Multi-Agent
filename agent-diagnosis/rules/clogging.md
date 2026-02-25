# Clogging (Pipe or Impeller)

## Root Cause
clogging

## Symptoms
- Reduced flow_m3h (below nominal)
- Reduced pressure_bar (head loss)
- Motor current may decrease or remain stable
- Valve may appear fully open but effective flow is limited

## Related Signals
flow_m3h, pressure_bar, motor_current_a, valve_open_pct

## Variants
- **Sudden**: flow drop in 10s (negative slope), sustained > 15s
- **Gradual**: flow and pressure both low over time

## Recommended Actions
- Inspect suction strainer and inlet piping for debris
- Check impeller for clogging or wear
- Verify pipe condition and potential blockages
- Consider backflushing or chemical cleaning if applicable

## Time/Trend Hints
- Use compute_slope(asset_id, "flow_m3h", 10) for sudden drop (negative slope)
- Use get_telemetry_window(asset_id, 30) to see flow/pressure evolution
- Sudden clogging: flow drop in 10s, sustained > 15s

## Impact
Medium to High - reduces efficiency and capacity
