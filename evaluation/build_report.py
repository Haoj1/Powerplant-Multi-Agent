#!/usr/bin/env python3
"""
Build evaluation report with charts for use in reports.
Run: python evaluation/build_report.py

Outputs:
  - evaluation/report/  (charts as PNG + HTML dashboard)
  - evaluation/report/eval_report.html  (standalone HTML with embedded charts)
"""

import json
import sys
from pathlib import Path

_project_root = Path(__file__).parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import matplotlib
    matplotlib.rcParams["font.family"] = ["DejaVu Sans", "sans-serif"]
    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False

from evaluation.run_evaluation import run_evaluation


def _ensure_report_dir() -> Path:
    d = _project_root / "evaluation" / "report"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _save_fig(fig, name: str, report_dir: Path) -> str:
    path = report_dir / f"{name}.png"
    fig.savefig(path, dpi=120, bbox_inches="tight")
    plt.close(fig)
    return str(path.relative_to(_project_root))


def chart_detection_by_signal(data: dict, report_dir: Path) -> str | None:
    if not HAS_MATPLOTLIB:
        return None
    det = data.get("detection_by_signal", {})
    if not det:
        return None
    signals = list(det.keys())
    rates = [det[s].get("detection_rate", 0) or 0 for s in signals]
    colors = ["#2ecc71" if r >= 0.9 else "#f39c12" if r >= 0.5 else "#e74c3c" for r in rates]
    fig, ax = plt.subplots(figsize=(10, 5))
    bars = ax.barh(signals, [r * 100 for r in rates], color=colors)
    ax.set_xlim(0, 105)
    ax.set_xlabel("Detection Rate (%)")
    ax.set_title("Alert Detection Rate by Signal")
    ax.axvline(x=100, color="gray", linestyle="--", alpha=0.5)
    for i, (s, r) in enumerate(zip(signals, rates)):
        ax.text(r * 100 + 1, i, f"{r*100:.0f}%", va="center", fontsize=9)
    return _save_fig(fig, "01_detection_by_signal", report_dir)


def chart_diagnosis_accuracy(data: dict, report_dir: Path) -> str | None:
    if not HAS_MATPLOTLIB:
        return None
    diag = data.get("diagnosis_by_root_cause", {})
    rc = [k for k in diag.keys() if not k.startswith("_")]
    if not rc:
        return None
    acc = [diag[k].get("accuracy") or 0 for k in rc]
    colors = ["#2ecc71" if a >= 0.9 else "#f39c12" if a >= 0.5 else "#e74c3c" for a in acc]
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.barh(rc, [a * 100 for a in acc], color=colors)
    ax.set_xlim(0, 105)
    ax.set_xlabel("Accuracy (%)")
    ax.set_title("Diagnosis Accuracy by Root Cause")
    ax.axvline(x=100, color="gray", linestyle="--", alpha=0.5)
    for i, (r, a) in enumerate(zip(rc, acc)):
        ax.text(a * 100 + 1, i, f"{a*100:.1f}%", va="center", fontsize=9)
    return _save_fig(fig, "02_diagnosis_accuracy", report_dir)


def chart_scenario_matrix(data: dict, report_dir: Path) -> str | None:
    if not HAS_MATPLOTLIB:
        return None
    sm = data.get("scenario_matrix", {})
    names = [k for k in sm.keys() if "healthy" not in k.lower() and sm[k].get("diagnosis_count", 0) > 0]
    if not names:
        return None
    det_rates = [sm[n].get("detection_rate") or 0 for n in names]
    diag_acc = [sm[n].get("diagnosis_accuracy") or 0 for n in names]
    x = range(len(names))
    w = 0.35
    fig, ax = plt.subplots(figsize=(12, 5))
    ax.bar([i - w/2 for i in x], [r * 100 for r in det_rates], w, label="Detection Rate", color="#3498db")
    ax.bar([i + w/2 for i in x], [a * 100 for a in diag_acc], w, label="Diagnosis Accuracy", color="#9b59b6")
    ax.set_xticks(x)
    ax.set_xticklabels(names, rotation=30, ha="right")
    ax.set_ylabel("%")
    ax.set_title("Scenario Matrix: Detection vs Diagnosis")
    ax.legend()
    ax.set_ylim(0, 105)
    return _save_fig(fig, "03_scenario_matrix", report_dir)


def chart_correct_vs_incorrect(data: dict, report_dir: Path) -> str | None:
    if not HAS_MATPLOTLIB:
        return None
    d = data.get("diagnosis_by_root_cause", {}).get("_all", {})
    if not d:
        return None
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 4))
    labels = ["Correct", "Incorrect"]
    steps = [d.get("avg_steps_correct") or 0, d.get("avg_steps_incorrect") or 0]
    tokens = [d.get("avg_tokens_correct") or 0, d.get("avg_tokens_incorrect") or 0]
    ax1.bar(labels, steps, color=["#2ecc71", "#e74c3c"])
    ax1.set_ylabel("Avg Steps")
    ax1.set_title("Steps: Correct vs Incorrect")
    ax2.bar(labels, [t/1000 for t in tokens], color=["#2ecc71", "#e74c3c"])
    ax2.set_ylabel("Avg Tokens (k)")
    ax2.set_title("Tokens: Correct vs Incorrect")
    return _save_fig(fig, "04_correct_vs_incorrect", report_dir)


def chart_tokens_by_scenario(data: dict, report_dir: Path) -> str | None:
    if not HAS_MATPLOTLIB:
        return None
    sm = data.get("scenario_matrix", {})
    names = [k for k in sm.keys() if sm[k].get("avg_total_tokens") is not None]
    if not names:
        return None
    tokens = [sm[n]["avg_total_tokens"] / 1000 for n in names]
    colors = plt.cm.viridis([t / max(tokens) if tokens else 0 for t in tokens])
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.barh(names, tokens, color=colors)
    ax.set_xlabel("Avg Total Tokens (k)")
    ax.set_title("Token Usage by Scenario")
    return _save_fig(fig, "05_tokens_by_scenario", report_dir)


def chart_confusion_heatmap(data: dict, report_dir: Path) -> str | None:
    if not HAS_MATPLOTLIB:
        return None
    cm = data.get("confusion_matrix", {})
    rc = sorted([k for k in cm.keys()])
    preds = set()
    for row in cm.values():
        preds.update(row.keys())
    preds = sorted(preds)
    if not rc or not preds:
        return None
    mat = []
    for r in rc:
        row = [cm[r].get(p, 0) for p in preds]
        mat.append(row)
    fig, ax = plt.subplots(figsize=(8, 6))
    im = ax.imshow(mat, cmap="Blues", aspect="auto")
    ax.set_xticks(range(len(preds)))
    ax.set_xticklabels(preds, rotation=45, ha="right")
    ax.set_yticks(range(len(rc)))
    ax.set_yticklabels(rc)
    ax.set_xlabel("Predicted")
    ax.set_ylabel("Expected")
    ax.set_title("Confusion Matrix")
    for i in range(len(rc)):
        for j in range(len(preds)):
            v = mat[i][j]
            c = "white" if v > (max(max(row) for row in mat) * 0.5) else "black"
            ax.text(j, i, str(v), ha="center", va="center", color=c, fontsize=9)
    plt.colorbar(im, ax=ax, label="Count")
    return _save_fig(fig, "06_confusion_matrix", report_dir)


def chart_summary_kpis(data: dict, report_dir: Path) -> str | None:
    if not HAS_MATPLOTLIB:
        return None
    fig, ax = plt.subplots(figsize=(6, 3))
    ax.axis("off")
    kpis = [
        ("Scenario Runs", data.get("scenario_runs", 0)),
        ("Alert Detection Rate", f"{(data.get('detection_rate') or 0)*100:.1f}%"),
        ("Diagnosis Accuracy", f"{(data.get('diagnosis_accuracy') or 0)*100:.1f}%"),
        ("Healthy False Positive", f"{(data.get('healthy_false_positive_rate') or 0)*100:.1f}%"),
        ("Alert Accuracy (TP+TN)/total", f"{(data.get('alert_accuracy') or 0)*100:.1f}%"),
        ("Fault Scenario Detection (excl. healthy)", f"{(data.get('fault_scenario_detection_rate') or 0)*100:.1f}%"),
    ]
    table = ax.table(
        cellText=[[k, str(v)] for k, v in kpis],
        colLabels=["Metric", "Value"],
        loc="center",
        cellLoc="left",
    )
    table.auto_set_font_size(False)
    table.set_fontsize(11)
    table.scale(1.2, 2)
    ax.set_title("Evaluation Summary", fontsize=14, pad=20)
    return _save_fig(fig, "00_summary_kpis", report_dir)


def build_html_report(data: dict, chart_paths: dict, report_dir: Path) -> Path:
    html = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>Evaluation Report - Multi-Agent Monitoring</title>
  <style>
    body { font-family: system-ui, sans-serif; max-width: 1200px; margin: 0 auto; padding: 24px; background: #f5f5f5; }
    h1 { color: #2c3e50; }
    h2 { color: #34495e; margin-top: 32px; }
    .kpi-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px; margin: 24px 0; }
    .kpi { background: white; padding: 20px; border-radius: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); text-align: center; }
    .kpi .val { font-size: 28px; font-weight: bold; color: #3498db; }
    .kpi .label { font-size: 12px; color: #7f8c8d; margin-top: 4px; }
    .chart { background: white; padding: 16px; margin: 16px 0; border-radius: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }
    .chart img { max-width: 100%; height: auto; }
    table { width: 100%; border-collapse: collapse; background: white; border-radius: 8px; overflow: hidden; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }
    th, td { padding: 12px; text-align: left; border-bottom: 1px solid #ecf0f1; }
    th { background: #34495e; color: white; }
  </style>
</head>
<body>
  <h1>Evaluation Report</h1>
  <p>Multi-Agent Powerplant Monitoring System</p>

  <div class="kpi-grid">
    <div class="kpi"><div class="val">""" + str(data.get("scenario_runs", 0)) + """</div><div class="label">Scenario Runs</div></div>
    <div class="kpi"><div class="val">""" + f"{(data.get('detection_rate') or 0)*100:.1f}%" + """</div><div class="label">Alert Detection Rate</div></div>
    <div class="kpi"><div class="val">""" + f"{(data.get('diagnosis_accuracy') or 0)*100:.1f}%" + """</div><div class="label">Diagnosis Accuracy</div></div>
    <div class="kpi"><div class="val">""" + f"{(data.get('healthy_false_positive_rate') or 0)*100:.1f}%" + """</div><div class="label">Healthy False Positive</div></div>
    <div class="kpi"><div class="val">""" + f"{(data.get('alert_accuracy') or 0)*100:.1f}%" + """</div><div class="label">Alert Accuracy (TP+TN)/total</div></div>
    <div class="kpi"><div class="val">""" + f"{(data.get('fault_scenario_detection_rate') or 0)*100:.1f}%" + """</div><div class="label">Fault Scenario Detection (excl. healthy)</div></div>
  </div>
"""
    for name, path in sorted(chart_paths.items()):
        if path:
            rel = Path(path).name
            html += f'  <div class="chart"><h2>{name}</h2><img src="{rel}" alt="{name}" /></div>\n'

    html += """
  <h2>Scenario Matrix (Table)</h2>
  <table>
    <tr><th>Scenario</th><th>Runs</th><th>Detection Rate</th><th>Diagnosis Accuracy</th><th>Avg Steps</th><th>Avg Tokens</th></tr>
"""
    for name, s in (data.get("scenario_matrix") or {}).items():
        dr = f"{(s.get('detection_rate') or 0)*100:.1f}%" if s.get("detection_rate") is not None else "-"
        da = f"{(s.get('diagnosis_accuracy') or 0)*100:.1f}%" if s.get("diagnosis_accuracy") is not None else "-"
        steps = f"{s.get('avg_steps') or 0:.1f}" if s.get("avg_steps") is not None else "-"
        toks = f"{(s.get('avg_total_tokens') or 0)/1000:.1f}k" if s.get("avg_total_tokens") is not None else "-"
        html += f"    <tr><td>{name}</td><td>{s.get('runs', 0)}</td><td>{dr}</td><td>{da}</td><td>{steps}</td><td>{toks}</td></tr>\n"
    html += "  </table>\n</body>\n</html>"

    out = report_dir / "eval_report.html"
    out.write_text(html, encoding="utf-8")
    return out


def build_markdown_report(data: dict, report_dir: Path) -> Path:
    """Export a Markdown report for docs/reports."""
    md = "# Evaluation Report\n\n"
    md += f"- **Scenario Runs**: {data.get('scenario_runs', 0)}\n"
    md += f"- **Alert Detection Rate**: {(data.get('detection_rate') or 0)*100:.1f}%\n"
    md += f"- **Diagnosis Accuracy**: {(data.get('diagnosis_accuracy') or 0)*100:.1f}%\n"
    md += f"- **Healthy False Positive**: {(data.get('healthy_false_positive_rate') or 0)*100:.1f}%\n"
    md += f"- **Alert Accuracy (TP+TN)/total**: {(data.get('alert_accuracy') or 0)*100:.1f}%\n"
    md += f"- **Fault Scenario Detection (excl. healthy)**: {(data.get('fault_scenario_detection_rate') or 0)*100:.1f}%\n\n"
    md += "## Scenario Matrix\n\n| Scenario | Runs | Detection | Diagnosis | Avg Steps | Avg Tokens |\n|----------|------|-----------|-----------|-----------|------------|\n"
    for name, s in (data.get("scenario_matrix") or {}).items():
        dr = f"{(s.get('detection_rate') or 0)*100:.1f}%" if s.get("detection_rate") is not None else "-"
        da = f"{(s.get('diagnosis_accuracy') or 0)*100:.1f}%" if s.get("diagnosis_accuracy") is not None else "-"
        steps = f"{s.get('avg_steps') or 0:.1f}" if s.get("avg_steps") is not None else "-"
        toks = f"{(s.get('avg_total_tokens') or 0)/1000:.1f}k" if s.get("avg_total_tokens") is not None else "-"
        md += f"| {name} | {s.get('runs', 0)} | {dr} | {da} | {steps} | {toks} |\n"
    md += "\n## Diagnosis by Root Cause\n\n| Root Cause | Count | Correct | Accuracy | Avg Steps | Avg Tokens |\n|------------|-------|---------|----------|-----------|------------|\n"
    for rc, s in (data.get("diagnosis_by_root_cause") or {}).items():
        if rc.startswith("_"):
            continue
        acc = f"{(s.get('accuracy') or 0)*100:.1f}%" if s.get("accuracy") is not None else "-"
        steps = f"{s.get('avg_steps') or 0:.1f}" if s.get("avg_steps") is not None else "-"
        toks = f"{(s.get('avg_total_tokens') or 0)/1000:.1f}k" if s.get("avg_total_tokens") is not None else "-"
        md += f"| {rc} | {s.get('count', 0)} | {s.get('correct', 0)} | {acc} | {steps} | {toks} |\n"
    out = report_dir / "eval_report.md"
    out.write_text(md, encoding="utf-8")
    return out


def main():
    print("Running evaluation...")
    data = run_evaluation()
    report_dir = _ensure_report_dir()

    # Save raw JSON
    json_path = report_dir / "eval_result.json"
    json_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    print(f"  Saved: {json_path.relative_to(_project_root)}")

    chart_paths = {}
    if HAS_MATPLOTLIB:
        chart_paths["Summary KPIs"] = chart_summary_kpis(data, report_dir)
        chart_paths["Detection by Signal"] = chart_detection_by_signal(data, report_dir)
        chart_paths["Diagnosis Accuracy"] = chart_diagnosis_accuracy(data, report_dir)
        chart_paths["Scenario Matrix"] = chart_scenario_matrix(data, report_dir)
        chart_paths["Correct vs Incorrect"] = chart_correct_vs_incorrect(data, report_dir)
        chart_paths["Tokens by Scenario"] = chart_tokens_by_scenario(data, report_dir)
        chart_paths["Confusion Matrix"] = chart_confusion_heatmap(data, report_dir)
        for k, v in chart_paths.items():
            if v:
                print(f"  Chart: {k} -> {v}")
    else:
        print("  Install matplotlib for charts: pip install matplotlib")

    html_path = build_html_report(data, chart_paths, report_dir)
    print(f"  Report: {html_path.relative_to(_project_root)}")

    md_path = build_markdown_report(data, report_dir)
    print(f"  Markdown: {md_path.relative_to(_project_root)}")

    print("Done.")


if __name__ == "__main__":
    main()
