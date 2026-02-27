# Bearing Wear (Acute)

## Root Cause
bearing_wear

## Symptoms
- Vibration and bearing_temp both above threshold
- Positive slope on both signals (rapid onset)
- May accompany minor rpm fluctuation or motor_current_a increase

## Related Signals
vibration_rms, bearing_temp_c, rpm, motor_current_a

## Detection Hints
- Both vibration_rms and bearing_temp_c above threshold
- Use compute_slope to confirm positive trend (rapid degradation)

## Recommended Actions
- Immediate inspection recommended
- Check bearing lubrication level and quality
- Inspect bearing for wear, pitting, or contamination
- Consider earlier shutdown if acute failure pattern

## Impact
High - can lead to catastrophic failure if unaddressed
