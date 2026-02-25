# Bearing Wear

## Root Cause
bearing_wear

## Symptoms
- Elevated vibration_rms (above baseline)
- Elevated bearing_temp_c (above ambient + normal load)
- May accompany minor rpm fluctuation or motor_current_a increase

## Related Signals
vibration_rms, bearing_temp_c, rpm, motor_current_a

## Variants
- **Chronic**: vibration slope > 0 over 60s, sustained > 30s (gradual degradation)
- **Acute**: vibration + bearing_temp both above threshold, slope positive (rapid onset)

## Recommended Actions
- Check bearing lubrication level and quality
- Inspect bearing for wear, pitting, or contamination
- Schedule planned shutdown for bearing replacement if degradation confirmed
- Monitor vibration trend to assess progression

## Time/Trend Hints
- Use compute_slope(asset_id, "vibration_rms", 60) to check for gradual increase
- Use compute_slope(asset_id, "bearing_temp_c", 60) for temperature trend
- Chronic bearing wear: slope > 0 over 60s, sustained > 30s
- Acute: both signals above threshold with positive slope

## Impact
High - can lead to catastrophic failure if unaddressed
