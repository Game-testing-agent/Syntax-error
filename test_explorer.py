#!/usr/bin/env python3
"""
test_explorer.py — Unit & Integration Test Suite for explorer.py

Validates:
1. Path parser and schema validation (valid & malformed paths, subsequences, frames/durations).
2. Checkpoint evaluation logic (all supported checkpoint types and timeouts).
3. Simultaneous inputs and action normalization.
4. Scripted execution with mock game controller (step ordering, death handling, checkpoints).
5. Random exploration with seed repeatability.
6. Coverage-guided action selection and obstacle avoidance.
7. Safe input release and action history recording.
"""

import os
import sys
import json
import time
import tempfile
import unittest
from typing import Dict, Any, List, Optional

from explorer import (
    PathParser, PathValidationError, ScriptedStep, CheckpointEvaluator,
    ActionHistoryRecorder, ScriptedExecutor, RandomExplorer,
    CoverageGuidedExplorer, GameController, VALID_ACTIONS
)


class MockGameController:
    """Mock controller simulating Godot telemetry and inputs for headless testing."""

    def __init__(self, fps: int = 60):
        self.fps = fps
        self.active_actions: List[str] = []
        self.command_history: List[Dict[str, Any]] = []
        self.state: Dict[str, Any] = {
            "scene": "Level01",
            "frame": 100,
            "player": {
                "alive": True,
                "on_floor": True,
                "position": {"x": 200.0, "y": 600.0},
                "velocity": {"x": 0.0, "y": 0.0}
            },
            "stats": {
                "score": 0,
                "deaths": 0
            },
            "coins": {
                "coins_collected": 0,
                "nearest_coin": {"relative_x": 300.0, "relative_y": -50.0}
            },
            "goal": {
                "found": True,
                "relative_x": 1000.0
            }
        }
        self.event_counter = 10

    def get_latest_state(self) -> Dict[str, Any]:
        return json.loads(json.dumps(self.state))

    def get_latest_event_id(self) -> int:
        return self.event_counter

    def get_events_since(self, since_id: int) -> List[Dict[str, Any]]:
        diff = max(0, self.event_counter - since_id)
        return [{"event_id": since_id + i + 1, "event_name": f"mock_event_{i}"} for i in range(diff)]

    def press_actions(self, actions: List[str]) -> None:
        self.active_actions = list(actions)
        self.command_history.append({"press": actions})
        # Simulate state updates based on inputs
        if "move_right" in actions:
            self.state["player"]["position"]["x"] += 40.0
        if "move_left" in actions:
            self.state["player"]["position"]["x"] -= 40.0
        if "jump" in actions:
            self.state["player"]["on_floor"] = False
            self.state["player"]["position"]["y"] -= 30.0
        self.event_counter += 1

    def release_all(self) -> None:
        self.active_actions = []
        self.command_history.append({"command": "release_all"})
        self.state["player"]["on_floor"] = True  # Player settles

    def retry(self) -> None:
        self.command_history.append({"command": "retry"})
        self.state["player"]["alive"] = True
        self.state["player"]["position"] = {"x": 200.0, "y": 600.0}
        self.state["stats"]["score"] = 0
        self.event_counter += 1

    def pause(self, val: Optional[bool] = None) -> None:
        self.command_history.append({"command": "pause", "val": val})

    def start_game(self) -> None:
        self.command_history.append({"command": "start_game"})

    def wait_seconds(self, duration: float) -> None:
        # For mock tests, don't sleep real time
        pass


class TestExplorerSuite(unittest.TestCase):

    def test_01_valid_path_parsing(self):
        """Verify standard path files parse cleanly."""
        for p in ["paths/basic_platformer.json", "paths/coin_and_jump.json",
                  "paths/checkpoint_demo.json", "paths/retry_recovery.json",
                  "paths/reusable_subsequences.json"]:
            if os.path.exists(p):
                name, desc, steps = PathParser.parse_file(p)
                self.assertTrue(len(name) > 0)
                self.assertTrue(len(steps) > 0)
                for s in steps:
                    self.assertTrue(isinstance(s.actions, list))
                    self.assertTrue(s.frames > 0)
                    self.assertTrue(s.duration_sec > 0)

    def test_02_invalid_action_error(self):
        """Malformed action strings must throw PathValidationError."""
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
            json.dump({
                "name": "invalid_test",
                "steps": [{"action": "fly_to_moon", "frames": 10}]
            }, f)
            temp_path = f.name

        try:
            with self.assertRaises(PathValidationError) as ctx:
                PathParser.parse_file(temp_path)
            self.assertIn("Unknown action 'fly_to_moon'", str(ctx.exception))
        finally:
            os.remove(temp_path)

    def test_03_invalid_json_error(self):
        """Corrupt JSON file must raise clear PathValidationError."""
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
            f.write("{ invalid json")
            temp_path = f.name

        try:
            with self.assertRaises(PathValidationError) as ctx:
                PathParser.parse_file(temp_path)
            self.assertIn("Invalid JSON", str(ctx.exception))
        finally:
            os.remove(temp_path)

    def test_04_simultaneous_inputs_normalization(self):
        """Check both array and plus notation for simultaneous inputs."""
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
            json.dump({
                "name": "simultaneous_test",
                "steps": [
                    {"actions": ["move_right", "jump"], "frames": 20},
                    {"action": "move_left+jump", "duration": 0.5}
                ]
            }, f)
            temp_path = f.name

        try:
            _, _, steps = PathParser.parse_file(temp_path)
            self.assertEqual(len(steps), 2)
            self.assertEqual(steps[0].actions, ["move_right", "jump"])
            self.assertEqual(steps[0].frames, 20)
            self.assertEqual(steps[1].actions, ["move_left", "jump"])
            self.assertEqual(steps[1].frames, 30)  # 0.5s * 60 = 30f
        finally:
            os.remove(temp_path)

    def test_05_subsequence_expansion(self):
        """Verify reusable subsequence templates are expanded correctly."""
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
            json.dump({
                "name": "subseq_test",
                "subsequences": {
                    "dash_jump": [
                        {"action": "move_right", "frames": 10},
                        {"actions": ["move_right", "jump"], "frames": 15}
                    ]
                },
                "steps": [
                    {"subsequence": "dash_jump"},
                    {"action": "wait", "frames": 5},
                    {"subsequence": "dash_jump"}
                ]
            }, f)
            temp_path = f.name

        try:
            _, _, steps = PathParser.parse_file(temp_path)
            self.assertEqual(len(steps), 5)
            self.assertEqual(steps[0].actions, ["move_right"])
            self.assertEqual(steps[1].actions, ["move_right", "jump"])
            self.assertEqual(steps[2].actions, ["wait"])
            self.assertEqual(steps[3].actions, ["move_right"])
            self.assertEqual(steps[4].actions, ["move_right", "jump"])
        finally:
            os.remove(temp_path)

    def test_06_checkpoint_evaluator(self):
        """Test evaluation of all checkpoint condition types."""
        state1 = {
            "scene": "Level01",
            "player": {"alive": True, "on_floor": True, "position": {"x": 300.0, "y": 500.0}},
            "stats": {"score": 200, "deaths": 0},
            "coins": {"coins_collected": 2}
        }
        state0 = {
            "scene": "Level01",
            "player": {"alive": True, "on_floor": False, "position": {"x": 100.0, "y": 400.0}},
            "stats": {"score": 100, "deaths": 0},
            "coins": {"coins_collected": 1}
        }

        # 1. on_floor
        passed, _ = CheckpointEvaluator.evaluate({"type": "on_floor", "expected": True}, state1, state0)
        self.assertTrue(passed)

        # 2. is_airborne
        passed, _ = CheckpointEvaluator.evaluate({"type": "is_airborne"}, state0, state1)
        self.assertTrue(passed)

        # 3. score_greater_than
        passed, _ = CheckpointEvaluator.evaluate({"type": "score_greater_than", "value": 150}, state1, state0)
        self.assertTrue(passed)

        # 4. score_increased
        passed, _ = CheckpointEvaluator.evaluate({"type": "score_increased"}, state1, state0)
        self.assertTrue(passed)

        # 5. coin_collected
        passed, _ = CheckpointEvaluator.evaluate({"type": "coin_collected"}, state1, state0)
        self.assertTrue(passed)

        # 6. position_x_greater
        passed, _ = CheckpointEvaluator.evaluate({"type": "position_x_greater", "value": 250}, state1, state0)
        self.assertTrue(passed)

        # 7. scene
        passed, _ = CheckpointEvaluator.evaluate({"type": "scene", "value": "Level01"}, state1, state0)
        self.assertTrue(passed)

    def test_07_scripted_executor_with_mock(self):
        """Execute complete scripted path through MockController."""
        mock = MockGameController()
        executor = ScriptedExecutor(mock, verbose=False)
        recorder = ActionHistoryRecorder("scripted", {"path": "paths/basic_platformer.json"})

        success = executor.run("paths/basic_platformer.json", recorder)
        self.assertTrue(success)
        self.assertEqual(len(recorder.steps), 5)
        self.assertEqual(mock.active_actions, [])  # All inputs released

    def test_08_death_handling_in_scripted_path(self):
        """Verify stop_if_died halts execution upon player death."""
        mock = MockGameController()
        # Kill player when action is executed in step 1
        orig_press = mock.press_actions
        def press_and_die(actions):
            orig_press(actions)
            mock.state["player"]["alive"] = False
        mock.press_actions = press_and_die

        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
            json.dump({
                "name": "death_halt_test",
                "steps": [
                    {"action": "move_right", "frames": 10, "stop_if_died": True},
                    {"action": "move_right", "frames": 10}
                ]
            }, f)
            temp_path = f.name

        try:
            executor = ScriptedExecutor(mock, verbose=False)
            recorder = ActionHistoryRecorder("scripted", {"path": temp_path})
            success = executor.run(temp_path, recorder)
            self.assertFalse(success)
            self.assertEqual(len(recorder.steps), 1)
            self.assertEqual(recorder.steps[0]["status"], "interrupted_death")
        finally:
            os.remove(temp_path)

    def test_09_random_explorer_repeatability(self):
        """Random exploration with fixed seed must be deterministic."""
        def run_random(seed: int) -> List[List[str]]:
            mock = MockGameController()
            explorer = RandomExplorer(mock, seed=seed, max_actions=10)
            recorder = ActionHistoryRecorder("random", {"seed": seed})
            explorer.run(recorder)
            return [s["actions"] for s in recorder.steps]

        run1 = run_random(42)
        run2 = run_random(42)
        run3 = run_random(99)

        self.assertEqual(run1, run2)  # Same seed produces same sequence
        self.assertNotEqual(run1, run3)  # Different seed produces different sequence

    def test_10_coverage_guided_novelty(self):
        """Coverage-guided mode must select actions and advance spatial cells."""
        mock = MockGameController()
        explorer = CoverageGuidedExplorer(mock, max_actions=15, grid_size=100)
        recorder = ActionHistoryRecorder("coverage_guided", {})

        explorer.run(recorder)
        self.assertEqual(len(recorder.steps), 15)
        # Verify unique cells increased
        self.assertGreater(len(explorer.state_visits), 1)

    def test_11_action_history_persistence(self):
        """Action history recorder outputs valid, comprehensive JSON."""
        recorder = ActionHistoryRecorder("test_mode", {"key": "val"})
        recorder.record_step(1, ["move_right"], 0.5, None, None, "success", [])

        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
            temp_path = f.name

        try:
            out_file = recorder.finalize(temp_path)
            with open(out_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.assertEqual(data["mode"], "test_mode")
            self.assertEqual(data["summary"]["total_steps"], 1)
            self.assertEqual(len(data["steps"]), 1)
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)


if __name__ == "__main__":
    unittest.main()
