"""
Interactive Live Log Viewer & Event Inspector for the Structured GameLogger.
Displays real-time JSON events (Schema 1.0), anomalies, recent action contexts,
and allows inspecting historical session data.
"""

import os
import sys
import json
import time
from typing import Optional, Dict, Any

EVENT_FILE = "game_events.jsonl"
STATE_FILE = "latest_state.json"

# ANSI Colors for terminal output
COLOR_RESET = "\033[0m"
COLOR_CYAN = "\033[96m"
COLOR_GREEN = "\033[92m"
COLOR_YELLOW = "\033[93m"
COLOR_RED = "\033[91m"
COLOR_MAGENTA = "\033[95m"
COLOR_BOLD = "\033[1m"
COLOR_DIM = "\033[2m"

CATEGORY_COLORS = {
    "input": COLOR_CYAN,
    "player_movement": COLOR_GREEN,
    "player_lifecycle": COLOR_YELLOW,
    "enemy": COLOR_RED,
    "collectible": "\033[33m", # Orange/gold
    "portal": COLOR_MAGENTA,
    "scene_lifecycle": COLOR_CYAN,
    "ui": COLOR_CYAN,
    "state_snapshot": COLOR_DIM,
    "anomaly": "\033[41;97m", # White text on red background
    "runtime_error": "\033[41;97m"
}


def find_log_file() -> str:
    """Finds game_events.jsonl in current directory, godot-4game, or user data."""
    paths_to_check = [
        os.path.join(os.getcwd(), EVENT_FILE),
        os.path.join(os.getcwd(), "godot-4game", EVENT_FILE),
        os.path.expandvars(r"%APPDATA%\Godot\app_userdata\Your First Game: 2d Platformer\game_events.jsonl"),
        os.path.expandvars(r"%APPDATA%\Godot\app_userdata\Your First Game- 2d Platformer\game_events.jsonl")
    ]
    for p in paths_to_check:
        if os.path.exists(p):
            return p
    return paths_to_check[0]


def format_event_line(record: Dict[str, Any]) -> str:
    """Formats a Schema 1.0 JSON event record into a clean, highlighted terminal output."""
    event_id = record.get("event_id", 0)
    event_name = record.get("event_name", "unknown")
    category = record.get("category", "general")
    frame = record.get("physics_frame", 0)
    elapsed = record.get("elapsed_ms", 0)
    scene = os.path.basename(record.get("scene", "") or "Main")
    
    cat_color = CATEGORY_COLORS.get(category, COLOR_CYAN)
    
    # Player info if present
    player = record.get("player")
    if player and isinstance(player, dict) and "position" in player:
        pos = player["position"]
        pos_str = f"P:({pos.get('x', 0):.0f}, {pos.get('y', 0):.0f})"
    else:
        pos_str = "P:none"

    # Action context (recent inputs)
    act_ctx = record.get("action_context", {}).get("recent_actions", [])
    last_act = act_ctx[-1]["action"] if act_ctx else "-"

    # Data summary
    data = record.get("data", {})
    data_str = json.dumps(data, ensure_ascii=False)
    if len(data_str) > 65:
        data_str = data_str[:62] + "..."

    anomaly_tag = f" {COLOR_BOLD}⚠️ ANOMALY!{COLOR_RESET}" if category == "anomaly" else ""

    line = (
        f"{COLOR_DIM}#{event_id:04d}{COLOR_RESET} "
        f"[{COLOR_CYAN}F:{frame:04d}{COLOR_RESET}|{elapsed:4d}ms] "
        f"{cat_color}[{category:<16}]{COLOR_RESET} "
        f"{COLOR_BOLD}{event_name:<26}{COLOR_RESET} "
        f"{pos_str:<15} "
        f"{COLOR_DIM}act:{last_act:<15}{COLOR_RESET} "
        f"{data_str}{anomaly_tag}"
    )
    return line


def main():
    # Enable ANSI terminal sequences on Windows
    os.system("")
    
    log_path = find_log_file()
    print("=" * 100)
    print(f" {COLOR_BOLD}🎮 AI GAME TESTER AGENT - STRUCTURED JSON LOGGER VIEWER (SCHEMA 1.0){COLOR_RESET}")
    print(f" Reading log: {COLOR_CYAN}{log_path}{COLOR_RESET}")
    print("=" * 100)
    print(f"  {COLOR_DIM}Legend: [input] [player_movement] [enemy] [collectible] [portal] [anomaly]{COLOR_RESET}")
    print("-" * 100)

    if not os.path.exists(log_path):
        print(f"{COLOR_YELLOW}Log file not created yet. Launch the game using run_game.bat to generate events!{COLOR_RESET}")

    # Read the existing last 15 lines as preview
    if os.path.exists(log_path):
        with open(log_path, "r", encoding="utf-8", errors="replace") as f:
            lines = [l.strip() for l in f if l.strip()]
            recent = lines[-15:] if len(lines) > 15 else lines
            if recent:
                print(f"{COLOR_DIM}--- Last {len(recent)} recorded events ---{COLOR_RESET}")
                for l in recent:
                    try:
                        obj = json.loads(l)
                        print(format_event_line(obj))
                    except Exception:
                        pass
                print(f"{COLOR_DIM}--- Live Event Stream (Press Ctrl+C to stop) ---{COLOR_RESET}")

    # Live follow/tail mode
    while not os.path.exists(log_path):
        time.sleep(0.5)

    with open(log_path, "r", encoding="utf-8", errors="replace") as f:
        f.seek(0, os.SEEK_END)
        while True:
            line = f.readline()
            if not line:
                time.sleep(0.03)
                continue
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
                print(format_event_line(rec))
            except json.JSONDecodeError:
                continue


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n{COLOR_DIM}Viewer closed.{COLOR_RESET}")
