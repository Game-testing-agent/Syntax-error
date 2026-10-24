"""Post-Run QA Evaluator: Ingests Godot game_events.jsonl, runs Path 1 + Path 2 checks, produces findings."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Optional

from checker import check_event, check_snapshot, violations_to_findings
from llm import get_llm_status, review_window
from loader import load_sessions, resolve_log_path
from schemas import Check, Finding, ReviewWindow, SessionData, Severity, Verdict, Violation

ROOT = Path(__file__).parent
DATA_DIR = ROOT / "data"
RESULTS_DIR = ROOT / "results"
RESULTS_DIR.mkdir(exist_ok=True)


def load_checks(checks_path: Optional[Path] = None) -> list[Check]:
    path = checks_path or (DATA_DIR / "checks.json")
    if not path.exists():
        path = DATA_DIR / "check.json"
    if not path.exists():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    return [Check(**c) for c in data.get("checks", [])]


def dedupe_finding_key(f: Finding) -> tuple:
    frames = tuple(sorted(f.evidence_frames or []))
    return (f.title, frames, f.suspected_code or "")


def merge_findings(existing: Finding, incoming: Finding) -> None:
    if existing.path == "path2" and incoming.path == "path1":
        existing.path = "both"
    elif existing.path == "path1" and incoming.path == "path2":
        existing.path = "both"

    combined_frames = list(set((existing.evidence_frames or []) + (incoming.evidence_frames or [])))
    existing.evidence_frames = sorted(combined_frames)

    sev_order = {Severity.low: 1, Severity.medium: 2, Severity.high: 3, Severity.critical: 4}
    if sev_order.get(incoming.severity, 0) > sev_order.get(existing.severity, 0):
        existing.severity = incoming.severity

    existing.confidence = max(existing.confidence, incoming.confidence)

    if len(incoming.explanation) > len(existing.explanation):
        existing.explanation = incoming.explanation

    existing.needs_human_review = existing.needs_human_review or incoming.needs_human_review


def run_session_evaluation(
    session: SessionData,
    checks: list[Check],
    window_sec: float = 5.0,
) -> list[Finding]:
    """Runs Path 1 (invariants & engine anomalies) and Path 2 (review windows)."""
    checks_by_id = {c.id: c for c in checks}
    all_violations: list[Violation] = []
    history: list = []

    # 1. Path 1: Check snapshots
    for snap in session.snapshots:
        history.append(snap)
        vs = check_snapshot(snap, checks, history)
        all_violations.extend(vs)

    # 2. Path 1: Check discrete events (including engine anomalies)
    for ev in session.events:
        v = check_event(ev)
        if v:
            all_violations.append(v)

    findings: list[Finding] = violations_to_findings(all_violations, checks_by_id)

    # 3. Path 2: Review windows
    if session.snapshots or session.events:
        all_times = [s.session_time for s in session.snapshots] + [e.session_time for e in session.events]
        max_t = max(all_times) if all_times else 0.0
        cur_t = 0.0
        w_idx = 0

        while cur_t <= max_t + 0.1:
            next_t = cur_t + window_sec
            w_snaps = [s for s in session.snapshots if cur_t <= s.session_time < next_t]
            w_events = [e for e in session.events if cur_t <= e.session_time < next_t]

            if w_snaps or w_events:
                rw = ReviewWindow(
                    window_id=f"w{w_idx:02d}",
                    session_id=session.session_id,
                    scene=w_snaps[0].scene if w_snaps else (w_events[0].scene or ""),
                    start_frame=w_snaps[0].frame if w_snaps else (w_events[0].frame if w_events else 0),
                    end_frame=w_snaps[-1].frame if w_snaps else (w_events[-1].frame if w_events else 0),
                    snapshots=w_snaps,
                    events=w_events,
                    active_checks=checks,
                )
                f = review_window(rw)
                if f:
                    f_key = dedupe_finding_key(f)
                    existing = next((ex for ex in findings if dedupe_finding_key(ex) == f_key), None)
                    if existing is None:
                        findings.append(f)
                    else:
                        merge_findings(existing, f)

            cur_t = next_t
            w_idx += 1

    return findings


def run_evaluation(
    log_path: Optional[str] = None,
    checks_path: Optional[str] = None,
    out_path: Optional[str] = None,
    window_sec: float = 5.0,
    stride: int = 4,
    ignore_checks: bool = True,
) -> dict:
    resolved_log = resolve_log_path(log_path)
    print(f"[eval] Loading game log from: {resolved_log}")

    sessions = load_sessions(resolved_log, stride=stride)
    print(f"[eval] Loaded {len(sessions)} session(s): {list(sessions.keys())}")

    if ignore_checks:
        checks = []
        print("[eval] Ignoring checks.json — Agent-based verification mode active")
    else:
        checks = load_checks(Path(checks_path) if checks_path else None)
        print(f"[eval] Loaded {len(checks)} active invariant check(s)")

    print(f"[eval] Path 2 Judge Mode: {get_llm_status()}")

    all_results = []
    print("\n" + "=" * 70)
    print(f"{'Session ID':<30} {'Events':<8} {'Snaps':<8} {'Findings':<8}")
    print("-" * 70)

    for sid, sess in sessions.items():
        findings = run_session_evaluation(sess, checks, window_sec=window_sec)

        all_results.append({
            "session_id": sid,
            "total_events": len(sess.events),
            "total_snapshots": len(sess.snapshots),
            "findings": [f.model_dump() for f in findings],
        })

        print(f"{sid:<30} {len(sess.events):<8} {len(sess.snapshots):<8} {len(findings):<8}")

    out_file = Path(out_path) if out_path else (RESULTS_DIR / "eval_results.json")
    out_file.write_text(json.dumps(all_results, indent=2), encoding="utf-8")
    print("-" * 70)
    print(f"[eval] Wrote results to: {out_file}\n")

    return {"results": all_results, "output_path": str(out_file)}


def main() -> None:
    parser = argparse.ArgumentParser(description="Game_QA Post-Run Evaluator for Syntax-error Godot Logs")
    parser.add_argument("--log", type=str, default=None, help="Path to game_events.jsonl")
    parser.add_argument("--checks", type=str, default=None, help="Path to checks.json")
    parser.add_argument("--out", type=str, default=None, help="Path to output eval_results.json")
    parser.add_argument("--window", type=float, default=5.0, help="Window size in seconds for Path 2 review")
    parser.add_argument("--stride", type=int, default=4, help="Sampling stride (default: 4)")
    parser.add_argument("--ignore-checks", dest="ignore_checks", action="store_true", default=True, help="Rely on agent audit")
    parser.add_argument("--use-checks", dest="ignore_checks", action="store_false", help="Enable deterministic checks from checks.json")

    args = parser.parse_args()
    run_evaluation(
        log_path=args.log,
        checks_path=args.checks,
        out_path=args.out,
        window_sec=args.window,
        stride=args.stride,
        ignore_checks=args.ignore_checks,
    )


if __name__ == "__main__":
    main()
