# Chapter 5 Evaluation — 框架与所需图表

## 5.1 Evaluation Setup

**要写的内容：**
- **目标**：评估 alert 检测率、诊断准确率、健康假阳性率、推理效率（steps/tokens）。
- **场景列表**：列出 7 类场景（与 `run_alert_eval.py` 一致）：
  - `healthy_baseline`（无故障）
  - `bearing_wear_eval`
  - `clogging_eval`
  - `valve_flow_mismatch_eval`
  - `sensor_drift_eval_temp_override` / `rpm_eval_override`（sensor_override）
  - `noise_burst_eval`
- **流程**：先启动所有服务（MQTT、Simulator、Agent A/B/C/D）→ `run_alert_eval.py` 按序跑多轮场景 → 生成 `scenario_runs.jsonl` 并写入 DB → `run_evaluation.py` 读 DB 与 jsonl 算指标 → `build_report.py` 生成图表。
- **时间窗口**：每个 fault 场景的评估窗口（duration + buffer），healthy 的窗口；说明与 `min_duration_sec`、cooldown 的关系。
- **指标定义**：Detection rate（至少产生 1 个 alert 的 run 占比）、Diagnosis accuracy（预测 root_cause 正确占比）、Healthy false positive rate（healthy 场景下产生任意 alert 的 run 占比）、Fault scenario detection rate（排除 healthy 后的检测率）。

**图表：**
- 可选：**Figure 5.1** — 评估流程图（Pipeline：Services → run_alert_eval → scenario_runs.jsonl + DB → run_evaluation → eval_result.json → build_report → charts）。若正文已够清晰可省略。

---

## 5.2 Alert Detection Results

**要写的内容：**
- **整体**：Overall detection rate（如 44.9%）、Fault scenario detection rate（如 83.3%，排除 healthy）。
- **按信号**：各信号（vibration_rms, bearing_temp_c, flow_m3h, pressure_bar, motor_current_a, valve_flow_mismatch, temp_c, rpm）的 detection rate、expected_runs、hits；指出谁 100%、谁偏低（如 vibration_rms 50%、noise_burst 0%）。
- **健康假阳性**：Healthy false positive rate（如 11.9%）、主要由哪类信号引起（如 bearing_temp_c）。
- **简要原因**：duration 要求、noise_burst 瞬态难满足 min_duration 等。

**图表：**
- **Figure 5.2** — **Detection rate by signal**（横向条形图）  
  - 源文件：`evaluation/report/01_detection_by_signal.png`（build_report.py 中 `chart_detection_by_signal`）。  
  - 说明：每个信号的检测率（%），可与正文“按信号”描述对应。

**表格：**
- **Table 5.1** — Detection by signal（可选）：Signal | Expected runs | Hits | Detection rate (%) | Avg latency (s)。数据来自 `eval_result.json` 的 `detection_by_signal`。

---

## 5.3 Diagnosis Accuracy

**要写的内容：**
- **整体**：Diagnosis accuracy（如 81.1%）、总 diagnosis 数、正确数。
- **按 root cause**：bearing_wear、valve_stuck 100%；clogging、sensor_override、none 的准确率与典型混淆（如 clogging 被误判为 valve_stuck/bearing_wear；sensor_override 与 bearing_wear/clogging 混淆；healthy 被误判为 bearing_wear 等）。
- **混淆矩阵**：用一小段话概括主要混淆对（可引用 Figure 5.5）。

**图表：**
- **Figure 5.3** — **Diagnosis accuracy by root cause**（横向条形图）  
  - 源文件：`evaluation/report/02_diagnosis_accuracy.png`（`chart_diagnosis_accuracy`）。  
  - 说明：各 root_cause 的准确率（%）。

- **Figure 5.5** — **Confusion matrix**（热力图）  
  - 源文件：`evaluation/report/06_confusion_matrix.png`（`chart_confusion_heatmap`）。  
  - 说明：Expected（行）vs Predicted（列），展示混淆对。

**表格：**
- **Table 5.2** — Diagnosis accuracy by root cause（可选）：Root cause | Count | Correct | Accuracy (%)。数据来自 `diagnosis_by_root_cause`。

---

## 5.4 Scenario Matrix (Detection vs Diagnosis)

**要写的内容：**
- 每个**故障场景**同时看“是否被检测到”和“诊断是否正确”。
- 逐场景简述：bearing_wear_eval / valve_flow_mismatch_eval 检测与诊断均好；clogging_eval 检测高、诊断有混淆；sensor_override 类场景诊断难；noise_burst_eval 检测为 0 导致无诊断。
- 可简要提 healthy_baseline：检测假阳性率、诊断对 “none” 的准确率。

**图表：**
- **Figure 5.4** — **Scenario matrix: Detection rate vs Diagnosis accuracy**（并排条形图，按场景）  
  - 源文件：`evaluation/report/03_scenario_matrix.png`（`chart_scenario_matrix`）。  
  - 说明：每个 fault 场景两根柱子（Detection Rate %、Diagnosis Accuracy %），便于对比。

---

## 5.5 Token Usage and Latency

**要写的内容：**
- **Steps**：平均 ReAct 步数、正确 vs 错误诊断的步数差异（可引用图）。
- **Tokens**：平均 total/prompt/completion tokens、按场景的差异（bearing_wear 较少，clogging/sensor_override 较多）。
- **Latency**：从 alert 到 diagnosis 的延迟（若有）；检测 latency（从 fault start 到首 alert）的均值/范围。
- 说明：token 与步骤数反映推理成本与难度（难区分的故障更耗 token）。

**图表：**
- **Figure 5.6** — **Token usage by scenario**（横向条形图，单位 k tokens）  
  - 源文件：`evaluation/report/05_tokens_by_scenario.png`（`chart_tokens_by_scenario`）。

- **Figure 5.7** — **Steps and tokens: Correct vs incorrect diagnoses**（双条形图）  
  - 源文件：`evaluation/report/04_correct_vs_incorrect.png`（`chart_correct_vs_incorrect`）。  
  - 说明：左图 Avg Steps（Correct / Incorrect），右图 Avg Tokens (k)（Correct / Incorrect）。

**表格：**
- **Table 5.3** — Per-scenario summary（可选）：Scenario | Runs | Detection rate | Diagnosis accuracy | Avg steps | Avg tokens (k)。数据来自 `scenario_matrix`。

---

## 5.6 Summary KPIs（可选独立小节或合并到 5.1）

**要写的内容：**
- 用一段话汇总：Scenario runs 总数、Alert detection rate、Diagnosis accuracy、Healthy false positive、Fault scenario detection rate、Alert accuracy (TP+TN)/total（若有）。

**图表：**
- **Figure 5.1 或 Table 5.0** — **Evaluation summary KPIs**  
  - 源文件：`evaluation/report/00_summary_kpis.png`（`chart_summary_kpis`）。  
  - 说明：一表概括主要数值，可放在 5.1 末尾或 5.6。

---

## 5.7 Discussion

**要写的内容：**
- **优点**：bearing_wear / valve_stuck 检测与诊断均好；证据可解释（规则+ReAct）；评估可复现（固定场景+脚本）。
- **局限**：noise_burst 检测失败；clogging 与 valve_stuck 互混；sensor_override 与 bearing_wear/clogging 混淆；healthy 上 bearing_temp_c 假阳性。
- **原因简析**：阈值与 duration、规则区分度、LLM 对“传感器故障”与“真实故障”的区分能力。

---

## 5.8 Improvement Opportunities（或合并入 5.7）

**要写的内容：**
- Alert：针对瞬态（noise_burst）调 threshold/duration；改进 vibration_rms 检测。
- Diagnosis：增加 clogging vs sensor_drift 的判别规则；利用更多 telemetry/slope 特征。
- RAG/系统：批量索引、keyword+semantic 混合检索；多资产/真实数据评估。

---

## 图表与数据文件汇总

| 图号 | 用途 | 源文件（evaluation/report/） | 数据来源 |
|------|------|------------------------------|----------|
| Fig 5.1 | 评估流程（可选） | — | 手绘或 TikZ |
| Fig 5.1/Table 5.0 | 汇总 KPI | 00_summary_kpis.png | eval_result.json 顶层 |
| Fig 5.2 | 按信号检测率 | 01_detection_by_signal.png | detection_by_signal |
| Fig 5.3 | 按 root cause 诊断准确率 | 02_diagnosis_accuracy.png | diagnosis_by_root_cause |
| Fig 5.4 | 场景矩阵（检测 vs 诊断） | 03_scenario_matrix.png | scenario_matrix |
| Fig 5.5 | 混淆矩阵 | 06_confusion_matrix.png | confusion_matrix |
| Fig 5.6 | 按场景 token 用量 | 05_tokens_by_scenario.png | scenario_matrix[*].avg_total_tokens |
| Fig 5.7 | 正确 vs 错误（steps/tokens） | 04_correct_vs_incorrect.png | diagnosis_by_root_cause._all |

**生成图表：** 在项目根目录执行：
```bash
python evaluation/run_evaluation.py    # 若尚未有最新 eval_result.json
python evaluation/build_report.py     # 生成 evaluation/report/*.png
```
将需要的 PNG 复制到 `report/figures/`（或约定路径），在 main.tex 中用 `\includegraphics` 引用。

**表格数据：** 均来自 `evaluation/report/eval_result.json`，可在正文或附录中注明“数据来自 run_evaluation.py 输出”。

---

## 建议的 Chapter 5 节结构（最终）

1. **5.1 Evaluation Setup** — 目标、场景、流程、指标定义；（可选）Figure 5.1 评估流程；可选 Table/Figure 汇总 KPI。
2. **5.2 Alert Detection Results** — 整体与按信号、健康假阳性；**Figure 5.2** 按信号检测率；可选 Table 5.1。
3. **5.3 Diagnosis Accuracy** — 整体与按 root cause、混淆简述；**Figure 5.3** 按 root cause 准确率；**Figure 5.5** 混淆矩阵；可选 Table 5.2。
4. **5.4 Scenario Matrix** — 各场景检测+诊断；**Figure 5.4** 场景矩阵图。
5. **5.5 Token Usage and Latency** — steps/tokens/延迟；**Figure 5.6** 按场景 token；**Figure 5.7** 正确 vs 错误；可选 Table 5.3。
6. **5.6 Discussion** — 优点与局限。
7. **5.7 Improvement Opportunities** — 改进方向。

图号可按实际插入顺序微调（如 5.1 为 KPI，5.2–5.7 为各结果图）。
