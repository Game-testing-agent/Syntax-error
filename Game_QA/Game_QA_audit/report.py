"""Markdown QA Report Generator: Formats eval_results.json into report.md."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).parent
RESULTS_FILE = ROOT / "results" / "eval_results.json"
REPORT_FILE = ROOT / "report.md"


def generate_report(results_path: Optional[Path] = None, output_path: Optional[Path] = None) -> Path:
    results_file = results_path or RESULTS_FILE
    out_file = output_path or REPORT_FILE

    if not results_file.exists():
        print(f"[report] Results file not found: {results_file}")
        return out_file

    data = json.loads(results_file.read_text(encoding="utf-8"))

    total_sessions = len(data)
    total_findings = sum(len(r.get("findings", [])) for r in data)
    sev_counts = {"critical": 0, "high": 0, "medium": 0, "low": 0}
    path_counts = {"path1": 0, "path2": 0}

    for r in data:
        for f in r.get("findings", []):
            sev = (f.get("severity") or "medium").lower()
            sev_counts[sev] = sev_counts.get(sev, 0) + 1
            p = f.get("path", "path1")
            path_counts[p] = path_counts.get(p, 0) + 1

    lines = [
        "# 🎮 Game_QA Post-Run Evaluation Report",
        "",
        "> Automated Dual-Path QA Analysis for Godot 2D Platformer (`Syntax-error`)",
        "",
        "## 📊 Executive Summary",
        "",
        f"- **Sessions Analyzed**: `{total_sessions}`",
        f"- **Total Findings**: `{total_findings}`",
        f"- **Path 1 (Deterministic Invariants & Engine Anomalies)**: `{path_counts.get('path1', 0)}`",
        f"- **Path 2 (LLM / Semantic Window Review)**: `{path_counts.get('path2', 0)}`",
        "",
        "| Severity | Count |",
        "| :--- | :--- |",
        f"| 🔴 **Critical** | {sev_counts.get('critical', 0)} |",
        f"| 🟠 **High** | {sev_counts.get('high', 0)} |",
        f"| 🟡 **Medium** | {sev_counts.get('medium', 0)} |",
        f"| 🔵 **Low** | {sev_counts.get('low', 0)} |",
        "",
        "---",
        "",
    ]

    for r in data:
        sid = r.get("session_id", "Unknown")
        nevents = r.get("total_events", 0)
        nsnaps = r.get("total_snapshots", 0)
        findings = r.get("findings", [])
        score = r.get("score", {})

        lines.append(f"## 🕹️ Session: `{sid}`")
        lines.append(f"*(Events logged: {nevents} | Telemetry snapshots: {nsnaps})*")
        lines.append("")

        if score.get("matched"):
            lines.append("### 🎯 Ground Truth Evaluation Score")
            matched_count = sum(1 for m in score["matched"] if m["found"])
            total_exp = len(score["matched"])
            lines.append(f"- **Expected Bugs Caught**: `{matched_count} / {total_exp}`")
            lines.append(f"- **False Positives**: `{len(score.get('false_positives', []))}`")
            lines.append("")
            lines.append("| Expected Anomaly / Bug | Caught? | Detection Path | Target |")
            lines.append("| :--- | :--- | :--- | :--- |")
            for m in score["matched"]:
                status = "✅ YES" if m["found"] else "❌ NO"
                lines.append(f"| `{m['expected']}` | {status} | `{m['path'] or '-'}` | `{m['should_be']}` |")
            lines.append("")

        lines.append("### 🔍 Detailed Findings")
        lines.append("")

        if not findings:
            lines.append("✅ _No bugs or invariant violations detected in this session._\n")
            continue

        for i, f in enumerate(findings, start=1):
            sev = (f.get("severity") or "medium").upper()
            path_tag = "Path 1 (Deterministic)" if f.get("path") == "path1" else "Path 2 (Semantic / LLM)"
            human_tag = "⚠️ Human Review Recommended" if f.get("needs_human_review") else "🤖 Auto-Verified"
            title = f.get("title", "Untitled Finding")
            conf = f.get("confidence", 0.0)
            frames = f.get("evidence_frames", [])
            suspected = f.get("suspected_code") or "Unknown"

            lines.append(f"#### {i}. [{sev}] {title}")
            lines.append(f"- **Detection Mechanism**: `{path_tag}` ({human_tag})")
            lines.append(f"- **Confidence**: `{conf:.2f}`")
            if frames:
                lines.append(f"- **Evidence Frame(s)**: `{frames}`")
            lines.append(f"- **Suspected Component**: `{suspected}`")
            lines.append(f"- **Details**:")
            lines.append(f"  > {f.get('explanation')}")
            lines.append("")

        lines.append("---")
        lines.append("")

    out_file.write_text("\n".join(lines), encoding="utf-8")
    print(f"[report] Generated Markdown report at: {out_file}")
    return out_file


def main() -> None:
    generate_report()


if __name__ == "__main__":
    main()

    main()