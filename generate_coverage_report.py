#!/usr/bin/env python3
"""
generate_coverage_report.py — Offline Coverage Report Generator
for the AI Game Tester Logger (Schema 1.0)

Reads game_events.jsonl, computes PASS/MISSING status for every expected
event in the schema manifest, and writes coverage_report.json.

Usage:
    python generate_coverage_report.py [path/to/game_events.jsonl]

Output:
    coverage_report.json  (same directory as the input file)
"""

import json
import os
import sys
import time
from collections import defaultdict

# ---------------------------------------------------------------------------
# Schema Manifest — mirrors EXPECTED_EVENTS in GameLogger.gd
# ---------------------------------------------------------------------------
EXPECTED_EVENTS = {
    "input": [
        "move_left_pressed", "move_left_released",
        "move_right_pressed", "move_right_released",
        "jump_pressed", "jump_released", "pause_pressed",
        "retry_pressed", "quit_pressed", "main_menu_pressed",
    ],
    "player_movement": [
        "jump_started", "jump_interrupted", "fall_started",
        "fall_distance_threshold_reached", "player_landed",
        "player_left_floor", "player_moved",
    ],
    "player_lifecycle": [
        "player_spawned", "player_died", "player_removed",
        "death_counter_incremented",
    ],
    "enemy": [
        "enemy_spawned", "enemy_started_moving", "enemy_reversed_at_wall",
        "stomp_attempted", "enemy_stomp_area_entered", "enemy_stomped",
        "enemy_contact_started", "enemy_contact_death",
        "enemy_killed", "enemy_removed",
    ],
    "collectible": [
        "coin_spawned", "coin_overlap_started", "coin_picked",
        "coin_score_awarded", "coin_animation_started",
        "coin_remaining_count_changed", "coin_removed",
    ],
    "portal": [
        "portal_entered", "portal_transition_started", "portal_fade_started",
        "portal_fade_completed", "scene_change_requested", "level_completed",
        "portal_target_missing", "scene_load_failed",
    ],
    "scene_lifecycle": [
        "session_start", "session_end", "scene_loaded",
        "level_loaded", "main_screen_loaded", "end_screen_loaded",
    ],
    "ui": [
        "pause_opened", "pause_closed", "death_overlay_shown",
        "death_menu_opened", "score_label_updated", "retry_started",
        "global_state_reset", "return_to_main_menu",
    ],
    "state_snapshot": ["state_snapshot"],
    "anomaly": [
        "player_stuck_detected", "player_out_of_bounds",
        "unexpected_player_removal", "unexpected_score_change",
        "duplicate_pickup_attempt", "missing_expected_object",
        "scene_transition_timeout", "runtime_error_observed",
    ],
}

# Build flat lookup
ALL_EXPECTED: dict[str, str] = {}  # event_name -> category
for cat, evs in EXPECTED_EVENTS.items():
    for ev in evs:
        ALL_EXPECTED[ev] = cat

# ---------------------------------------------------------------------------
# ANSI helpers for terminal output
# ---------------------------------------------------------------------------
GREEN  = "\033[92m"
YELLOW = "\033[93m"
RED    = "\033[91m"
CYAN   = "\033[96m"
BOLD   = "\033[1m"
DIM    = "\033[2m"
RESET  = "\033[0m"


def find_log_file() -> str:
    candidates = [
        os.path.join(os.getcwd(), "game_events.jsonl"),
        os.path.join(os.getcwd(), "godot-4game", "game_events.jsonl"),
        os.path.expandvars(
            r"%APPDATA%\Godot\app_userdata\Your First Game: 2d Platformer\game_events.jsonl"
        ),
    ]
    for c in candidates:
        if os.path.exists(c):
            return c
    return candidates[0]


def read_jsonl(path: str) -> tuple[list[dict], int, int]:
    """Parse the JSONL file, returning (schema_records, legacy_count, error_count)."""
    schema_records: list[dict] = []
    legacy = 0
    errors = 0
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        for lineno, raw in enumerate(f, 1):
            raw = raw.strip()
            if not raw:
                continue
            try:
                obj = json.loads(raw)
            except json.JSONDecodeError:
                errors += 1
                continue
            if "schema_version" not in obj:
                legacy += 1
            else:
                schema_records.append(obj)
    return schema_records, legacy, errors


def build_report(records: list[dict], path: str, legacy: int, errors: int) -> dict:
    """Compute coverage metrics and produce the report dict."""
    # Count occurrences per event name (Schema 1.0 only)
    observed: dict[str, int] = defaultdict(int)
    sessions: set[str] = set()
    anomaly_types: dict[str, int] = defaultdict(int)

    last_eid: dict[str, int] = {}  # session_id -> last event_id
    monotonic_errors = 0

    for r in records:
        ev = r.get("event_name", "?")
        observed[ev] += 1
        sess = r.get("session_id", "")
        if sess:
            sessions.add(sess)
        eid = r.get("event_id", -1)
        if sess in last_eid:
            if eid != last_eid[sess] + 1:
                monotonic_errors += 1
        last_eid[sess] = eid

        if r.get("category") == "anomaly":
            atype = r.get("data", {}).get("anomaly_type", ev)
            anomaly_types[atype] += 1

    # Per-category coverage
    categories: dict[str, dict] = {}
    total_expected = 0
    total_covered = 0
    total_missing = 0

    for cat, event_list in EXPECTED_EVENTS.items():
        covered = [e for e in event_list if observed.get(e, 0) > 0]
        missing = [e for e in event_list if observed.get(e, 0) == 0]
        total_expected += len(event_list)
        total_covered += len(covered)
        total_missing += len(missing)

        ev_detail = []
        for e in event_list:
            count = observed.get(e, 0)
            ev_detail.append({
                "event_name": e,
                "status": "PASS" if count > 0 else "MISSING",
                "count": count,
            })

        categories[cat] = {
            "total_expected": len(event_list),
            "covered": len(covered),
            "missing_count": len(missing),
            "coverage_percent": round(len(covered) / max(len(event_list), 1) * 100, 1),
            "events": ev_detail,
            "missing": missing,
        }

    # Extra events logged that aren't in the schema manifest
    extra_events = {
        ev: cnt for ev, cnt in observed.items()
        if ev not in ALL_EXPECTED and ev != "?"
    }

    coverage_pct = round(total_covered / max(total_expected, 1) * 100, 1)

    return {
        "schema_version": "1.0",
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "log_file": path,
        "sessions_found": len(sessions),
        "integrity": {
            "total_lines": len(records) + legacy + errors,
            "schema_10_records": len(records),
            "legacy_records": legacy,
            "parse_errors": errors,
            "monotonic_id_errors": monotonic_errors,
        },
        "summary": {
            "total_expected_events": total_expected,
            "covered": total_covered,
            "missing": total_missing,
            "coverage_percent": coverage_pct,
            "extra_events_count": len(extra_events),
            "anomalies_logged": sum(anomaly_types.values()),
        },
        "categories": categories,
        "extra_events": extra_events,
        "anomaly_breakdown": dict(anomaly_types),
    }


def print_summary(report: dict) -> None:
    os.system("")  # Enable ANSI on Windows
    s = report["summary"]
    i = report["integrity"]
    pct = s["coverage_percent"]
    color = GREEN if pct >= 90 else (YELLOW if pct >= 70 else RED)

    print("=" * 72)
    print(f" {BOLD}AI GAME TESTER LOGGER — COVERAGE REPORT (Schema 1.0){RESET}")
    print("=" * 72)
    print(f"  Log file : {CYAN}{report['log_file']}{RESET}")
    print(f"  Generated: {report['generated_at']}")
    print(f"  Sessions : {report['sessions_found']}")
    print()
    print(f"  {BOLD}Integrity{RESET}")
    print(f"    Total lines      : {i['total_lines']}")
    print(f"    Schema 1.0 records: {i['schema_10_records']}")
    print(f"    Legacy records   : {YELLOW}{i['legacy_records']}{RESET}")
    print(f"    Parse errors     : {RED if i['parse_errors'] else GREEN}{i['parse_errors']}{RESET}")
    print(f"    Monotonic errors : {RED if i['monotonic_id_errors'] else GREEN}{i['monotonic_id_errors']}{RESET}")
    print()
    print(f"  {BOLD}Event Coverage{RESET}")
    print(f"    Expected : {s['total_expected_events']}")
    print(f"    Covered  : {GREEN}{s['covered']}{RESET}")
    print(f"    Missing  : {RED}{s['missing']}{RESET}")
    print(f"    Coverage : {color}{BOLD}{pct}%{RESET}")
    print(f"    Anomalies: {s['anomalies_logged']}")
    print()
    print(f"  {BOLD}Per-Category Breakdown{RESET}")
    for cat, info in report["categories"].items():
        bar_pct = info["coverage_percent"]
        cat_color = GREEN if bar_pct == 100 else (YELLOW if bar_pct >= 70 else RED)
        miss_str = f"  {RED}MISSING: {info['missing']}{RESET}" if info["missing"] else ""
        print(f"    {cat:<20} {cat_color}{bar_pct:5.1f}%{RESET}  "
              f"({info['covered']}/{info['total_expected']}){miss_str}")
    print("=" * 72)


def main() -> None:
    log_path = sys.argv[1] if len(sys.argv) > 1 else find_log_file()

    if not os.path.exists(log_path):
        print(f"Log file not found: {log_path}")
        print("Run the game first via run_game.bat, then re-run this script.")
        sys.exit(1)

    records, legacy, errors = read_jsonl(log_path)
    report = build_report(records, log_path, legacy, errors)
    print_summary(report)

    out_path = os.path.join(os.path.dirname(log_path) or ".", "coverage_report.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    print(f"\n  {GREEN}Coverage report written to:{RESET} {out_path}\n")


if __name__ == "__main__":
    main()
