"""
Live Log Reader & Agent Telemetry Monitor for Godot 2D Platformer (Game 2).

Provides instant real-time telemetry from the running game for AI agents, RL models, and LLM planners:
- Can poll 'latest_state.json' for atomic state snapshots (player, coins, enemies, goal, inputs, raycasts)
- Can stream 'game_events.jsonl' for sequence tracking, training data, and reward milestones
- Can be imported directly into Python agent scripts:
      from log_reader import GameStateReader
"""

import os
import sys
import time
import json
from typing import Optional, Dict, Any, Generator

STATE_FILE = "latest_state.json"
LOG_FILE = "game_events.jsonl"


class GameStateReader:
    """Helper class for AI agents to easily read the current game state and stream events."""

    def __init__(self, directory: Optional[str] = None):
        # Default to current directory, fallback to godot-4game if needed
        self.directory = directory or os.getcwd()
        self.state_path = os.path.join(self.directory, STATE_FILE)
        self.log_path = os.path.join(self.directory, LOG_FILE)

        # Fallback search if opened from subfolder
        if not os.path.exists(self.state_path):
            alt_path = os.path.join(self.directory, "godot-4game", STATE_FILE)
            if os.path.exists(alt_path):
                self.directory = os.path.join(self.directory, "godot-4game")
                self.state_path = alt_path
                self.log_path = os.path.join(self.directory, LOG_FILE)

    def get_latest_state(self) -> Optional[Dict[str, Any]]:
        """Returns the parsed dict of the current game state, or None if not yet written."""
        if not os.path.exists(self.state_path):
            return None
        try:
            with open(self.state_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return None

    def stream_events(self) -> Generator[Dict[str, Any], None, None]:
        """Generator that yields new event objects as they are appended to game_events.jsonl."""
        if not os.path.exists(self.log_path):
            return
        with open(self.log_path, "r", encoding="utf-8") as f:
            f.seek(0, os.SEEK_END)
            while True:
                line = f.readline()
                if not line:
                    time.sleep(0.04)
                    continue
                try:
                    yield json.loads(line)
                except json.JSONDecodeError:
                    continue

    def get_player(self) -> Optional[Dict[str, Any]]:
        """Convenience method returning player data if alive."""
        state = self.get_latest_state()
        if not state:
            return None
        p = state.get("player", {})
        return p if p.get("alive") else None

    def get_nearest_coin(self) -> Optional[Dict[str, Any]]:
        state = self.get_latest_state()
        if not state:
            return None
        return state.get("coins", {}).get("nearest_coin")

    def get_closest_enemy(self) -> Optional[Dict[str, Any]]:
        state = self.get_latest_state()
        if not state:
            return None
        return state.get("enemies", {}).get("closest_enemy")

    def get_goal_portal(self) -> Optional[Dict[str, Any]]:
        state = self.get_latest_state()
        if not state:
            return None
        g = state.get("goal", {})
        return g if g.get("found") else None


def live_cli_monitor():
    """Terminal HUD that continuously prints the live game telemetry."""
    reader = GameStateReader()
    print("=" * 75)
    print("   🎮 GODOT 2D PLATFORMER (GAME 2) - LIVE AGENT LOG MONITOR")
    print(f"   Monitoring: {reader.state_path}")
    print("   Waiting for game data... (Launch the game with run_game.bat)")
    print("=" * 75)

    last_frame = -1
    while True:
        state = reader.get_latest_state()
        if state is None:
            time.sleep(0.25)
            continue

        frame = state.get("frame", 0)
        if frame != last_frame:
            last_frame = frame
            p = state.get("player", {})
            c = state.get("coins", {})
            e = state.get("enemies", {})
            g = state.get("goal", {})
            stats = state.get("stats", {})
            game_state = state.get("game_state", "unknown")
            scene = state.get("scene", "Unknown")

            closest_enemy = e.get("closest_enemy")
            if closest_enemy:
                stomp_str = "STOMPABLE!" if closest_enemy.get("is_stompable") else ("THREAT!" if closest_enemy.get("is_threat") else "Safe")
                enemy_info = f"{closest_enemy['distance']}px ({stomp_str})"
            else:
                enemy_info = "None"

            nearest_coin = c.get("nearest_coin")
            coin_info = f"{nearest_coin['distance']}px" if nearest_coin else "None"

            portal_info = f"{g.get('distance_to_portal', 0)}px" if g.get("found") else "None"

            ground_dist = p.get("distance_to_ground", -1)
            ground_str = f"{ground_dist}px" if ground_dist >= 0 else "PIT!"

            # Single-line live updating terminal display
            status_line = (
                f"\r[{scene:<7} | Frame {frame:05d} | {game_state.upper():<7}] "
                f"P:({p.get('x', 0):4d},{p.get('y', 0):4d}) "
                f"Vel:({p.get('vel_x', 0):+4.0f},{p.get('vel_y', 0):+4.0f}) "
                f"Floor:{'YES' if p.get('on_floor') else 'NO '} "
                f"Grd:{ground_str:<5} | "
                f"Coins:{c.get('coins_collected', 0):2d} (Rem:{c.get('coins_remaining', 0):2d}) | "
                f"Score:{stats.get('score', 0):4d} Deaths:{stats.get('deaths', 0)} | "
                f"Nearest Coin:{coin_info:<7} | "
                f"Enemy:{enemy_info:<16} | "
                f"Exit:{portal_info}   "
            )
            sys.stdout.write(status_line)
            sys.stdout.flush()

        time.sleep(0.04)


if __name__ == "__main__":
    try:
        live_cli_monitor()
    except KeyboardInterrupt:
        print("\nMonitor stopped.")
