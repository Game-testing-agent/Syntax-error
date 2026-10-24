#!/usr/bin/env python3
"""
game_recorder.py — Manual Gameplay Recording & Demonstration Dataset Generator
for GDQuest 2D Platformer (Godot 4).

Allows manual play while capturing raw input events, player state transitions,
physics frame timing, and gameplay events into structured, reproducible demonstration datasets.
"""

import os
import sys
import time
import json
import uuid
from datetime import datetime
from typing import Optional, Dict, List, Any, Tuple


def normalize_level_name(level_input: Any) -> Tuple[str, str]:
    """
    Normalizes level input into (level_id, scene_path).
    Supports: "1", "2", 1, 2, "Level01", "Level02", "res://src/Levels/Level01.tscn".
    """
    s = str(level_input).strip()
    if s in ("1", "level1", "level_1", "Level01", "res://src/Levels/Level01.tscn"):
        return ("Level01", "res://src/Levels/Level01.tscn")
    elif s in ("2", "level2", "level_2", "Level02", "res://src/Levels/Level02.tscn"):
        return ("Level02", "res://src/Levels/Level02.tscn")
    elif s in ("3", "level3", "map3", "map_3", "Map3", "Map3_SkyCastle", "map3_sky_castle", "res://src/Levels/Map3_SkyCastle.tscn"):
        return ("Map3_SkyCastle", "res://src/Levels/Map3_SkyCastle.tscn")
    elif "Level02" in s:
        return ("Level02", s if s.startswith("res://") else f"res://src/Levels/{s}.tscn")
    elif "Map3" in s or "SkyCastle" in s:
        return ("Map3_SkyCastle", s if s.startswith("res://") else f"res://src/Levels/{s}.tscn")
    else:
        return ("Level01", s if s.startswith("res://") else "res://src/Levels/Level01.tscn")


class RecordingAttempt:
    """Encapsulates a single gameplay recording attempt."""

    def __init__(self, attempt_id: str, session_id: str, level: str,
                 start_frame: int, start_time_ms: int,
                 start_pos: Optional[Dict[str, float]] = None):
        self.attempt_id = attempt_id
        self.session_id = session_id
        self.level = level
        self.status = "in_progress"  # in_progress, completed, failed, inconclusive
        self.failure_reason: Optional[str] = None
        self.start_physics_frame = start_frame
        self.end_physics_frame: Optional[int] = None
        self.start_timestamp_unix_ms = start_time_ms
        self.end_timestamp_unix_ms: Optional[int] = None
        self.duration_seconds: float = 0.0

        self.start_player_pos = start_pos or {}
        self.end_player_pos: Dict[str, float] = {}

        self.final_score: int = 0
        self.death_count: int = 0

        self.events: List[Dict[str, Any]] = []
        self.input_summary: Dict[str, int] = {}
        self.gameplay_summary: Dict[str, Any] = {
            "coins_collected": 0,
            "enemies_stomped": 0,
            "jumps_performed": 0,
            "portal_entered": False
        }

    def add_event(self, event: Dict[str, Any]) -> None:
        """Adds a verified event to this attempt and updates summaries."""
        self.events.append(event)
        ev_name = event.get("event_name", event.get("event", ""))
        cat = event.get("category", "")

        # Track input counts
        if cat == "input" or "_pressed" in ev_name:
            action = ev_name.replace("_pressed", "").replace("_released", "")
            self.input_summary[action] = self.input_summary.get(action, 0) + 1

        # Track gameplay summaries
        if ev_name in ("coin_picked", "coin_collected"):
            self.gameplay_summary["coins_collected"] += 1
        elif ev_name in ("enemy_stomped", "enemy_killed"):
            self.gameplay_summary["enemies_stomped"] += 1
        elif ev_name == "jump_started":
            self.gameplay_summary["jumps_performed"] += 1
        elif ev_name in ("portal_entered", "portal_transition_started", "level_completed"):
            self.gameplay_summary["portal_entered"] = True

        # Track score/deaths if present
        data = event.get("data") or {}
        game_state = event.get("game_state") or {}
        if "score" in game_state:
            self.final_score = max(self.final_score, int(game_state["score"]))
        elif "final_score" in data:
            self.final_score = max(self.final_score, int(data["final_score"]))

        if "deaths" in game_state:
            self.death_count = max(self.death_count, int(game_state["deaths"]))

    def mark_failed(self, reason: str, end_frame: int, end_time_ms: int,
                    end_pos: Optional[Dict[str, float]] = None) -> None:
        """Marks the attempt as failed."""
        self.status = "failed"
        self.failure_reason = reason
        self.end_physics_frame = end_frame
        self.end_timestamp_unix_ms = end_time_ms
        self.duration_seconds = max(0.0, round((end_time_ms - self.start_timestamp_unix_ms) / 1000.0, 3))
        if end_pos:
            self.end_player_pos = end_pos

    def mark_completed(self, end_frame: int, end_time_ms: int,
                       end_pos: Optional[Dict[str, float]] = None,
                       final_score: Optional[int] = None) -> None:
        """Marks the attempt as successfully completed."""
        self.status = "completed"
        self.failure_reason = None
        self.end_physics_frame = end_frame
        self.end_timestamp_unix_ms = end_time_ms
        self.duration_seconds = max(0.0, round((end_time_ms - self.start_timestamp_unix_ms) / 1000.0, 3))
        if end_pos:
            self.end_player_pos = end_pos
        if final_score is not None:
            self.final_score = final_score
        self.gameplay_summary["portal_entered"] = True

    def mark_inconclusive(self, reason: str) -> None:
        """Marks attempt as inconclusive (e.g. timeout or manual abort)."""
        self.status = "inconclusive"
        self.failure_reason = reason
        now_ms = int(time.time() * 1000)
        self.end_timestamp_unix_ms = now_ms
        self.duration_seconds = max(0.0, round((now_ms - self.start_timestamp_unix_ms) / 1000.0, 3))

    def to_attempt_dict(self) -> Dict[str, Any]:
        """Returns JSON-serializable dictionary for attempt logs."""
        return {
            "schema_version": "1.0",
            "attempt_id": self.attempt_id,
            "session_id": self.session_id,
            "level": self.level,
            "status": self.status,
            "failure_reason": self.failure_reason,
            "start_physics_frame": self.start_physics_frame,
            "end_physics_frame": self.end_physics_frame,
            "start_timestamp_unix_ms": self.start_timestamp_unix_ms,
            "end_timestamp_unix_ms": self.end_timestamp_unix_ms,
            "duration_seconds": self.duration_seconds,
            "start_player_position": self.start_player_pos,
            "end_player_position": self.end_player_pos,
            "final_score": self.final_score,
            "death_count": self.death_count,
            "total_events": len(self.events),
            "input_summary": self.input_summary,
            "gameplay_summary": self.gameplay_summary
        }

    def to_demonstration_dict(self, demonstration_id: str, event_rel_path: str = "events.jsonl") -> Dict[str, Any]:
        """Returns metadata dictionary for successful demonstrations."""
        return {
            "schema_version": "1.0",
            "demonstration_id": demonstration_id,
            "level": self.level,
            "status": "completed",
            "source": "manual",
            "attempt_id": self.attempt_id,
            "session_id": self.session_id,
            "start_physics_frame": self.start_physics_frame,
            "end_physics_frame": self.end_physics_frame or self.start_physics_frame,
            "start_timestamp_unix_ms": self.start_timestamp_unix_ms,
            "end_timestamp_unix_ms": self.end_timestamp_unix_ms or self.start_timestamp_unix_ms,
            "duration_seconds": self.duration_seconds,
            "final_score": self.final_score,
            "death_count": self.death_count,
            "event_count": len(self.events),
            "input_event_count": sum(self.input_summary.values()),
            "input_summary": self.input_summary,
            "gameplay_summary": self.gameplay_summary,
            "initial_player_position": self.start_player_pos,
            "final_player_position": self.end_player_pos,
            "event_file": event_rel_path
        }


class DemonstrationDatasetManager:
    """Manages directory organization and persistence of demonstration records."""

    def __init__(self, base_dir: str = "recordings"):
        self.base_dir = os.path.abspath(base_dir)
        self.attempts_dir = os.path.join(self.base_dir, "attempts")
        self.failed_dir = os.path.join(self.base_dir, "failed")
        self.demonstrations_dir = os.path.join(self.base_dir, "demonstrations")
        self.raw_dir = os.path.join(self.base_dir, "raw")

        for d in (self.base_dir, self.attempts_dir, self.failed_dir,
                  self.demonstrations_dir, self.raw_dir):
            os.makedirs(d, exist_ok=True)

    def save_attempt(self, attempt: RecordingAttempt) -> str:
        """Saves attempt metadata JSON to recordings/attempts/."""
        path = os.path.join(self.attempts_dir, f"{attempt.attempt_id}.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(attempt.to_attempt_dict(), f, indent=2)
        return path

    def save_failed_attempt(self, attempt: RecordingAttempt) -> str:
        """Saves failed attempt metadata and events to recordings/failed/."""
        self.save_attempt(attempt)
        meta_path = os.path.join(self.failed_dir, f"{attempt.attempt_id}.json")
        data = attempt.to_attempt_dict()
        data["events"] = attempt.events
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        return meta_path

    def save_demonstration(self, attempt: RecordingAttempt) -> Tuple[str, str]:
        """
        Saves completed demonstration to:
        recordings/demonstrations/<level>_run_<id>/
          metadata.json
          events.jsonl
        """
        self.save_attempt(attempt)
        level_clean = attempt.level.lower()
        timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        demo_id = f"{level_clean}_demo_{timestamp_str}"
        demo_folder = os.path.join(self.demonstrations_dir, demo_id)
        os.makedirs(demo_folder, exist_ok=True)

        # Write events.jsonl
        events_path = os.path.join(demo_folder, "events.jsonl")
        with open(events_path, "w", encoding="utf-8") as f:
            for ev in attempt.events:
                f.write(json.dumps(ev) + "\n")

        # Write metadata.json
        meta_path = os.path.join(demo_folder, "metadata.json")
        meta = attempt.to_demonstration_dict(demo_id, event_rel_path="events.jsonl")
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(meta, f, indent=2)

        return (demo_folder, meta_path)


class ManualGameplayRecorder:
    """
    Coordinates manual gameplay recording with safe death detection,
    automatic retry handling, and demonstration generation.
    """

    def __init__(self, controller: Any, target_level: str = "Level01",
                 recordings_dir: str = "recordings",
                 auto_retry: bool = True, max_attempts: int = 5,
                 init_timeout: float = 6.0, tick_interval: float = 0.03,
                 verbose: bool = False):
        self.controller = controller
        self.target_level, self.scene_path = normalize_level_name(target_level)
        self.dataset_manager = DemonstrationDatasetManager(recordings_dir)
        self.auto_retry = auto_retry
        self.max_attempts = max_attempts
        self.init_timeout = init_timeout
        self.tick_interval = tick_interval
        self.verbose = verbose

        self.current_attempt: Optional[RecordingAttempt] = None
        self.completed_demonstration: Optional[Dict[str, Any]] = None
        self.last_file_offset: int = 0
        self.events_path = self.controller.events_path if hasattr(self.controller, "events_path") else ""

    def _init_file_offset(self) -> None:
        """Sets file offset to end of game_events.jsonl to only stream fresh events."""
        if self.events_path and os.path.exists(self.events_path):
            try:
                self.last_file_offset = os.path.getsize(self.events_path)
            except OSError:
                self.last_file_offset = 0
        else:
            self.last_file_offset = 0

    def _read_new_events(self) -> List[Dict[str, Any]]:
        """Reads newly appended events from game_events.jsonl since last offset."""
        if not self.events_path or not os.path.exists(self.events_path):
            return []

        new_events = []
        try:
            cur_size = os.path.getsize(self.events_path)
            if cur_size < self.last_file_offset:
                # File was truncated/recreated
                self.last_file_offset = 0

            with open(self.events_path, "r", encoding="utf-8", errors="replace") as f:
                f.seek(self.last_file_offset)
                for line in f:
                    line = line.strip()
                    if line:
                        try:
                            record = json.loads(line)
                            new_events.append(record)
                        except json.JSONDecodeError:
                            continue
                self.last_file_offset = f.tell()
        except OSError:
            pass

        return new_events

    def _wait_for_player_ready(self, timeout: float = 6.0) -> Optional[Dict[str, Any]]:
        """
        Safeguarded polling loop that waits for level and player initialization.
        Distinguishes scene_transitioning, waiting_for_player, alive, and dead.
        """
        start = time.time()
        while time.time() - start < timeout:
            st = self.controller.get_latest_state()
            if not st:
                time.sleep(0.1)
                continue

            scene = st.get("scene", "")
            game_state = st.get("game_state", "")

            # Scene transition or player spawning in progress: wait patiently, DO NOT retry
            if game_state in ("scene_transitioning", "waiting_for_player") or "Unknown" in scene:
                time.sleep(0.1)
                continue

            player = st.get("player") or {}
            is_alive = bool(player.get("alive", False))
            pos = player.get("position") or {}

            # Authoritative ready condition:
            # Correct level active, game playing, player alive with valid position
            if (self.target_level in scene or scene == self.target_level) and is_alive and pos:
                if game_state == "playing":
                    return st

            time.sleep(0.1)

        return None

    def _check_death(self, new_events: List[Dict[str, Any]], state: Optional[Dict[str, Any]]) -> bool:
        """Authoritatively checks if player has died using signals and events."""
        # 1. Authoritative event markers in stream
        death_event_names = {
            "player_died", "enemy_contact_death", "death_overlay_shown",
            "death_menu_opened", "death_counter_incremented"
        }
        for ev in new_events:
            ev_name = ev.get("event_name", ev.get("event", ""))
            if ev_name in death_event_names:
                return True

        # 2. State snapshot check
        if state:
            game_state = state.get("game_state", "")
            # Only consider player_died if not transitioning and player lifecycle says dead
            if game_state == "player_died":
                player = state.get("player") or {}
                if player.get("lifecycle_state") == "dead" or not player.get("alive", True):
                    return True

        return False

    def _check_completion(self, new_events: List[Dict[str, Any]], state: Optional[Dict[str, Any]]) -> bool:
        """Authoritatively checks if the target level was completed."""
        if self.target_level == "Level01":
            # Level 01 completes when portal to Level02 is entered
            for ev in new_events:
                ev_name = ev.get("event_name", ev.get("event", ""))
                data = ev.get("data") or {}
                if ev_name in ("portal_entered", "portal_transition_started"):
                    target = data.get("target_scene", "")
                    if "Level02" in target:
                        return True
                elif ev_name in ("scene_loaded", "scene_changed"):
                    scene = data.get("scene", ev.get("scene", ""))
                    if "Level02" in scene:
                        return True

            if state:
                cur_scene = state.get("scene", "")
                if "Level02" in cur_scene:
                    return True

        elif self.target_level == "Level02":
            # Level 02 completes when portal to EndScreen is entered or victory reached
            for ev in new_events:
                ev_name = ev.get("event_name", ev.get("event", ""))
                data = ev.get("data") or {}
                if ev_name in ("portal_entered", "portal_transition_started"):
                    target = data.get("target_scene", "")
                    if "EndScreen" in target:
                        return True
                elif ev_name in ("level_completed", "end_screen_loaded"):
                    return True
                elif ev_name in ("scene_loaded", "scene_changed"):
                    scene = data.get("scene", ev.get("scene", ""))
                    if "EndScreen" in scene:
                        return True

            if state:
                cur_scene = state.get("scene", "")
                game_state = state.get("game_state", "")
                if "EndScreen" in cur_scene or game_state == "victory":
                    return True

        return False

    def record(self) -> Optional[Dict[str, Any]]:
        """
        Executes manual recording session.
        Handles attempts, safe recovery on death, and clean demonstration saving.
        """
        print("\n" + "=" * 80)
        print("   >>> MANUAL GAMEPLAY RECORDING MODE")
        print(f"     Target Level      : {self.target_level} ({self.scene_path})")
        print(f"     Auto-Retry        : {self.auto_retry}")
        print(f"     Max Attempts      : {self.max_attempts}")
        print(f"     Recordings Dir    : {self.dataset_manager.base_dir}")
        print("   Instructions: Play normally using keyboard/controller controls.")
        print("   The recorder will monitor and preserve successful demonstration traces.")
        print("=" * 80 + "\n")

        self._init_file_offset()
        attempt_idx = 0

        while attempt_idx < self.max_attempts:
            attempt_idx += 1
            attempt_id = f"attempt_{attempt_idx:03d}"

            print(f"[STATUS] Preparing Attempt {attempt_id} for {self.target_level}...")
            print("         Waiting for level and player initialization...")

            ready_state = self._wait_for_player_ready(timeout=self.init_timeout)
            if not ready_state:
                print(f"[WARN] Initialization timed out for {self.target_level}.")
                # If player might be dead on initial screen, issue one retry if auto_retry
                if self.auto_retry and attempt_idx == 1:
                    print("[INFO] Issuing startup retry to reset player...")
                    self.controller.retry()
                    ready_state = self._wait_for_player_ready(timeout=self.init_timeout)

                if not ready_state:
                    print(f"[ERROR] Could not confirm player ready. Aborting recording session.")
                    break

            # Player is confirmed alive and grounded in the level
            player_info = ready_state.get("player", {})
            start_pos = player_info.get("position", {})
            start_frame = int(ready_state.get("physics_frame", 0))
            start_time_ms = int(time.time() * 1000)
            session_id = ready_state.get("session_id", f"session_{start_time_ms}")

            self.current_attempt = RecordingAttempt(
                attempt_id=attempt_id,
                session_id=session_id,
                level=self.target_level,
                start_frame=start_frame,
                start_time_ms=start_time_ms,
                start_pos=start_pos
            )

            # Consume any stale events from load phase
            self._read_new_events()

            print(f"\n[RECORDING STARTED] {attempt_id} is ACTIVE for {self.target_level}!")
            print(f"  Spawn Pos: ({start_pos.get('x')}, {start_pos.get('y')}) | Frame: {start_frame}")
            print("  >>> PLAY NOW! Advance to the level portal.\n")

            attempt_finished = False
            last_status_print = time.time()

            while not attempt_finished:
                time.sleep(self.tick_interval)

                new_events = self._read_new_events()
                cur_state = self.controller.get_latest_state()

                # Add events to current attempt
                for ev in new_events:
                    self.current_attempt.add_event(ev)

                # Periodic console heartbeat (every 3 seconds)
                if time.time() - last_status_print > 3.0:
                    last_status_print = time.time()
                    if cur_state and cur_state.get("player"):
                        p_pos = cur_state["player"].get("position", {})
                        p_x = round(p_pos.get("x", 0.0), 1)
                        p_y = round(p_pos.get("y", 0.0), 1)
                        inputs_cnt = sum(self.current_attempt.input_summary.values())
                        print(f"  [RECORDING] {attempt_id} | Pos: ({p_x}, {p_y}) | "
                              f"Inputs: {inputs_cnt} | Score: {self.current_attempt.final_score}")

                # 1. Check for Death
                if self._check_death(new_events, cur_state):
                    end_frame = int((cur_state or {}).get("physics_frame", start_frame))
                    end_time_ms = int(time.time() * 1000)
                    end_pos = ((cur_state or {}).get("player") or {}).get("position", {})

                    self.current_attempt.mark_failed("player_died", end_frame, end_time_ms, end_pos)
                    failed_path = self.dataset_manager.save_failed_attempt(self.current_attempt)

                    print(f"\n[DEATH DETECTED] Attempt {attempt_id} FAILED.")
                    print(f"  Failure reason preserved in: {failed_path}")
                    attempt_finished = True

                    if self.auto_retry and attempt_idx < self.max_attempts:
                        print(f"  [AUTO-RETRY] Issuing safe level reload (Attempt {attempt_idx + 1}/{self.max_attempts})...")
                        self.controller.retry()
                        # Short grace pause to allow Godot to queue scene reload
                        time.sleep(0.4)
                    else:
                        print(f"  [STOP] Max attempts ({self.max_attempts}) reached or auto-retry disabled.")
                    break

                # 2. Check for Level Completion
                if self._check_completion(new_events, cur_state):
                    end_frame = int((cur_state or {}).get("physics_frame", start_frame))
                    end_time_ms = int(time.time() * 1000)
                    end_pos = ((cur_state or {}).get("player") or {}).get("position", {})
                    final_score = int(((cur_state or {}).get("stats") or {}).get("score", self.current_attempt.final_score))

                    self.current_attempt.mark_completed(end_frame, end_time_ms, end_pos, final_score)
                    demo_folder, meta_path = self.dataset_manager.save_demonstration(self.current_attempt)

                    print("\n" + "*" * 80)
                    print("   [DEMONSTRATION RECORDED SUCCESSFULLY!]")
                    print(f"     Level               : {self.target_level}")
                    print(f"     Attempt ID          : {attempt_id}")
                    print(f"     Duration            : {self.current_attempt.duration_seconds}s")
                    print(f"     Frames              : {self.current_attempt.start_physics_frame} -> {self.current_attempt.end_physics_frame}")
                    print(f"     Final Score         : {self.current_attempt.final_score}")
                    print(f"     Total Events        : {len(self.current_attempt.events)}")
                    print(f"     Input Summary       : {self.current_attempt.input_summary}")
                    print(f"     Demonstration Dir   : {demo_folder}")
                    print("*" * 80 + "\n")

                    with open(meta_path, "r", encoding="utf-8") as f:
                        self.completed_demonstration = json.load(f)
                    return self.completed_demonstration

        print(f"\n[INFO] Recording session ended without a completed demonstration.")
        return None


def main():
    import argparse
    from explorer import GameController, launch_godot_game

    parser = argparse.ArgumentParser(description="Manual Gameplay Recorder for GDQuest 2D Platformer")
    parser.add_argument("--level", default="1", help="Target level: 1, 2, Level01, Level02")
    parser.add_argument("--launch", action="store_true", help="Launch Godot game if not already running")
    parser.add_argument("--port", type=int, default=4242, help="UDP control port (default: 4242)")
    parser.add_argument("--recordings-dir", default="recordings", help="Output directory (default: recordings)")
    parser.add_argument("--max-attempts", type=int, default=5, help="Maximum recording attempts before stopping")
    parser.add_argument("--no-auto-retry", action="store_true", help="Disable automatic retry on death")
    parser.add_argument("--verbose", action="store_true", help="Verbose logging")

    args = parser.parse_args()

    godot_proc = None
    level_id, scene_path = normalize_level_name(args.level)
    if args.launch:
        godot_proc = launch_godot_game(scene_path)

    controller = GameController(port=args.port)
    controller.connect(retries=3, retry_interval=0.4)

    recorder = ManualGameplayRecorder(
        controller=controller,
        target_level=level_id,
        recordings_dir=args.recordings_dir,
        auto_retry=not args.no_auto_retry,
        max_attempts=args.max_attempts,
        verbose=args.verbose
    )

    try:
        recorder.record()
    finally:
        controller.close()
        if godot_proc and godot_proc.poll() is None:
            try:
                godot_proc.terminate()
            except Exception:
                pass


if __name__ == "__main__":
    main()
