# Evaluation Section Writing Reminder

When writing the Evaluation chapter of the report, be sure to include the following metrics and explain how each is computed:

## Required Metrics

1. **detection_rate** (Alert Detection Rate)  
   - Meaning: proportion of runs with at least one alert  
   - Formula: `detection_run_count / total_runs`

2. **healthy_false_positive_rate** (Healthy False Positive)  
   - Meaning: false positive rate in healthy scenarios  
   - Formula: `healthy_runs_with_alerts / healthy_runs`

3. **diagnosis_accuracy** (Diagnosis Accuracy)  
   - Meaning: root cause diagnosis correctness rate  
   - Formula: `diagnosis_correct / diagnosis_count`

4. **alert_accuracy** (Alert Accuracy)  
   - Meaning: binary classification accuracy (alert vs no alert)  
   - Formula: `(TP + TN) / total`  
   - Where: TP = fault runs with alerts, TN = healthy runs without alerts

5. **fault_scenario_detection_rate** (Fault Scenario Alert Detection Rate, excluding healthy)  
   - Meaning: alert detection rate for fault scenarios only  
   - Formula: `TP / fault_runs`  
   - Reference: ~83.3% (based on current data)

## Report Requirements

- Provide definition and formula for each metric  
- Explicitly state the fault-scenario-only alert detection rate (excluding healthy)  
- Clearly distinguish between detection_rate and alert_accuracy in the report
