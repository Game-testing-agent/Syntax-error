#!/usr/bin/env python3
"""
explorer.py — AI Game Tester Explorer for GDQuest 2D Platformer (Godot 4)

Provides 3 Exploration Modes:
1. Scripted Path Mode: Sequential execution of predefined JSON paths with checkpoints.
2. Random Mode: Randomized actions with configurable seed, duration, and death recovery.
3. Coverage-Guided Mode: Novelty and telemetry-guided exploration tracking visited states,
   coins, events, and spatial coverage.

Communication:
- Control: Non-blocking UDP packets to 127.0.0.1:4242 (with agent_command.json mailbox fallback).
- Telemetry: Real-time atomic snapshots from latest_state.json and streaming from game_events.jsonl.
"""

import os
import sys
import time
import json
import socket
import random
import atexit
import argparse
import subprocess
from datetime import datetime
from typing import Optional, Dict, List, Any, Tuple, Union

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

DEFAULT_UDP_PORT = 4242
DEFAULT_FPS = 60
STATE_FILE = "latest_state.json"
EVENTS_FILE = "game_events.jsonl"
COMMAND_FILE = "agent_command.json"
COVERAGE_FILE = "coverage_report.json"

VALID_ACTIONS = {
    "move_left",
    "move_right",
    "jump",
    "pause",
    "retry",
    "main_menu",
    "start_game",
    "play",
    "release_all",
    "wait"
}


# ==============================================================================
# TELEMETRY & GAME CONTROLLER
# ==============================================================================

class GameController:
    """Handles communication with Godot game via UDP port 4242 & mailbox fallback."""

    def __init__(self, host: str = "127.0.0.1", port: int = DEFAULT_UDP_PORT,
                 workspace_dir: Optional[str] = None, fps: int = DEFAULT_FPS):
        self.host = host
        self.port = port
        self.fps = fps
        self.workspace_dir = workspace_dir or os.getcwd()

        # Locate files in root or godot-4game subfolder
        self.state_path = self._find_path(STATE_FILE)
        self.events_path = self._find_path(EVENTS_FILE)
        self.command_path = os.path.join(self.workspace_dir, COMMAND_FILE)

        # Setup UDP socket
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.settimeout(0.15)
        self.active_actions: List[str] = []
        self._connected = False

        # Register cleanup on exit
        atexit.register(self.release_all)

    def _find_path(self, filename: str) -> str:
        p1 = os.path.join(self.workspace_dir, filename)
        if os.path.exists(p1):
            return p1
        p2 = os.path.join(self.workspace_dir, "godot-4game", filename)
        if os.path.exists(p2):
            return p2
        return p1

    def send_command(self, cmd: Dict[str, Any]) -> bool:
        """Sends command dictionary to Godot via UDP, falls back to mailbox file."""
        payload = json.dumps(cmd).encode("utf-8")
        sent = False
        try:
            self.sock.sendto(payload, (self.host, self.port))
            sent = True
        except OSError:
            pass

        # Also write mailbox file if UDP might fail or for redundancy
        try:
            tmp_path = self.command_path + ".tmp"
            with open(tmp_path, "w", encoding="utf-8") as f:
                json.dump(cmd, f)
            if os.path.exists(self.command_path):
                os.remove(self.command_path)
            os.replace(tmp_path, self.command_path)
        except OSError:
            pass

        return sent

    def ping(self, timeout: float = 0.5) -> Optional[Dict[str, Any]]:
        """Sends ping to Godot and waits for response."""
        try:
            self.sock.sendto(json.dumps({"command": "ping"}).encode("utf-8"), (self.host, self.port))
            start = time.time()
            while time.time() - start < timeout:
                try:
                    data, _ = self.sock.recvfrom(4096)
                    resp = json.loads(data.decode("utf-8"))
                    if resp.get("status") == "ok":
                        self._connected = True
                        return resp
                except socket.timeout:
                    break
                except (json.JSONDecodeError, OSError):
                    continue
        except OSError:
            pass
        return None

    def connect(self, retries: int = 5, retry_interval: float = 0.5) -> bool:
        """Attempts to establish connection with running Godot instance."""
        print(f"Connecting to Godot on {self.host}:{self.port}...")
        for attempt in range(1, retries + 1):
            res = self.ping(timeout=0.6)
            if res:
                print(f"[OK] Connected to Godot! Scene: {res.get('scene', 'Unknown')}, "
                      f"Frame: {res.get('frame', 0)}, Player Alive: {res.get('player_alive', False)}")
                self._connected = True
                return True
            time.sleep(retry_interval)
        print(f"[NOTE] UDP handshake did not respond directly. Using mailbox/asynchronous mode.")
        return False

    def get_latest_state(self) -> Optional[Dict[str, Any]]:
        """Reads atomic state snapshot from latest_state.json with retry logic."""
        if not os.path.exists(self.state_path):
            self.state_path = self._find_path(STATE_FILE)
            if not os.path.exists(self.state_path):
                return None

        # Retry up to 3 times to prevent Windows file locking collisions
        for _ in range(3):
            try:
                with open(self.state_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except (json.JSONDecodeError, OSError, PermissionError):
                time.sleep(0.005)
        return None

    def get_latest_event_id(self) -> int:
        """Finds the maximum event_id recorded in game_events.jsonl so far."""
        if not os.path.exists(self.events_path):
            return 0
        try:
            with open(self.events_path, "r", encoding="utf-8") as f:
                f.seek(0, os.SEEK_END)
                size = f.tell()
                f.seek(max(0, size - 2048), os.SEEK_SET)
                lines = f.readlines()
                for line in reversed(lines):
                    line = line.strip()
                    if line:
                        try:
                            data = json.loads(line)
                            if "event_id" in data:
                                return int(data["event_id"])
                        except json.JSONDecodeError:
                            continue
        except OSError:
            pass
        return 0

    def get_events_since(self, since_id: int) -> List[Dict[str, Any]]:
        """Reads all events logged after since_id."""
        if not os.path.exists(self.events_path):
            return []
        events = []
        try:
            with open(self.events_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        record = json.loads(line)
                        if record.get("event_id", 0) > since_id:
                            events.append(record)
                    except json.JSONDecodeError:
                        continue
        except OSError:
            pass
        return events

    def press_actions(self, actions: List[str]) -> None:
        """Sets active pressed actions in Godot."""
        cleaned = [a for a in actions if a in VALID_ACTIONS and a not in ("wait", "release_all")]
        self.active_actions = cleaned
        self.send_command({"actions": cleaned})

    def release_all(self) -> None:
        """Releases all active inputs in Godot."""
        self.active_actions = []
        self.send_command({"command": "release_all"})

    def retry(self) -> None:
        """Triggers level restart/retry."""
        self.send_command({"command": "retry"})

    def pause(self, val: Optional[bool] = None) -> None:
        """Toggles or sets pause state."""
        cmd: Dict[str, Any] = {"command": "pause"}
        if val is not None:
            cmd["value"] = val
        self.send_command(cmd)

    def start_game(self) -> None:
        """Instructs Godot to switch to Level01 from main screen."""
        self.send_command({"command": "start_game"})

    def wait_seconds(self, duration: float) -> None:
        """Precise waiting helper."""
        time.sleep(max(0.0, duration))

    def close(self) -> None:
        """Cleanup socket and releases inputs."""
        self.release_all()
        try:
            self.sock.close()
        except OSError:
            pass


# ==============================================================================
# SCRIPTED PATH PARSER & VALIDATOR
# ==============================================================================

class PathValidationError(Exception):
    pass


class ScriptedStep:
    """Represents a validated execution step in a scripted path."""

    def __init__(self, step_idx: int, actions: List[str], frames: int, duration_sec: float,
                 description: str = "", checkpoint: Optional[Dict[str, Any]] = None,
                 stop_if_died: bool = False, retry_if_died: bool = False):
        self.step_idx = step_idx
        self.actions = actions
        self.frames = frames
        self.duration_sec = duration_sec
        self.description = description
        self.checkpoint = checkpoint
        self.stop_if_died = stop_if_died
        self.retry_if_died = retry_if_died

    def to_dict(self) -> Dict[str, Any]:
        return {
            "step": self.step_idx,
            "actions": self.actions,
            "frames": self.frames,
            "duration": self.duration_sec,
            "description": self.description,
            "checkpoint": self.checkpoint,
            "stop_if_died": self.stop_if_died,
            "retry_if_died": self.retry_if_died
        }


class PathParser:
    """Parses and validates scripted path JSON files, expanding subsequences."""

    @staticmethod
    def parse_file(path_file: str, fps: int = DEFAULT_FPS) -> Tuple[str, str, List[ScriptedStep]]:
        if not os.path.exists(path_file):
            raise FileNotFoundError(f"Path file not found: {path_file}")

        try:
            with open(path_file, "r", encoding="utf-8") as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            raise PathValidationError(f"Invalid JSON in {path_file}: {e}")

        if not isinstance(data, dict):
            raise PathValidationError(f"Path root must be a JSON object, got {type(data).__name__}")

        name = data.get("name", os.path.basename(path_file))
        description = data.get("description", "")
        subsequences = data.get("subsequences", {})

        raw_steps = data.get("steps", [])
        if not isinstance(raw_steps, list):
            raise PathValidationError(f"'steps' must be a JSON array, got {type(raw_steps).__name__}")

        if len(raw_steps) == 0:
            raise PathValidationError(f"'steps' array cannot be empty in {path_file}")

        # Expand subsequences
        expanded_raw_steps = PathParser._expand_subsequences(raw_steps, subsequences)

        parsed_steps: List[ScriptedStep] = []
        for idx, step_data in enumerate(expanded_raw_steps):
            parsed_steps.append(PathParser._parse_step(idx + 1, step_data, fps))

        return name, description, parsed_steps

    @staticmethod
    def _expand_subsequences(steps: List[Any], subsequences: Dict[str, Any], depth: int = 0) -> List[Dict[str, Any]]:
        if depth > 10:
            raise PathValidationError("Exceeded maximum recursion depth (10) for subsequences.")

        expanded = []
        for step in steps:
            if not isinstance(step, dict):
                raise PathValidationError(f"Expected step dictionary, got {type(step).__name__}: {step}")

            if "subsequence" in step:
                sub_name = step["subsequence"]
                if sub_name not in subsequences:
                    raise PathValidationError(f"Referenced undefined subsequence: '{sub_name}'")
                sub_steps = subsequences[sub_name]
                if not isinstance(sub_steps, list):
                    raise PathValidationError(f"Subsequence '{sub_name}' must be an array of steps.")
                expanded.extend(PathParser._expand_subsequences(sub_steps, subsequences, depth + 1))
            else:
                expanded.append(step)
        return expanded

    @staticmethod
    def _parse_step(step_idx: int, step: Dict[str, Any], fps: int) -> ScriptedStep:
        # Determine actions (supports "action", "actions", and "+" syntax)
        actions: List[str] = []
        if "actions" in step:
            raw_acts = step["actions"]
            if not isinstance(raw_acts, list):
                raise PathValidationError(f"Step {step_idx}: 'actions' must be an array, got {type(raw_acts).__name__}")
            for a in raw_acts:
                actions.extend(PathParser._normalize_action(a, step_idx))
        elif "action" in step:
            raw_act = step["action"]
            if isinstance(raw_act, list):
                for a in raw_act:
                    actions.extend(PathParser._normalize_action(a, step_idx))
            else:
                actions.extend(PathParser._normalize_action(raw_act, step_idx))
        else:
            raise PathValidationError(f"Step {step_idx} must specify 'action' or 'actions'")

        # Determine duration & frames
        frames = None
        duration_sec = None

        if "frames" in step:
            try:
                frames = int(step["frames"])
                if frames <= 0:
                    raise ValueError()
                duration_sec = round(frames / float(fps), 4)
            except (ValueError, TypeError):
                raise PathValidationError(f"Step {step_idx}: 'frames' must be a positive integer.")
        elif "duration" in step:
            try:
                duration_sec = float(step["duration"])
                if duration_sec <= 0:
                    raise ValueError()
                frames = max(1, int(round(duration_sec * fps)))
            except (ValueError, TypeError):
                raise PathValidationError(f"Step {step_idx}: 'duration' must be a positive number of seconds.")
        else:
            # Default to 1 frame for instantaneous triggers like jump or retry, 30 frames for movement
            if any(a in ("jump", "retry", "pause") for a in actions):
                frames = 1
                duration_sec = round(1.0 / fps, 4)
            else:
                frames = 30
                duration_sec = 0.5

        # Checkpoint & flags
        desc = step.get("description", step.get("comment", ""))
        checkpoint = step.get("checkpoint", None)
        if checkpoint and not isinstance(checkpoint, dict):
            raise PathValidationError(f"Step {step_idx}: 'checkpoint' must be an object.")

        stop_if_died = bool(step.get("stop_if_died", False))
        retry_if_died = bool(step.get("retry_if_died", False))

        return ScriptedStep(step_idx, actions, frames, duration_sec, desc, checkpoint, stop_if_died, retry_if_died)

    @staticmethod
    def _normalize_action(action_str: Any, step_idx: int) -> List[str]:
        if not isinstance(action_str, str):
            raise PathValidationError(f"Step {step_idx}: Action must be a string, got {type(action_str).__name__}")
        action_str = action_str.strip()
        # Handle "move_right+jump" syntax
        parts = [p.strip() for p in action_str.split("+")]
        for p in parts:
            if p not in VALID_ACTIONS:
                raise PathValidationError(
                    f"Step {step_idx}: Unknown action '{p}'. Valid actions are: {sorted(list(VALID_ACTIONS))}"
                )
        return parts


# ==============================================================================
# CHECKPOINT EVALUATION
# ==============================================================================

class CheckpointEvaluator:
    """Evaluates checkpoint conditions against live telemetry snapshots."""

    @staticmethod
    def evaluate(checkpoint: Dict[str, Any], state: Optional[Dict[str, Any]],
                 state_before: Optional[Dict[str, Any]]) -> Tuple[bool, str]:
        if not checkpoint:
            return True, "No checkpoint"
        if not state:
            return False, "No state data available"

        cp_type = checkpoint.get("type", "")
        player = state.get("player") or {}
        stats = state.get("stats") or {}
        coins = state.get("coins") or {}

        # 1. on_floor / grounded
        if cp_type in ("on_floor", "grounded", "is_grounded"):
            expected = checkpoint.get("expected", True)
            actual = bool(player.get("on_floor", False))
            if actual == expected:
                return True, f"Player on_floor is {actual} (expected {expected})"
            return False, f"Player on_floor is {actual} (expected {expected})"

        # 2. is_airborne
        if cp_type == "is_airborne":
            on_floor = bool(player.get("on_floor", False))
            if not on_floor:
                return True, "Player is airborne (not on floor)"
            return False, "Player is still on the floor"

        # 3. score_greater_than
        if cp_type == "score_greater_than":
            val = checkpoint.get("value", 0)
            actual = stats.get("score", 0)
            if actual > val:
                return True, f"Score {actual} > {val}"
            return False, f"Score {actual} <= {val}"

        # 4. score_increased
        if cp_type == "score_increased":
            score_before = (state_before.get("stats") or {}).get("score", 0) if state_before else 0
            score_after = stats.get("score", 0)
            if score_after > score_before:
                return True, f"Score increased from {score_before} to {score_after}"
            return False, f"Score has not increased ({score_after} <= {score_before})"

        # 5. coin_collected
        if cp_type == "coin_collected":
            c_before = (state_before.get("coins") or {}).get("coins_collected", 0) if state_before else 0
            c_after = coins.get("coins_collected", 0)
            if c_after > c_before:
                return True, f"Coins collected increased from {c_before} to {c_after}"
            return False, f"Coins collected has not increased ({c_after} <= {c_before})"

        # 6. player_alive
        if cp_type == "player_alive":
            expected = checkpoint.get("expected", True)
            actual = bool(player.get("alive", False))
            if actual == expected:
                return True, f"Player alive is {actual} (expected {expected})"
            return False, f"Player alive is {actual} (expected {expected})"

        # 7. position_x_greater
        if cp_type == "position_x_greater":
            val = checkpoint.get("value", 0.0)
            actual = player.get("position", {}).get("x", 0.0)
            if actual > val:
                return True, f"Player X {actual} > {val}"
            return False, f"Player X {actual} <= {val}"

        # 8. position_x_less
        if cp_type == "position_x_less":
            val = checkpoint.get("value", 0.0)
            actual = player.get("position", {}).get("x", 0.0)
            if actual < val:
                return True, f"Player X {actual} < {val}"
            return False, f"Player X {actual} >= {val}"

        # 9. scene
        if cp_type == "scene":
            val = checkpoint.get("value", "")
            actual = state.get("scene", "")
            if val in actual:
                return True, f"Scene '{actual}' matches '{val}'"
            return False, f"Scene '{actual}' does not match '{val}'"

        return False, f"Unknown checkpoint type '{cp_type}'"


# ==============================================================================
# ACTION HISTORY RECORDER
# ==============================================================================

class ActionHistoryRecorder:
    """Logs and persists full step-by-step history of exploration runs for replay."""

    def __init__(self, mode: str, metadata: Dict[str, Any]):
        self.mode = mode
        self.metadata = metadata
        self.start_time = datetime.now().isoformat()
        self.start_epoch = time.time()
        self.steps: List[Dict[str, Any]] = []

    def record_step(self, step_idx: int, actions: List[str], duration_sec: float,
                    state_before: Optional[Dict[str, Any]], state_after: Optional[Dict[str, Any]],
                    status: str, events: List[Dict[str, Any]], checkpoint_result: Optional[str] = None) -> None:
        p_before = (state_before.get("player") or {}) if state_before else {}
        p_after = (state_after.get("player") or {}) if state_after else {}
        stats_after = (state_after.get("stats") or {}) if state_after else {}

        event_summaries = [
            {"id": ev.get("event_id"), "name": ev.get("event_name"), "category": ev.get("category")}
            for ev in events
        ]

        step_record = {
            "step_index": step_idx,
            "actions": actions,
            "duration_seconds": round(duration_sec, 4),
            "timestamp": time.time(),
            "status": status,
            "checkpoint_result": checkpoint_result,
            "state_before": {
                "x": p_before.get("position", {}).get("x", None),
                "y": p_before.get("position", {}).get("y", None),
                "on_floor": p_before.get("on_floor", None),
                "alive": p_before.get("alive", None)
            },
            "state_after": {
                "x": p_after.get("position", {}).get("x", None),
                "y": p_after.get("position", {}).get("y", None),
                "on_floor": p_after.get("on_floor", None),
                "alive": p_after.get("alive", None),
                "score": stats_after.get("score", 0),
                "deaths": stats_after.get("deaths", 0),
                "scene": state_after.get("scene", "") if state_after else ""
            },
            "events_count": len(events),
            "events": event_summaries
        }
        self.steps.append(step_record)

    def finalize(self, output_path: Optional[str] = None) -> str:
        duration_total = round(time.time() - self.start_epoch, 2)
        success_count = sum(1 for s in self.steps if s["status"] == "success")
        fail_count = sum(1 for s in self.steps if s["status"] in ("failed", "timeout", "interrupted"))

        summary = {
            "total_steps": len(self.steps),
            "successful_steps": success_count,
            "failed_steps": fail_count,
            "duration_total_seconds": duration_total,
            "final_score": self.steps[-1]["state_after"]["score"] if self.steps else 0,
            "final_deaths": self.steps[-1]["state_after"]["deaths"] if self.steps else 0
        }

        full_doc = {
            "run_id": f"explorer_{self.mode}_{int(self.start_epoch)}",
            "mode": self.mode,
            "start_time": self.start_time,
            "end_time": datetime.now().isoformat(),
            "metadata": self.metadata,
            "summary": summary,
            "steps": self.steps
        }

        if not output_path:
            timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = f"explorer_history_{self.mode}_{timestamp_str}.json"

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(full_doc, f, indent=2)

        return output_path


# ==============================================================================
# MODE A: SCRIPTED PATH EXECUTOR
# ==============================================================================

class ScriptedExecutor:
    """Executes a parsed scripted path sequentially and validates checkpoints."""

    def __init__(self, controller: GameController, verbose: bool = True):
        self.controller = controller
        self.verbose = verbose

    def run(self, path_file: str, history_recorder: ActionHistoryRecorder) -> bool:
        name, description, steps = PathParser.parse_file(path_file, fps=self.controller.fps)

        print("\n" + "=" * 75)
        print(f"   >>> EXECUTING SCRIPTED PATH: {name}")
        if description:
            print(f"     Description: {description}")
        print(f"     Total Steps: {len(steps)}")
        print("=" * 75)

        # Initial handshake & unpause/reset if needed
        initial_state = self.controller.get_latest_state()
        if initial_state and not (initial_state.get("player") or {}).get("alive", False):
            print("[INFO] Player not alive at start, issuing retry...")
            self.controller.retry()
            time.sleep(1.0)

        all_passed = True

        for step in steps:
            step_idx = step.step_idx
            actions = step.actions
            dur_sec = step.duration_sec
            desc = f" ({step.description})" if step.description else ""

            print(f"\n[Step {step_idx}/{len(steps)}] Actions: {actions} for {dur_sec}s ({step.frames}f){desc}")

            state_before = self.controller.get_latest_state()
            event_id_before = self.controller.get_latest_event_id()

            # Execute action inputs
            if "retry" in actions:
                self.controller.retry()
                self.controller.wait_seconds(dur_sec)
            elif "pause" in actions:
                self.controller.pause()
                self.controller.wait_seconds(dur_sec)
            elif "main_menu" in actions:
                self.controller.send_command({"command": "main_menu"})
                self.controller.wait_seconds(dur_sec)
            elif "start_game" in actions or "play" in actions:
                self.controller.start_game()
                self.controller.wait_seconds(dur_sec)
            elif "release_all" in actions or "wait" in actions:
                self.controller.release_all()
                self.controller.wait_seconds(dur_sec)
            else:
                self.controller.press_actions(actions)
                self.controller.wait_seconds(dur_sec)

            # Checkpoint evaluation & waiting
            status = "success"
            cp_result_msg = None

            if step.checkpoint:
                timeout = float(step.checkpoint.get("timeout", 2.0))
                cp_start = time.time()
                passed = False
                reason = ""
                while time.time() - cp_start < timeout:
                    current_st = self.controller.get_latest_state()
                    passed, reason = CheckpointEvaluator.evaluate(step.checkpoint, current_st, state_before)
                    if passed:
                        break
                    time.sleep(0.04)

                if passed:
                    cp_result_msg = f"PASSED: {reason}"
                    print(f"  [PASS] Checkpoint: {cp_result_msg}")
                else:
                    cp_result_msg = f"TIMED OUT ({timeout}s): {reason}"
                    status = "timeout"
                    all_passed = False
                    print(f"  [FAIL] Checkpoint: {cp_result_msg}")

            # Check death conditions
            state_after = self.controller.get_latest_state()
            player_alive = (state_after.get("player") or {}).get("alive", True) if state_after else True

            if not player_alive:
                if step.stop_if_died:
                    status = "interrupted_death"
                    all_passed = False
                    print("  [!] Player died and 'stop_if_died' is active. Aborting path.")
                    self.controller.release_all()
                    events = self.controller.get_events_since(event_id_before)
                    history_recorder.record_step(step_idx, actions, dur_sec, state_before, state_after,
                                                 status, events, cp_result_msg)
                    break
                elif step.retry_if_died:
                    print("  [!] Player died. 'retry_if_died' is active, issuing retry...")
                    self.controller.retry()
                    time.sleep(1.0)
                    state_after = self.controller.get_latest_state()

            # Release inputs unless next step specifies continuation
            self.controller.release_all()

            events = self.controller.get_events_since(event_id_before)
            history_recorder.record_step(step_idx, actions, dur_sec, state_before, state_after,
                                         status, events, cp_result_msg)

            # Log displacement & state info
            p0 = (state_before.get("player") or {}).get("position", {}) if state_before else {}
            p1 = (state_after.get("player") or {}).get("position", {}) if state_after else {}
            if p0.get("x") is not None and p1.get("x") is not None:
                dx = round(p1["x"] - p0["x"], 1)
                dy = round(p1["y"] - p0["y"], 1)
                print(f"  -> Pos: ({p1['x']}, {p1['y']}) [dx={dx}, dy={dy}] | Grounded: {state_after.get('player', {}).get('on_floor')} | Events: +{len(events)}")

        print("\n" + "=" * 75)
        print(f"   [DONE] SCRIPTED PATH FINISHED: {'ALL PASSED' if all_passed else 'SOME STEPS FAILED/TIMED OUT'}")
        print("=" * 75)
        return all_passed


# ==============================================================================
# MODE B: RANDOM EXPLORER
# ==============================================================================

class RandomExplorer:
    """Explores the game by randomly sampling valid actions, durations, and seeds."""

    ACTION_CHOICES = [
        ["move_right"],
        ["move_left"],
        ["jump"],
        ["move_right", "jump"],
        ["move_left", "jump"],
        ["wait"]
    ]

    def __init__(self, controller: GameController, seed: int = 42, max_actions: int = 100):
        self.controller = controller
        self.seed = seed
        self.max_actions = max_actions
        self.rng = random.Random(seed)

    def run(self, history_recorder: ActionHistoryRecorder) -> None:
        print("\n" + "=" * 75)
        print(f"   [*] RUNNING RANDOM EXPLORATION")
        print(f"     Random Seed : {self.seed}")
        print(f"     Max Actions : {self.max_actions}")
        print("=" * 75)

        for action_idx in range(1, self.max_actions + 1):
            state_before = self.controller.get_latest_state()
            player = (state_before.get("player") or {}) if state_before else {}

            # Handle death & retry
            if not player.get("alive", True):
                print(f"  [Death Detected] Triggering retry and respawning...")
                self.controller.retry()
                self.controller.wait_seconds(1.0)
                state_before = self.controller.get_latest_state()

            # Sample random action & duration (10 to 45 frames ~ 0.16s to 0.75s)
            chosen_actions = self.rng.choice(self.ACTION_CHOICES)
            frames = self.rng.randint(10, 45)
            dur_sec = round(frames / float(self.controller.fps), 3)

            event_id_before = self.controller.get_latest_event_id()

            print(f"[{action_idx:03d}/{self.max_actions}] Action: {chosen_actions} for {dur_sec}s ({frames}f)")

            if "wait" in chosen_actions:
                self.controller.release_all()
            else:
                self.controller.press_actions(chosen_actions)

            self.controller.wait_seconds(dur_sec)
            self.controller.release_all()

            state_after = self.controller.get_latest_state()
            events = self.controller.get_events_since(event_id_before)

            history_recorder.record_step(action_idx, chosen_actions, dur_sec, state_before, state_after,
                                         "success", events)

            # Telemetry readout
            p_pos = (state_after.get("player") or {}).get("position", {}) if state_after else {}
            score = (state_after.get("stats") or {}).get("score", 0) if state_after else 0
            deaths = (state_after.get("stats") or {}).get("deaths", 0) if state_after else 0
            print(f"  -> Pos: ({p_pos.get('x')}, {p_pos.get('y')}) | Score: {score} | Deaths: {deaths} | Events: +{len(events)}")


# ==============================================================================
# MODE C: COVERAGE-GUIDED EXPLORER
# ==============================================================================

class CoverageGuidedExplorer:
    """Uses state discretization, novelty scoring, and telemetry to explore new areas."""

    CANDIDATE_ACTIONS = [
        ["move_right"],
        ["move_right", "jump"],
        ["move_left"],
        ["move_left", "jump"],
        ["jump"],
        ["wait"]
    ]

    def __init__(self, controller: GameController, max_actions: int = 150, grid_size: int = 120):
        self.controller = controller
        self.max_actions = max_actions
        self.grid_size = grid_size
        self.state_visits: Dict[Tuple, int] = {}
        self.action_history_counts: Dict[str, int] = {str(a): 0 for a in self.CANDIDATE_ACTIONS}
        self.stuck_counter = 0
        self.last_pos_x = None

    def discretize_state(self, state: Optional[Dict[str, Any]]) -> Tuple:
        if not state:
            return ("unknown", 0, 0, False)
        scene = state.get("scene", "Unknown")
        player = state.get("player") or {}
        pos = player.get("position", {})
        gx = int((pos.get("x", 0) or 0) // self.grid_size)
        gy = int((pos.get("y", 0) or 0) // self.grid_size)
        on_floor = bool(player.get("on_floor", False))
        return (scene, gx, gy, on_floor)

    def select_action(self, state: Optional[Dict[str, Any]]) -> Tuple[List[str], int]:
        """Calculates explainable novelty & telemetry guidance scores to pick the best action."""
        if not state:
            return ["move_right"], 30

        player = state.get("player") or {}
        coins = state.get("coins") or {}
        goal = state.get("goal") or {}
        current_cell = self.discretize_state(state)
        cur_x = player.get("position", {}).get("x", 0)

        # Stuck detection
        if self.last_pos_x is not None and abs(cur_x - self.last_pos_x) < 5.0:
            self.stuck_counter += 1
        else:
            self.stuck_counter = 0
        self.last_pos_x = cur_x

        # If stuck against an obstacle, strongly favor jump-right
        if self.stuck_counter >= 2:
            return ["move_right", "jump"], 35

        # Novelty scores for candidates
        best_action = ["move_right"]
        best_score = -1e9

        for candidate in self.CANDIDATE_ACTIONS:
            score = 0.0

            # 1. Forward progression bonus (Platformers progress to the right)
            if "move_right" in candidate:
                score += 15.0
            if "move_left" in candidate:
                score += 4.0

            # 2. Nearest coin attraction
            nearest_coin = coins.get("nearest_coin")
            if nearest_coin:
                rel_x = nearest_coin.get("relative_x", 0)
                rel_y = nearest_coin.get("relative_y", 0)
                if rel_x > 0 and "move_right" in candidate:
                    score += 20.0
                elif rel_x < 0 and "move_left" in candidate:
                    score += 18.0
                if rel_y < -40 and "jump" in candidate:
                    score += 15.0

            # 3. Goal Portal guidance
            if goal.get("found", False) and goal.get("relative_x", 0) > 0:
                if "move_right" in candidate:
                    score += 10.0

            # 4. Jump encouragement when grounded
            if player.get("on_floor", False) and "jump" in candidate:
                score += 8.0

            # 5. Action diversity / novelty bonus (prefer less-used actions)
            act_str = str(candidate)
            usage = self.action_history_counts.get(act_str, 0)
            score -= (usage * 0.4)

            # 6. Epsilon random exploration jitter (15%)
            if random.random() < 0.15:
                score += random.uniform(-10.0, 10.0)

            if score > best_score:
                best_score = score
                best_action = candidate

        # Duration logic: longer runs for running, medium for jumps
        if "jump" in best_action:
            frames = 25
        elif "wait" in best_action:
            frames = 15
        else:
            frames = 35

        return best_action, frames

    def run(self, history_recorder: ActionHistoryRecorder) -> None:
        print("\n" + "=" * 75)
        print(f"   [*] RUNNING COVERAGE-GUIDED EXPLORATION")
        print(f"     Max Actions : {self.max_actions}")
        print(f"     Grid Size   : {self.grid_size}px")
        print("=" * 75)

        for action_idx in range(1, self.max_actions + 1):
            state_before = self.controller.get_latest_state()
            player = (state_before.get("player") or {}) if state_before else {}

            # Handle death & respawn
            if not player.get("alive", True):
                print(f"  [Death Detected] Respawning via retry...")
                self.controller.retry()
                self.controller.wait_seconds(1.0)
                state_before = self.controller.get_latest_state()

            cell_before = self.discretize_state(state_before)
            self.state_visits[cell_before] = self.state_visits.get(cell_before, 0) + 1

            # Select guided action
            chosen_actions, frames = self.select_action(state_before)
            dur_sec = round(frames / float(self.controller.fps), 3)

            act_str = str(chosen_actions)
            self.action_history_counts[act_str] = self.action_history_counts.get(act_str, 0) + 1

            event_id_before = self.controller.get_latest_event_id()

            print(f"[{action_idx:03d}/{self.max_actions}] Action: {chosen_actions} for {dur_sec}s ({frames}f)")

            if "wait" in chosen_actions:
                self.controller.release_all()
            else:
                self.controller.press_actions(chosen_actions)

            self.controller.wait_seconds(dur_sec)
            self.controller.release_all()

            state_after = self.controller.get_latest_state()
            cell_after = self.discretize_state(state_after)
            self.state_visits[cell_after] = self.state_visits.get(cell_after, 0) + 1

            events = self.controller.get_events_since(event_id_before)
            history_recorder.record_step(action_idx, chosen_actions, dur_sec, state_before, state_after,
                                         "success", events)

            p_pos = (state_after.get("player") or {}).get("position", {}) if state_after else {}
            score = (state_after.get("stats") or {}).get("score", 0) if state_after else 0
            unique_cells = len(self.state_visits)
            print(f"  -> Pos: ({p_pos.get('x')}, {p_pos.get('y')}) | Score: {score} | Unique Cells: {unique_cells} | Events: +{len(events)}")


# ==============================================================================
# GODOT LAUNCHER HELPER
# ==============================================================================

def launch_godot_game(level_path: Optional[str] = None) -> Optional[subprocess.Popen]:
    """Finds Godot 4 executable and launches the platformer game."""
    root_dir = os.path.dirname(os.path.abspath(__file__))
    candidates = [
        os.path.join(root_dir, "engine", "Godot_v4.3-stable_win64.exe"),
        os.path.join(root_dir, "engine", "Godot_v4.4-stable_win64.exe"),
        os.path.join(root_dir, "engine", "godot.exe"),
        os.path.join(root_dir, "..", "godot engine", "Godot_v4.3-stable_win64.exe"),
        "godot"
    ]

    exe = None
    for c in candidates:
        if os.path.exists(c):
            exe = c
            break

    if not exe:
        print("[WARNING] Could not auto-detect Godot 4 executable. Please ensure game is running.")
        return None

    cmd = [exe, "--path", os.path.join(root_dir, "godot-4game")]
    if level_path:
        cmd.append(level_path)

    print(f"[LAUNCH] Starting Godot process: {exe}...")
    proc = subprocess.Popen(cmd, cwd=os.path.join(root_dir, "godot-4game"))
    time.sleep(2.0)
    return proc


# ==============================================================================
# MAIN CLI
# ==============================================================================

def main():
    parser = argparse.ArgumentParser(description="AI Game Tester Explorer for GDQuest 2D Platformer")
    parser.add_argument("--mode", choices=["scripted", "random", "coverage_guided"], default="scripted",
                        help="Exploration mode (default: scripted)")
    parser.add_argument("--path", default="paths/basic_platformer.json",
                        help="Path to JSON file for scripted mode (default: paths/basic_platformer.json)")
    parser.add_argument("--seed", type=int, default=42,
                        help="Random seed for random mode (default: 42)")
    parser.add_argument("--max-actions", type=int, default=100,
                        help="Maximum actions for random or coverage_guided mode")
    parser.add_argument("--port", type=int, default=DEFAULT_UDP_PORT,
                        help="UDP control port (default: 4242)")
    parser.add_argument("--fps", type=int, default=DEFAULT_FPS,
                        help="Physics frames per second (default: 60)")
    parser.add_argument("--launch", action="store_true",
                        help="Auto-launch Godot game process if not running")
    parser.add_argument("--level", default="res://src/Levels/Level01.tscn",
                        help="Level scene path to launch (default: res://src/Levels/Level01.tscn)")
    parser.add_argument("--history-out", default=None,
                        help="Custom filename for saving action history JSON")
    parser.add_argument("--verbose", action="store_true",
                        help="Print detailed execution traces")

    args = parser.parse_args()

    # Launch game if requested
    godot_proc = None
    if args.launch:
        godot_proc = launch_godot_game(args.level)

    controller = GameController(port=args.port, fps=args.fps)
    connected = controller.connect(retries=4, retry_interval=0.5)

    if not connected:
        print("\n[NOTE] Game is not currently responding to UDP handshake.")
        print("       Please run the game via 'run_game.bat' or use '--launch' flag.")
        print("       Continuing with file-based / fallback telemetry...\n")

    metadata = {
        "mode": args.mode,
        "seed": args.seed if args.mode == "random" else None,
        "path_file": args.path if args.mode == "scripted" else None,
        "max_actions": args.max_actions if args.mode != "scripted" else None,
        "udp_connected": connected
    }

    history_recorder = ActionHistoryRecorder(args.mode, metadata)

    try:
        if args.mode == "scripted":
            executor = ScriptedExecutor(controller, verbose=args.verbose)
            executor.run(args.path, history_recorder)
        elif args.mode == "random":
            explorer = RandomExplorer(controller, seed=args.seed, max_actions=args.max_actions)
            explorer.run(history_recorder)
        elif args.mode == "coverage_guided":
            explorer = CoverageGuidedExplorer(controller, max_actions=args.max_actions)
            explorer.run(history_recorder)
    finally:
        controller.close()
        saved_history = history_recorder.finalize(args.history_out)
        print(f"\n[ACTION HISTORY] Saved reproducibility history log to: {saved_history}")


if __name__ == "__main__":
    main()
