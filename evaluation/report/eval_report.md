# Evaluation Report

- **Scenario Runs**: 390
- **Alert Detection Rate**: 44.9%
- **Diagnosis Accuracy**: 81.1%
- **Healthy False Positive**: 11.9%
- **Alert Accuracy (TP+TN)/total**: 85.9%
- **Fault Scenario Detection (excl. healthy)**: 83.3%

## Scenario Matrix

| Scenario | Runs | Detection | Diagnosis | Avg Steps | Avg Tokens |
|----------|------|-----------|-----------|-----------|------------|
| healthy_baseline | 210 | 11.9% | 66.7% | 8.3 | 36.0k |
| bearing_wear_eval | 30 | 100.0% | 100.0% | 7.1 | 27.7k |
| clogging_eval | 30 | 100.0% | 73.7% | 9.3 | 53.2k |
| valve_flow_mismatch_eval | 30 | 100.0% | 100.0% | 8.9 | 47.0k |
| sensor_drift_eval_temp_override | 30 | 100.0% | 63.3% | 9.6 | 52.6k |
| rpm_eval_override | 30 | 100.0% | 43.3% | 9.3 | 50.5k |
| noise_burst_eval | 30 | 0.0% | - | - | - |

## Diagnosis by Root Cause

| Root Cause | Count | Correct | Accuracy | Avg Steps | Avg Tokens |
|------------|-------|---------|----------|-----------|------------|
| bearing_wear | 78 | 78 | 100.0% | 7.1 | 27.7k |
| clogging | 19 | 14 | 73.7% | 9.3 | 53.2k |
| valve_stuck | 27 | 27 | 100.0% | 8.9 | 47.0k |
| sensor_override | 60 | 32 | 53.3% | 9.5 | 51.6k |
| none | 12 | 8 | 66.7% | 8.3 | 36.0k |
