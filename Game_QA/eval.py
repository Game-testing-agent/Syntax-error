"""Post-Run QA Evaluator: Ingests Godot game_events.jsonl, runs Path 1 + Path 2 checks, scores results."""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Optional, Union

from checker import check_event, check_snapshot, violations_to_findings
from llm import get_llm_status, review_window
from loader import load_sessions, resolve_log_path
from schemas import Check, Finding, ReviewWindow, SessionData, Severity, Truth, Verdict, Violation

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


FRAME_TOLERANCE_FRAMES = 120


def _normalize_code(code_str: Optional[str]) -> tuple[str, str]:
    """Returns (normalized_file, normalized_function/symbol)."""
    if not code_str:
        return ("", "")
    s = code_str.strip().replace("\\", "/")
    m = re.search(r"(\w+\.gd)", s, re.IGNORECASE)
    fname = m.group(1).lower() if m else ""
    fn_m = re.search(r"\((_?\w+)\)", s)
    if fn_m:
        fn_name = fn_m.group(1).lower()
    else:
        parts = s.split(":")
        fn_name = parts[1].strip().lower() if len(parts) > 1 and not parts[1].strip().startswith("L") else ""
    return (fname, fn_name)


SEVERITY_ORDER = {
    Severity.critical: 4,
    Severity.high: 3,
    Severity.medium: 2,
    Severity.low: 1,
}


def dedupe_finding_key(f: Finding) -> str:
    """Computes deduplication key based on normalized suspected_code, falling back to title."""
    if f.suspected_code and f.suspected_code.strip():
        s = f.suspected_code.strip().replace("\\", "/").lower()
        m = re.search(r"(\w+\.gd)(?::l?(\d+)(?:-\d+)?)?", s)
        if m:
            base = m.group(1)
            line = m.group(2) or ""
            return f"{base}:{line}"
        return s
    return f.title.strip().lower()


def merge_findings(existing: Finding, incoming: Finding) -> None:
    """Merges incoming finding into existing finding based on same root cause."""
    combined_frames = set(existing.evidence_frames) | set(incoming.evidence_frames)
    existing.evidence_frames = sorted(list(combined_frames))

    existing_sev_val = SEVERITY_ORDER.get(existing.severity, 0) if existing.severity else 0
    incoming_sev_val = SEVERITY_ORDER.get(incoming.severity, 0) if incoming.severity else 0
    if incoming_sev_val > existing_sev_val:
        existing.severity = incoming.severity

    existing.confidence = max(existing.confidence, incoming.confidence)

    if len(incoming.explanation) > len(existing.explanation):
        existing.explanation = incoming.explanation

    if incoming.title and "Engine Anomaly:" in existing.title:
        existing.title = incoming.title
        existing.suspected_code = incoming.suspected_code
        existing.path = incoming.path

    existing.needs_human_review = existing.needs_human_review or incoming.needs_human_review


def load_truth(truth_path: Optional[Path] = None) -> dict[str, dict]:
    path = truth_path or (DATA_DIR / "truth.json")
    if not path.exists():
        return {}
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        return raw if isinstance(raw, dict) else {}
    except Exception as exc:
        print(f"[eval] Warning: could not parse truth.json: {exc}")
        return {}


def run_session_evaluation(
    session: SessionData,
    checks: list[Check],
    window_sec: float = 5.0,
) -> list[Finding]:
    """Runs Path 1 (invariants & engine anomalies) and Path 2 (LLM review windows)."""
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
        # Determine time span
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


def score_session(findings: list[Finding], truth: Optional[Union[dict, Truth]]) -> dict:
    if not truth:
        return {"matched": [], "false_positives": [f.model_dump() for f in findings], "n_findings": len(findings)}

    truth_dict = truth.model_dump() if isinstance(truth, Truth) else dict(truth)
    sid = truth_dict.get("session_id", "")
    expected_bugs = truth_dict.get("expected_bugs", [])

    # Validate that truth entries have evidence grounding (frames or suspected code)
    for exp in expected_bugs:
        exp_title = exp.get("title", "")
        exp_frames = exp.get("evidence_frames") or ([exp.get("frame_approx")] if exp.get("frame_approx") is not None else [])
        exp_code = exp.get("suspected_code")
        if not exp_frames and not exp_code:
            raise ValueError(
                f"[eval] Scoring refused: truth entry '{exp_title}' in session '{sid}' "
                f"has neither evidence_frames nor suspected_code."
            )

    matched = []
    used_finding_indices: set[int] = set()

    for exp in expected_bugs:
        exp_title = exp.get("title", "").strip()
        exp_cat = exp.get("category", "").strip().lower()
        exp_frames = exp.get("evidence_frames") or ([exp.get("frame_approx")] if exp.get("frame_approx") is not None else [])
        exp_code = exp.get("suspected_code")
        exp_file, exp_func = _normalize_code(exp_code)

        matched_finding_idx: Optional[int] = None

        for idx, f in enumerate(findings):
            if idx in used_finding_indices:
                continue

            # Unsure or non-bug verdicts are never counted as hits
            if f.verdict != Verdict.bug:
                continue

            # 1. Title or category similarity check (explanation substring match is completely eliminated)
            norm_exp_title = exp_title.lower()
            norm_f_title = f.title.lower()
            title_match = (
                norm_exp_title in norm_f_title
                or norm_f_title in norm_exp_title
                or (bool(exp_cat) and exp_cat in norm_f_title)
            )

            if not title_match:
                continue

            # 2. Evidence Grounding: frame proximity OR file+function match
            frame_match = False
            if exp_frames and f.evidence_frames:
                frame_match = any(
                    abs(ff - tf) <= FRAME_TOLERANCE_FRAMES
                    for ff in f.evidence_frames
                    for tf in exp_frames
                )

            code_match = False
            if exp_file:
                f_file, f_func = _normalize_code(f.suspected_code)
                if f_file and f_file == exp_file:
                    if not exp_func or not f_func or f_func == exp_func:
                        code_match = True

            if frame_match or code_match:
                matched_finding_idx = idx
                break

        if matched_finding_idx is not None:
            used_finding_indices.add(matched_finding_idx)
            hit = findings[matched_finding_idx]
            matched.append({
                "expected": exp_title,
                "found": True,
                "path": hit.path,
                "should_be": exp.get("should_be_caught_by", "path1"),
            })
        else:
            matched.append({
                "expected": exp_title,
                "found": False,
                "path": None,
                "should_be": exp.get("should_be_caught_by", "path1"),
            })

    # All findings not matched 1-to-1 to a truth entry are false positives
    fp = [findings[i].model_dump() for i in range(len(findings)) if i not in used_finding_indices]

    return {
        "session_id": sid,
        "matched": matched,
        "false_positives": fp,
        "n_findings": len(findings),
    }


def run_evaluation(
    log_path: Optional[str] = None,
    checks_path: Optional[str] = None,
    truth_path: Optional[str] = None,
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
        print("[eval] Ignoring checks.json & check.json — Pure LLM Intelligence Mode active!")
    else:
        checks = load_checks(Path(checks_path) if checks_path else None)
        print(f"[eval] Loaded {len(checks)} active invariant check(s)")

    print(f"[eval] Path 2 Judge Mode: {get_llm_status()}")

    truth_map = load_truth(Path(truth_path) if truth_path else None)
    if truth_map:
        print(f"[eval] Loaded ground truth for {len(truth_map)} session(s)")

    all_results = []
    print("\n" + "=" * 70)
    print(f"{'Session ID':<30} {'Events':<8} {'Snaps':<8} {'Findings':<8}")
    print("-" * 70)

    for sid, sess in sessions.items():
        findings = run_session_evaluation(sess, checks, window_sec=window_sec)
        score_res = score_session(findings, truth_map.get(sid))

        all_results.append({
            "session_id": sid,
            "total_events": len(sess.events),
            "total_snapshots": len(sess.snapshots),
            "findings": [f.model_dump() for f in findings],
            "score": score_res,
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
    parser.add_argument("--truth", type=str, default=None, help="Path to truth.json")
    parser.add_argument("--out", type=str, default=None, help="Path to output eval_results.json")
    parser.add_argument("--window", type=float, default=5.0, help="Window size in seconds for Path 2 review")
    parser.add_argument("--stride", type=int, default=4, help="Sampling stride (default: 4, loads line 1, then multiples of 4: 4, 8, 12...)")
    parser.add_argument("--ignore-checks", dest="ignore_checks", action="store_true", default=True, help="Rely completely on LLM intelligence, ignoring checks.json (default)")
    parser.add_argument("--use-checks", dest="ignore_checks", action="store_false", help="Enable deterministic checks from checks.json")

    args = parser.parse_args()
    run_evaluation(
        log_path=args.log,
        checks_path=args.checks,
        truth_path=args.truth,
        out_path=args.out,
        window_sec=args.window,
        stride=args.stride,
        ignore_checks=args.ignore_checks,
    )


if __name__ == "__main__":
    main()
