"""CLI tool for Antigravity Agent to submit validated findings to the pipeline cache.

Usage:
  python tools/native_submit.py --session <session_id> --window <window_id> --findings <findings_json_file>
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Ensure repo root is on sys.path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from code_loader import get_game_codebase_context
from llm import _cache_put, window_cache_key
from loader import load_sessions, resolve_log_path
from schemas import Finding, ReviewWindow, Verdict


def submit_finding(
    session_id: str,
    window_id: str,
    findings_path: Path,
    log_path: str | None = None,
    stride: int = 4,
    window_sec: float = 5.0,
) -> Path:
    resolved_log = resolve_log_path(log_path)
    sessions = load_sessions(resolved_log, stride=stride)

    if session_id not in sessions:
        raise ValueError(f"Session '{session_id}' not found in telemetry log {resolved_log}")

    sess = sessions[session_id]

    # Reconstruct windows identically to eval.py
    all_times = [s.session_time for s in sess.snapshots] + [e.session_time for e in sess.events]
    max_t = max(all_times) if all_times else 0.0

    target_window = None
    cur_t = 0.0
    w_idx = 0

    while cur_t <= max_t + 0.1:
        next_t = cur_t + window_sec
        w_snaps = [s for s in sess.snapshots if cur_t <= s.session_time < next_t]
        w_events = [e for e in sess.events if cur_t <= e.session_time < next_t]

        curr_id = f"w{w_idx:02d}"
        if curr_id == window_id:
            target_window = ReviewWindow(
                window_id=curr_id,
                session_id=sess.session_id,
                scene=w_snaps[0].scene if w_snaps else (w_events[0].scene or ""),
                start_frame=w_snaps[0].frame if w_snaps else (w_events[0].frame if w_events else 0),
                end_frame=w_snaps[-1].frame if w_snaps else (w_events[-1].frame if w_events else 0),
                snapshots=w_snaps,
                events=w_events,
                active_checks=[],
            )
            break

        cur_t = next_t
        w_idx += 1

    if not target_window:
        raise ValueError(f"Window '{window_id}' could not be constructed for session '{session_id}'")

    # Load and validate findings file
    raw_data = json.loads(findings_path.read_text(encoding="utf-8"))
    if isinstance(raw_data, list):
        if not raw_data:
            raise ValueError("Findings JSON array is empty")
        finding_obj = Finding.model_validate(raw_data[0])
    elif isinstance(raw_data, dict):
        finding_obj = Finding.model_validate(raw_data)
    else:
        raise ValueError(f"Unexpected findings format in {findings_path}")

    # Compute content-addressed cache key
    code_context = get_game_codebase_context(target_window.events)
    cache_path = window_cache_key(target_window, code_context)

    # Write validated finding to cache
    _cache_put(cache_path, finding_obj.model_dump())
    print(f"[native_submit] Successfully submitted finding for {session_id} / {window_id}")
    print(f"  Title: {finding_obj.title}")
    print(f"  Cache key: {cache_path}")
    return cache_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Submit Agent Findings to Game_QA Pipeline Cache")
    parser.add_argument("--session", required=True, help="Session ID")
    parser.add_argument("--window", required=True, help="Window ID (e.g. w00)")
    parser.add_argument("--findings", required=True, help="Path to findings JSON file")
    parser.add_argument("--log", default=None, help="Path to log file")
    parser.add_argument("--stride", type=int, default=4, help="Sampling stride")
    parser.add_argument("--window-sec", type=float, default=5.0, help="Window duration in seconds")

    args = parser.parse_args()
    submit_finding(
        session_id=args.session,
        window_id=args.window,
        findings_path=Path(args.findings),
        log_path=args.log,
        stride=args.stride,
        window_sec=args.window_sec,
    )


if __name__ == "__main__":
    main()

