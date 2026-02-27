# Bearing Wear (Chronic)

## Root Cause
bearing_wear

## Symptoms
- Gradual increase in vibration_rms over time (slope > 0 over 60s)
- Gradual increase in bearing_temp_c
- Sustained above threshold for > 30s
- Degradation develops slowly

## Related Signals
vibration_rms, bearing_temp_c, rpm, motor_current_a

## Detection Hints
- Use compute_slope(asset_id, "vibration_rms", 60) to check for gradual increase
- Use compute_slope(asset_id, "bearing_temp_c", 60) for temperature trend
- Chronic: slope > 0 over 60s, sustained > 30s

## Recommended Actions
- Check bearing lubrication level and quality
- Inspect bearing for wear, pitting, or contamination
- Schedule planned shutdown for bearing replacement if degradation confirmed
- Monitor vibration trend to assess progression

## Impact
High - can lead to catastrophic failure if unaddressed
