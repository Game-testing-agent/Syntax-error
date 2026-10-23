#!/usr/bin/env python3
"""Convert GameLogger.gd game_events.jsonl records into the unique_id-first schema.

Current logger convention:
- unique_id is created as session_id:event_id.
- session_id identifies a game/logger session.
- event_id is a sequence number that restarts at 1 each session.
- timestamp_unix_ms is the event's Unix timestamp in milliseconds.
- physics_frame is the event's physics frame.
- `data` contains the event payload or the detailed state snapshot.

By default this converts and preserves EVERY valid source record. It does not
collapse events by second. Output records are sorted by timestamp, with
untimestamped records retained at the end in their original order.

Usage:
    python convert_game_events_to_schema_v2.py
    python convert_game_events_to_schema_v2.py game_events.jsonl
    python convert_game_events_to_schema_v2.py game_events.jsonl --output converted_game_events.jsonl
    python convert_game_events_to_schema_v2.py game_events.jsonl --latest-per-second

No third-party packages are required.
"""

import argparse
import json
from pathlib import Path
from typing import Any, Dict, Optional, Tuple


def first_present(*values):
    """Return the first value that is not None (preserves valid 0 and False)."""
    for value in values:
        if value is not None:
            return value
    return None


def bool01(value):
    """Convert Boolean values to 1/0; preserve unavailable values as null."""
    if value is None:
        return None
    return 1 if bool(value) else 0


def nested_xy(obj: Dict[str, Any], flat_x: str, flat_y: str, nested_key: str):
    nested = obj.get(nested_key)
    if isinstance(nested, dict):
        return (
            first_present(nested.get("x"), obj.get(flat_x)),
            first_present(nested.get("y"), obj.get(flat_y)),
        )
    return obj.get(flat_x), obj.get(flat_y)


def get_payload(record: Dict[str, Any]) -> Dict[str, Any]:
    payload = record.get("data")
    return payload if isinstance(payload, dict) else {}


def normalized_unix_ms(value: Any) -> Optional[int]:
    """Normalize numeric seconds or milliseconds to integer Unix milliseconds."""
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        return None
    if abs(value) >= 100_000_000_000:
        return int(value)
    return int(round(value * 1000))


def record_timestamp_ms(record: Dict[str, Any], payload: Dict[str, Any]) -> Optional[int]:
    # Current GameLogger convention: root timestamp_unix_ms.
    value = record.get("timestamp_unix_ms")
    if value is not None:
        return normalized_unix_ms(value)

    # Compatibility fallbacks for older logger records.
    value = payload.get("timestamp_unix_ms")
    if value is not None:
        return normalized_unix_ms(value)
    value = record.get("timestamp")
    if value is not None:
        return normalized_unix_ms(value)
    value = payload.get("timestamp")
    return normalized_unix_ms(value)


def get_player(source: Dict[str, Any], record: Dict[str, Any]):
    obj = source.get("player")
    if not isinstance(obj, dict):
        obj = record.get("player")
    if not isinstance(obj, dict):
        return None

    x, y = nested_xy(obj, "x", "y", "position")
    vx, vy = nested_xy(obj, "vel_x", "vel_y", "velocity")
    speed = obj.get("speed_max")
    if not isinstance(speed, dict):
        speed = obj.get("speed")
    hitbox = obj.get("hitbox")
    if not isinstance(hitbox, dict):
        hitbox = {}

    alive = obj.get("alive")
    if alive is None:
        # The event-level player object in GameLogger uses null when absent;
        # a present player object means player information is available.
        alive = True

    return [
        bool01(alive),  # 0 alive
        x,              # 1 world x
        y,              # 2 world y
        vx,             # 3 horizontal velocity
        vy,             # 4 vertical velocity
        bool01(first_present(obj.get("on_floor"), obj.get("grounded"))),  # 5
        bool01(obj.get("on_wall")),       # 6
        bool01(obj.get("on_ceiling")),    # 7
        obj.get("facing"),                # 8
        obj.get("stomp_impulse"),         # 9
        speed.get("x") if isinstance(speed, dict) else None,  # 10
        speed.get("y") if isinstance(speed, dict) else None,  # 11
        hitbox.get("width"),              # 12
        hitbox.get("height"),             # 13
        obj.get("distance_to_ground"),    # 14
        obj.get("distance_to_wall_ahead"),# 15
    ]


def get_player_instance_id(source: Dict[str, Any], record: Dict[str, Any]):
    # State snapshots may have a detailed player in data without an instance ID,
    # while the event envelope's player object still contains the instance ID.
    state_player = source.get("player")
    root_player = record.get("player")
    if isinstance(state_player, dict) and state_player.get("instance_id") is not None:
        return state_player.get("instance_id")
    if isinstance(root_player, dict):
        return root_player.get("instance_id")
    return None


def coin_row(obj):
    if not isinstance(obj, dict):
        return None
    return [
        obj.get("id"),
        obj.get("x"),
        obj.get("y"),
        obj.get("distance"),
        obj.get("relative_x"),
        obj.get("relative_y"),
    ]


def get_coins(source: Dict[str, Any]):
    obj = source.get("coins")
    if not isinstance(obj, dict):
        return None
    all_coins = obj.get("all")
    all_rows = (
        [row for row in (coin_row(coin) for coin in all_coins) if row is not None]
        if isinstance(all_coins, list)
        else None
    )
    return [
        obj.get("coins_collected"),
        obj.get("coins_remaining"),
        coin_row(obj.get("nearest_coin")),
        all_rows,
    ]


def enemy_row(obj):
    if not isinstance(obj, dict):
        return None
    return [
        obj.get("id"),
        obj.get("name"),
        obj.get("x"),
        obj.get("y"),
        first_present(obj.get("vel_x"), obj.get("velocity_x")),
        obj.get("distance"),
        obj.get("relative_x"),
        obj.get("relative_y"),
        bool01(obj.get("player_is_above")),
        bool01(obj.get("is_stompable")),
        bool01(obj.get("is_threat")),
    ]


def get_enemies(source: Dict[str, Any]):
    obj = source.get("enemies")
    if not isinstance(obj, dict):
        return None
    all_enemies = obj.get("all")
    all_rows = (
        [row for row in (enemy_row(enemy) for enemy in all_enemies) if row is not None]
        if isinstance(all_enemies, list)
        else None
    )
    return [obj.get("count"), enemy_row(obj.get("closest_enemy")), all_rows]


def get_inputs(source: Dict[str, Any]):
    obj = source.get("inputs")
    if not isinstance(obj, dict):
        return None
    raw = obj.get("raw_direction")
    if not isinstance(raw, dict):
        raw = {}
    return [
        bool01(obj.get("move_left")),
        bool01(obj.get("move_right")),
        bool01(obj.get("jump")),
        bool01(obj.get("jump_just_pressed")),
        bool01(obj.get("pause")),
        raw.get("x"),
        raw.get("y"),
    ]


def get_goal(source: Dict[str, Any]):
    obj = source.get("goal")
    if not isinstance(obj, dict):
        return None
    return [
        bool01(obj.get("found")),
        obj.get("portal_x"),
        obj.get("portal_y"),
        obj.get("distance_to_portal"),
        obj.get("relative_x"),
        obj.get("relative_y"),
    ]


def get_stats(record: Dict[str, Any], source: Dict[str, Any]):
    stats = source.get("stats")
    if not isinstance(stats, dict):
        stats = {}
    root_state = record.get("game_state")
    if not isinstance(root_state, dict):
        root_state = {}
    return [
        first_present(stats.get("score"), source.get("score"), root_state.get("score")),
        first_present(stats.get("deaths"), source.get("deaths"), root_state.get("deaths")),
    ]


def get_paused(record: Dict[str, Any]):
    state = record.get("game_state")
    if isinstance(state, dict):
        value = state.get("paused")
        return bool(value) if value is not None else None
    return None


def get_recent_actions(record: Dict[str, Any]):
    context = record.get("action_context")
    if not isinstance(context, dict):
        return None
    actions = context.get("recent_actions")
    if not isinstance(actions, list):
        return None
    return [
        [
            action.get("action"),
            action.get("physics_frame"),
            action.get("timestamp_unix_ms"),
        ]
        for action in actions
        if isinstance(action, dict)
    ]


def get_extra(record: Dict[str, Any], payload: Dict[str, Any], source: Dict[str, Any]):
    """Keep source-specific data not already represented in the standard fields."""
    extras = {}

    # Preserve event data in full for normal event records. For snapshots, fields
    # already represented in arrays/scalars are omitted; unknown fields survive.
    is_snapshot = any(key in payload for key in (
        "player", "inputs", "coins", "enemies", "goal", "stats"
    ))
    if payload:
        if not is_snapshot:
            extras["data"] = payload
        else:
            represented_payload_keys = {
                "frame", "physics_frame", "timestamp", "timestamp_unix_ms",
                "session_time", "fps", "game_state", "scene", "stats",
                "player", "inputs", "coins", "enemies", "goal", "event",
            }
            remaining_payload = {
                key: value for key, value in payload.items()
                if key not in represented_payload_keys
            }
            if remaining_payload:
                extras["data_extra"] = remaining_payload

    # Preserve any unexpected root fields rather than silently dropping them.
    root_fields = {
        "schema_version", "session_id", "event_id", "event_name", "category",
        "timestamp_unix_ms", "elapsed_ms", "physics_frame", "scene", "player",
        "game_state", "entity", "action_context", "evidence", "data",
    }
    unknown_root = {key: value for key, value in record.items() if key not in root_fields}
    if unknown_root:
        extras["root_extra"] = unknown_root

    # A snapshot carries a secondary timestamp in seconds inside `data`; it is
    # promoted to state_timestamp_unix_ms. Preserve the original event marker too.
    if source.get("event") is not None and is_snapshot:
        extras["state_event"] = source.get("event")

    return extras or None


def make_unique_id(record: Dict[str, Any], source_line_number: int) -> str:
    """Build an event identity from the logger's session_id and event_id.

    The current GameLogger convention has both fields. For older/malformed
    records without both fields, use a file-line fallback so no converted
    input record receives a duplicate unique_id within this conversion.
    """
    session_id = record.get("session_id")
    event_id = record.get("event_id")
    if session_id is not None and event_id is not None:
        return f"{session_id}:{event_id}"
    return f"legacy-line:{source_line_number}"


def compact_record(record: Dict[str, Any], source_line_number: int = 0) -> Dict[str, Any]:
    payload = get_payload(record)
    # State snapshots have their state dictionary inside data; ordinary events
    # have event-specific payload data and their player/entity context at root.
    has_state_payload = any(key in payload for key in (
        "player", "inputs", "coins", "enemies", "goal", "stats", "game_state"
    ))
    source = payload if has_state_payload else record

    timestamp_ms = record_timestamp_ms(record, payload)
    state_timestamp_ms = normalized_unix_ms(payload.get("timestamp")) if "timestamp" in payload else None
    if payload.get("timestamp_unix_ms") is not None:
        state_timestamp_ms = normalized_unix_ms(payload.get("timestamp_unix_ms"))

    event_name = first_present(record.get("event_name"), payload.get("event"), record.get("event"))
    root_scene = record.get("scene")
    state_scene = payload.get("scene") if has_state_payload else None
    if root_scene is None:
        root_scene = state_scene

    # Keep root physics frame and snapshot's inner physics frame separately.
    event_physics_frame = first_present(record.get("physics_frame"), source.get("physics_frame"))
    state_physics_frame = payload.get("physics_frame") if has_state_payload else None
    frame = payload.get("frame") if has_state_payload else source.get("frame")

    session_time = source.get("session_time") if has_state_payload else None
    fps = source.get("fps") if has_state_payload else None

    return {
        "unique_id": make_unique_id(record, source_line_number),
        "schema_version": record.get("schema_version"),
        "session_id": record.get("session_id"),
        "event_id": record.get("event_id"),
        "event_name": event_name,
        "category": record.get("category"),
        "timestamp_unix_ms": timestamp_ms,
        "elapsed_ms": record.get("elapsed_ms"),
        "physics_frame": event_physics_frame,
        "frame": frame,
        "state_physics_frame": state_physics_frame,
        "state_timestamp_unix_ms": state_timestamp_ms,
        "session_time": session_time,
        "fps": fps,
        "scene": root_scene,
        "state_scene": state_scene,
        "game_state": source.get("game_state") if isinstance(source.get("game_state"), str) else None,
        "paused": get_paused(record),
        "stats": get_stats(record, source),
        "player_instance_id": get_player_instance_id(source, record),
        "player": get_player(source, record),
        "inputs": get_inputs(source),
        "coins": get_coins(source),
        "enemies": get_enemies(source),
        "goal": get_goal(source),
        "entity": record.get("entity"),
        "recent_actions": get_recent_actions(record),
        "evidence": record.get("evidence"),
        "extra": get_extra(record, payload, source),
    }


def main():
    parser = argparse.ArgumentParser(
        description="Convert GameLogger.gd events to the unique_id-first fixed schema."
    )
    parser.add_argument("input", nargs="?", default="game_events.jsonl",
                        help="Input file (default: game_events.jsonl)")
    parser.add_argument("--output", default="converted_game_events.jsonl",
                        help="Output file (default: converted_game_events.jsonl)")
    parser.add_argument(
        "--latest-per-second", action="store_true",
        help="Optional lossy mode: keep only the latest event per second within each session.",
    )
    args = parser.parse_args()

    input_path = Path(args.input)
    output_path = Path(args.output)
    if not input_path.is_file():
        parser.error(f"Input file not found: {input_path}")

    records = []
    valid_count = 0
    missing_timestamp_count = 0
    malformed_count = 0

    with input_path.open("r", encoding="utf-8") as infile:
        for line_number, line in enumerate(infile, 1):
            line = line.strip()
            if not line:
                continue
            try:
                raw = json.loads(line)
            except json.JSONDecodeError:
                malformed_count += 1
                print(f"Warning: malformed JSON on line {line_number}; skipped.")
                continue
            if not isinstance(raw, dict):
                malformed_count += 1
                print(f"Warning: line {line_number} is not a JSON object; skipped.")
                continue

            converted = compact_record(raw, source_line_number=line_number)
            if converted["timestamp_unix_ms"] is None:
                missing_timestamp_count += 1
            records.append((line_number, converted))
            valid_count += 1

    # Optional per-session per-second reduction; by default every valid record is kept.
    if args.latest_per_second:
        selected = {}
        for line_number, record in records:
            session = record["session_id"] or "unknown_session"
            ts = record["timestamp_unix_ms"]
            if ts is None:
                # Never discard records just because they lack timestamps.
                selected[("untimed", line_number)] = (line_number, record)
                continue
            key = (session, ts // 1000)
            prev = selected.get(key)
            if prev is None or (
                record["timestamp_unix_ms"] >= prev[1]["timestamp_unix_ms"]
            ):
                selected[key] = (line_number, record)
        records = list(selected.values())

    # Sort timestamped records by time, preserving input order for ties.
    # Keep untimestamped records at the end in their original relative order.
    records.sort(key=lambda pair: (
        pair[1]["timestamp_unix_ms"] is None,
        pair[1]["timestamp_unix_ms"] if pair[1]["timestamp_unix_ms"] is not None else 0,
        pair[0],
    ))

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as outfile:
        for _, record in records:
            outfile.write(json.dumps(record, separators=(",", ":"), ensure_ascii=False) + "\n")

    print(f"Converted records: {len(records)}")
    print(f"Malformed/non-object lines skipped: {malformed_count}")
    print(f"Records without usable timestamp: {missing_timestamp_count} (preserved with null timestamp)")
    print(f"Saved to: {output_path.resolve()}")


if __name__ == "__main__":
    main()
