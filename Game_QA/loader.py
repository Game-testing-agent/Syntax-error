"""Log loader and session parser for Godot AI telemetry (game_events.jsonl & latest_state.json)."""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Optional

from schemas import Event, SessionData, Snapshot


ROOT = Path(__file__).resolve().parent

# Locate project workspace root:
# If Game_QA is inside Syntax-error, ROOT.parent is workspace root.
# If Game_QA is a sibling to Syntax-error, ROOT.parent / "Syntax-error" is workspace root.
WORKSPACE_ROOT = (
    ROOT.parent
    if (ROOT.parent / "godot-4game").exists() or (ROOT.parent / "game_events.jsonl").exists()
    else (ROOT.parent / "Syntax-error" if (ROOT.parent / "Syntax-error").exists() else ROOT)
)

DEFAULT_SEARCH_PATHS = [
    # Primary workspace root logs
    WORKSPACE_ROOT / "game_events.jsonl",
    WORKSPACE_ROOT / "godot-4game" / "game_events.jsonl",
    # Local to Game_QA
    ROOT / "game_events.jsonl",
    ROOT / "telemetry" / "game_events.jsonl",
    ROOT / "_private" / "telemetry" / "game_events_original.jsonl",
    # Current working directory
    Path("game_events.jsonl"),
    Path("godot-4game") / "game_events.jsonl",
    Path("..") / "game_events.jsonl",
    # Benchmark map logs
    WORKSPACE_ROOT / "maps" / "map1_green_hills" / "logs" / "game_events.jsonl",
    WORKSPACE_ROOT / "maps" / "map2_underground_caves" / "logs" / "game_events.jsonl",
    WORKSPACE_ROOT / "maps" / "map3_sky_castle" / "logs" / "game_events.jsonl",
    WORKSPACE_ROOT / "maps" / "map4_lava_fortress" / "logs" / "game_events.jsonl",
    # Sample / fallback datasets
    WORKSPACE_ROOT / "sample_game_events.jsonl",
    ROOT / "sample_game_events.jsonl",
    # Sibling fallback
    ROOT.parent / "Syntax-error" / "game_events.jsonl",
    ROOT.parent / "Syntax-error" / "godot-4game" / "game_events.jsonl",
    ROOT.parent / "Syntax-error" / "sample_game_events.jsonl",
]


def resolve_log_path(user_path: Optional[str] = None) -> Path:
    """Finds the log file given an optional user path or searches default locations."""
    if user_path:
        p = Path(user_path)
        if p.exists():
            return p.resolve()
        # Also check relative to WORKSPACE_ROOT and ROOT
        if (WORKSPACE_ROOT / user_path).exists():
            return (WORKSPACE_ROOT / user_path).resolve()
        if (ROOT / user_path).exists():
            return (ROOT / user_path).resolve()
        raise FileNotFoundError(f"Specified log file not found: {user_path}")

    # 1. Primary real game log: always prefer game_events.jsonl (even if currently 0 bytes / fresh)
    primary_paths = [
        WORKSPACE_ROOT / "game_events.jsonl",
        WORKSPACE_ROOT / "godot-4game" / "game_events.jsonl",
        Path("game_events.jsonl"),
        Path("godot-4game") / "game_events.jsonl",
        Path("..") / "game_events.jsonl",
        ROOT / "game_events.jsonl",
        ROOT / "telemetry" / "game_events.jsonl",
        ROOT / "_private" / "telemetry" / "game_events_original.jsonl",
        ROOT.parent / "Syntax-error" / "game_events.jsonl",
        ROOT.parent / "Syntax-error" / "godot-4game" / "game_events.jsonl",
    ]
    for p in primary_paths:
        if p.exists():
            return p.resolve()

    # 2. Benchmark map logs
    map_log_paths = [
        WORKSPACE_ROOT / "maps" / "map1_green_hills" / "logs" / "game_events.jsonl",
        WORKSPACE_ROOT / "maps" / "map2_underground_caves" / "logs" / "game_events.jsonl",
        WORKSPACE_ROOT / "maps" / "map3_sky_castle" / "logs" / "game_events.jsonl",
        WORKSPACE_ROOT / "maps" / "map4_lava_fortress" / "logs" / "game_events.jsonl",
    ]
    for p in map_log_paths:
        if p.exists():
            return p.resolve()

    # 3. Fallback to sample data ONLY if real game_events.jsonl does not exist at all
    sample_paths = [
        WORKSPACE_ROOT / "sample_game_events.jsonl",
        ROOT / "sample_game_events.jsonl",
        ROOT.parent / "Syntax-error" / "sample_game_events.jsonl",
        ROOT / "_private" / "telemetry" / "game_events_original.jsonl",
    ]
    for sample_path in sample_paths:
        if sample_path.exists():
            return sample_path.resolve()

    raise FileNotFoundError(
        "Could not automatically locate game_events.jsonl in Syntax-error workspace. "
        "Please provide --log <path>."
    )


def _normalize_player_dict(player: dict) -> dict:
    """Ensures player dictionary has convenient direct x, y, vel_x, vel_y fields."""
    if not isinstance(player, dict):
        return {}
    res = dict(player)
    pos = res.get("position")
    if isinstance(pos, dict):
        res.setdefault("x", pos.get("x", 0.0))
        res.setdefault("y", pos.get("y", 0.0))
    vel = res.get("velocity")
    if isinstance(vel, dict):
        res.setdefault("vel_x", vel.get("x", 0.0))
        res.setdefault("vel_y", vel.get("y", 0.0))
    return res


def load_sessions(log_path: Path, stride: int = 4, keep_anomalies: bool = True) -> dict[str, SessionData]:
    """Parses a game_events.jsonl file into grouped SessionData objects.

    Args:
        log_path: Path to game_events.jsonl.
        stride: Sampling interval. If stride=4, samples line 1, then line 4, 8, 12... (multiples of 4).
                Set stride=1 to load every log line.
        keep_anomalies: Always preserves explicit anomaly events regardless of stride.
    """
    sessions: dict[str, SessionData] = {}
    total_lines = 0
    sampled_lines = 0
    snapshot_idx = 0
    malformed_count = 0

    with open(log_path, "r", encoding="utf-8") as f:
        for line_no, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            total_lines += 1

            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                malformed_count += 1
                continue

            # Validate required session_id
            session_id = record.get("session_id")
            if not session_id or not isinstance(session_id, str):
                malformed_count += 1
                continue

            category = record.get("category")
            data = record.get("data", {})
            event_name = record.get("event_name") or record.get("event")
            data_event = data.get("event") if isinstance(data, dict) else None

            # Distinguish snapshots from discrete events
            is_snapshot = (
                category == "state_snapshot"
                or event_name == "state_snapshot"
                or data_event == "state_snapshot"
            )

            # If not a snapshot, record MUST have a valid event_name or event string
            if not is_snapshot:
                if not event_name or not isinstance(event_name, str):
                    malformed_count += 1
                    continue
                is_event = True
            else:
                is_event = False

            # Stride sampling: NEVER skip discrete events; thin only snapshots
            if is_snapshot:
                snapshot_idx += 1
                if stride > 1:
                    is_selected = (snapshot_idx == 1) or (snapshot_idx % stride == 0)
                    if not is_selected:
                        continue
            elif is_event:
                # Discrete events are NEVER skipped
                pass
            else:
                print(f"[loader] Warning: Line {line_no} matches neither snapshot nor event; keeping line.")

            sampled_lines += 1
            if session_id not in sessions:
                sessions[session_id] = SessionData(session_id=session_id)

            sess = sessions[session_id]

            # Common timing fields
            phys_frame = record.get("physics_frame")
            if phys_frame is None:
                phys_frame = record.get("data", {}).get("frame", 0)

            if "elapsed_ms" in record:
                s_time = float(record["elapsed_ms"]) / 1000.0
            else:
                s_time = float(record.get("data", {}).get("session_time", 0.0))

            if "timestamp_unix_ms" in record:
                ts = float(record["timestamp_unix_ms"]) / 1000.0
            else:
                ts = float(record.get("data", {}).get("timestamp", 0.0))

            scene = record.get("scene") or record.get("data", {}).get("scene") or ""
            evidence = record.get("evidence", {})

            # Parse state snapshot or discrete event
            if is_snapshot:
                if isinstance(data, dict):
                    snap_player = _normalize_player_dict(data.get("player", {}))
                    snap = Snapshot(
                        frame=int(data.get("frame", phys_frame or 0)),
                        session_time=float(data.get("session_time", s_time)),
                        timestamp=float(data.get("timestamp", ts)),
                        scene=str(data.get("scene", scene)),
                        game_state=str(data.get("game_state", "")),
                        fps=float(data.get("fps", 60.0)),
                        player=snap_player,
                        enemies=data.get("enemies", {}) if isinstance(data.get("enemies"), dict) else {},
                        coins=data.get("coins", {}) if isinstance(data.get("coins"), dict) else {},
                        goal=data.get("goal", {}) if isinstance(data.get("goal"), dict) else {},
                        inputs=data.get("inputs", {}) if isinstance(data.get("inputs"), dict) else {},
                        stats=data.get("stats", {}) if isinstance(data.get("stats"), dict) else {},
                    )
                    sess.snapshots.append(snap)
            else:
                # Merge top-level entity, player, and game_state into event payload for rich context
                if isinstance(data, dict):
                    merged_payload = dict(data)
                    if "player" in record and "player" not in merged_payload:
                        merged_payload["player"] = record["player"]
                    if "entity" in record and "entity" not in merged_payload:
                        merged_payload["entity"] = record["entity"]
                    if "game_state" in record and "game_state" not in merged_payload:
                        merged_payload["game_state"] = record["game_state"]
                else:
                    merged_payload = {"raw": data}

                event_obj = Event(
                    event=event_name,
                    frame=int(phys_frame or 0),
                    session_time=s_time,
                    timestamp=ts,
                    scene=scene,
                    category=category,
                    payload=merged_payload,
                    evidence=evidence if isinstance(evidence, dict) else {},
                )
                sess.events.append(event_obj)

    # Sort items within each session chronologically
    for sess in sessions.values():
        sess.events.sort(key=lambda e: (e.frame, e.session_time))
        sess.snapshots.sort(key=lambda s: (s.frame, s.session_time))

    if malformed_count > 0:
        print(f"[loader] Skipped {malformed_count} malformed record(s)")

    if stride > 1:
        print(f"[loader] Stride {stride} sampling: loaded {sampled_lines} / {total_lines} lines (1st, 4th, 8th, 12th...)")

    return sessions


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Inspect Godot Telemetry Sessions")
    parser.add_argument("--log", type=str, default=None, help="Path to log file")
    parser.add_argument("--stride", type=int, default=1, help="Sampling stride (default 1)")
    parser.add_argument("--session", type=str, default=None, help="Filter to specific session ID")
    parser.add_argument("--limit", type=int, default=30, help="Max events to display")
    args = parser.parse_args()

    log_path = resolve_log_path(args.log)
    sessions = load_sessions(log_path, stride=args.stride)
    print(f"\nLoaded {len(sessions)} session(s) from {log_path}:")
    for sid, s in sessions.items():
        if args.session and sid != args.session:
            continue
        print(f"\n=== Session: {sid} (Events: {len(s.events)}, Snapshots: {len(s.snapshots)}) ===")
        anomalies = [e for e in s.events if e.category == "anomaly"]
        if anomalies:
            print(f"  [Anomalies Found: {len(anomalies)}]")
            for a in anomalies:
                print(f"    - Frame {a.frame}: {a.event} -> {a.payload}")
        print(f"  [Sample Events (first {min(args.limit, len(s.events))} of {len(s.events)})]:")
        for e in s.events[:args.limit]:
            payload_str = str(e.payload)
            if len(payload_str) > 70:
                payload_str = payload_str[:67] + "..."
            print(f"    Frame {e.frame:5d} | {e.category or 'event':15s} | {e.event:25s} | {payload_str}")


