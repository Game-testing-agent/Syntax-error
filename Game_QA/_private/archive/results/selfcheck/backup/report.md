# 🎮 Game_QA Post-Run Evaluation Report

> Automated Dual-Path QA Analysis for Godot 2D Platformer (`Syntax-error`)

## 📊 Executive Summary

- **Sessions Analyzed**: `1`
- **Total Findings**: `2`
- **Path 1 (Deterministic Invariants & Engine Anomalies)**: `1`
- **Path 2 (LLM / Semantic Window Review)**: `1`

| Severity | Count |
| :--- | :--- |
| 🔴 **Critical** | 0 |
| 🟠 **High** | 2 |
| 🟡 **Medium** | 0 |
| 🔵 **Low** | 0 |

---

## 🕹️ Session: `session_1792777856_45957`
*(Events logged: 461 | Telemetry snapshots: 34)*

### 🔍 Detailed Findings

#### 1. [HIGH] Engine Anomaly: unexpected_score_change
- **Detection Mechanism**: `Path 1 (Deterministic)` (🤖 Auto-Verified)
- **Confidence**: `0.95`
- **Evidence Frame(s)**: `[578, 861, 964, 1156, 1714, 1887, 2270, 3805, 3970, 3985]`
- **Suspected Component**: `GameLogger.gd / res://src/Levels/Level01.tscn`
- **Details**:
  > Expected: Score should only increase or reset to 0 | Observed: Score decreased by 10 across frame(s) [578, 861, 964, 1156, 1714].

#### 2. [HIGH] Semantic Anomaly: unexpected_score_change
- **Detection Mechanism**: `Path 2 (Semantic / LLM)` (⚠️ Human Review Recommended)
- **Confidence**: `0.75`
- **Evidence Frame(s)**: `[578, 964, 1714, 1887, 2270, 3805, 3970, 4500, 4889, 5064, 5396]`
- **Suspected Component**: `PlayerData.gd:L36 (set_score)`
- **Details**:
  > White-box audit verified 'unexpected_score_change' at frame 578. Expected: Score should only increase or reset to 0 | Observed: Score decreased by 10. Traced to logic in PlayerData.gd:L36 (set_score).

---
