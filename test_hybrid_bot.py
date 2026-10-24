#!/usr/bin/env python3
"""
test_hybrid_bot.py — Unit & Integration Test Suite for Hybrid Game Bot

Validates:
1. Route loading and schema integrity for Level01 and Level02.
2. Waypoint advancement and scene transition tracking.
3. Behavior priority 1: Recovery on death and anti-stuck.
4. Behavior priority 2: Enemy threat detection, jump timing, and air steering stomp.
5. Behavior priority 3 & 4: Waypoint navigation and planned jump execution.
6. Behavior priority 5: Optional collectible coin detours.
7. End-to-end simulated execution with MockGameController.
8. Seeded variation reproducibility.
"""

import os
import json
import unittest
from typing import Dict, Any, List, Optional

from bot_controller import (
    BehaviorState, LevelRouteManager, HybridBotController, HybridBotRunner
)


class MockTelemetryController:
    """Simulates Godot physics, inputs, and telemetry transitions for testing."""

    def __init__(self, fps: int = 60):
        self.fps = fps
        self.active_actions: List[str] = []
        self.command_history: List[Dict[str, Any]] = []
        self.event_counter = 50
        self.state: Dict[str, Any] = {
            "scene": "Level01",
            "game_state": "playing",
            "frame": 100,
            "player": {
                "alive": True,
                "on_floor": True,
                "position": {"x": 200.0, "y": 760.0},
                "velocity": {"x": 0.0, "y": 0.0}
            },
            "stats": {
                "score": 0,
                "deaths": 0
            },
            "coins": {
                "coins_collected": 0,
                "nearest_coin": None
            },
            "enemies": {
                "count": 1,
                "closest_enemy": {
                    "id": 999,
                    "name": "Enemy",
                    "x": 2080.0,
                    "y": 800.0,
                    "distance": 1880.0,
                    "relative_x": 1880.0,
                    "relative_y": 40.0,
                    "player_is_above": False,
                    "is_stompable": False,
                    "is_threat": False
                }
            },
            "goal": {
                "found": True,
                "portal_x": 7410.0,
                "portal_y": 160.0,
                "distance_to_portal": 7210.0
            }
        }

    def get_latest_state(self) -> Dict[str, Any]:
        return json.loads(json.dumps(self.state))

    def get_latest_event_id(self) -> int:
        return self.event_counter

    def get_events_since(self, since_id: int) -> List[Dict[str, Any]]:
        diff = max(0, self.event_counter - since_id)
        return [{"event_id": since_id + i + 1, "event_name": f"event_{i}"} for i in range(diff)]

    def press_actions(self, actions: List[str]) -> None:
        self.active_actions = list(actions)
        self.command_history.append({"press": actions})
        p = self.state["player"]["position"]

        # Kinematic approximation
        if "move_right" in actions:
            p["x"] += 60.0
        if "move_left" in actions:
            p["x"] -= 60.0
        if "jump" in actions:
            self.state["player"]["on_floor"] = False
            p["y"] -= 80.0
        self.event_counter += 1

    def release_all(self) -> None:
        self.active_actions = []
        self.command_history.append({"command": "release_all"})
        # Player lands back down if airborne
        self.state["player"]["on_floor"] = True

    def retry(self) -> None:
        self.command_history.append({"command": "retry"})
        self.state["player"]["alive"] = True
        self.state["player"]["on_floor"] = True
        self.state["player"]["position"] = {"x": 200.0, "y": 760.0}
        self.state["game_state"] = "playing"
        self.event_counter += 1

    def wait_seconds(self, duration: float) -> None:
        pass

    def pause(self, val: Optional[bool] = None) -> None:
        self.command_history.append({"command": "pause", "val": val})
        self.state["game_state"] = "paused" if val is not False else "playing"


class TestHybridBot(unittest.TestCase):

    def setUp(self):
        self.routes_path = os.path.join(os.path.dirname(__file__), "level_routes.json")
        self.route_mgr = LevelRouteManager(self.routes_path)
        self.bot = HybridBotController(self.route_mgr, variation_mode=False, seed=42)

    def test_routes_file_loaded_correctly(self):
        """Validates level_routes.json exists and has valid schemas for Level01 & Level02."""
        self.assertIn("Level01", self.route_mgr.routes_data)
        self.assertIn("Level02", self.route_mgr.routes_data)

        l1 = self.route_mgr.get_route("Level01")
        self.assertEqual(l1["start_position"]["x"], 200.0)
        self.assertGreaterEqual(len(l1["waypoints"]), 10)

        # Final waypoint must be reach_portal
        last_wp_l1 = l1["waypoints"][-1]
        self.assertEqual(last_wp_l1["objective"], "reach_portal")

        l2 = self.route_mgr.get_route("Level02")
        self.assertGreaterEqual(len(l2["waypoints"]), 6)
        last_wp_l2 = l2["waypoints"][-1]
        self.assertEqual(last_wp_l2["objective"], "reach_portal")

    def test_priority1_death_recovery(self):
        """When player is dead, bot immediately issues retry under RECOVERY behavior."""
        dead_state = {
            "scene": "Level01",
            "player": {"alive": False, "on_floor": False, "position": {"x": 500.0, "y": 800.0}},
            "enemies": {},
            "coins": {}
        }
        actions, frames, behavior, reason = self.bot.decide_action(dead_state)
        self.assertEqual(behavior, BehaviorState.RECOVERY)
        self.assertIn("retry", actions)
        self.assertIn("death", reason.lower())
        self.assertEqual(self.bot.recovery_attempts, 1)

    def test_priority1_stuck_recovery(self):
        """When player position remains static across ticks, anti-stuck activates."""
        state = {
            "scene": "Level01",
            "player": {"alive": True, "on_floor": True, "position": {"x": 400.0, "y": 800.0}},
            "enemies": {},
            "coins": {}
        }
        # Feed unchanged position 8 times
        for _ in range(8):
            self.bot.decide_action(state)

        actions, frames, behavior, reason = self.bot.decide_action(state)
        self.assertEqual(behavior, BehaviorState.RECOVERY)
        self.assertTrue("jump" in actions or "move_left" in actions)
        self.assertIn("stuck", reason.lower())

    def test_priority2_enemy_stomp_initiation(self):
        """When an enemy is in threat range approaching player, bot initiates jump stomp."""
        threat_state = {
            "scene": "Level01",
            "player": {"alive": True, "on_floor": True, "position": {"x": 1900.0, "y": 800.0}},
            "enemies": {
                "closest_enemy": {
                    "name": "Enemy",
                    "x": 2080.0,
                    "y": 800.0,
                    "distance": 180.0,
                    "relative_x": 180.0,
                    "relative_y": 0.0,
                    "player_is_above": False,
                    "is_stompable": False,
                    "is_threat": True
                }
            },
            "coins": {}
        }
        actions, frames, behavior, reason = self.bot.decide_action(threat_state)
        self.assertEqual(behavior, BehaviorState.COMBAT_STOMP)
        self.assertIn("jump", actions)
        self.assertIn("move_right", actions)
        self.assertIn("stomp", reason.lower())

    def test_priority2_air_steering_stomp(self):
        """When player is airborne and above enemy, air steering guides onto enemy head."""
        air_state = {
            "scene": "Level01",
            "player": {"alive": True, "on_floor": False, "position": {"x": 2050.0, "y": 720.0}},
            "enemies": {
                "closest_enemy": {
                    "name": "Enemy",
                    "x": 2080.0,
                    "y": 800.0,
                    "distance": 85.0,
                    "relative_x": 30.0,
                    "relative_y": 80.0,
                    "player_is_above": True,
                    "is_stompable": True,
                    "is_threat": False
                }
            },
            "coins": {}
        }
        actions, frames, behavior, reason = self.bot.decide_action(air_state)
        self.assertEqual(behavior, BehaviorState.COMBAT_STOMP)
        self.assertIn("move_right", actions)
        self.assertIn("stomp", reason.lower())

    def test_waypoint_jump_execution(self):
        """When player reaches jump trigger coordinate for a waypoint, executes jump."""
        # Find a waypoint with jump
        wp_with_jump = None
        for idx, wp in enumerate(self.route_mgr.get_route("Level01")["waypoints"]):
            if "jump" in wp:
                self.route_mgr.current_waypoint_idx = idx
                wp_with_jump = wp
                break

        self.assertIsNotNone(wp_with_jump)
        trig_x = wp_with_jump["jump"]["trigger_x"]

        jump_state = {
            "scene": "Level01",
            "player": {"alive": True, "on_floor": True, "position": {"x": trig_x + 10.0, "y": 800.0}},
            "enemies": {},
            "coins": {}
        }
        actions, frames, behavior, reason = self.bot.decide_action(jump_state)
        self.assertIn("jump", actions)
        self.assertIn("planned jump", reason.lower())

    def test_scene_transition_to_level02(self):
        """Scene change from Level01 to Level02 resets waypoint index to 0 for Level02."""
        self.assertEqual(self.route_mgr.current_level, "Level01")
        self.route_mgr.current_waypoint_idx = 5

        l2_state = {
            "scene": "Level02",
            "player": {"alive": True, "on_floor": True, "position": {"x": 180.0, "y": 480.0}},
            "enemies": {},
            "coins": {}
        }
        self.bot.decide_action(l2_state)
        self.assertEqual(self.route_mgr.current_level, "Level02")
        self.assertEqual(self.route_mgr.current_waypoint_idx, 0)

    def test_end_screen_victory_recognition(self):
        """EndScreen scene triggers victory completion."""
        win_state = {
            "scene": "EndScreen",
            "game_state": "victory",
            "player": {"alive": False},
            "enemies": {},
            "coins": {}
        }
        actions, frames, behavior, reason = self.bot.decide_action(win_state)
        self.assertEqual(behavior, BehaviorState.OBJECTIVE)
        self.assertIn("complete", reason.lower())

    def test_variation_mode_reproducibility(self):
        """Fixed seed in variation mode produces deterministic actions."""
        bot1 = HybridBotController(LevelRouteManager(self.routes_path), variation_mode=True, seed=123)
        bot2 = HybridBotController(LevelRouteManager(self.routes_path), variation_mode=True, seed=123)

        state = {
            "scene": "Level01",
            "player": {"alive": True, "on_floor": True, "position": {"x": 1130.0, "y": 800.0}},
            "enemies": {},
            "coins": {}
        }
        res1 = bot1.decide_action(state)
        res2 = bot2.decide_action(state)
        self.assertEqual(res1, res2)

    def test_full_playthrough_simulation(self):
        """Simulates full playthrough progressing from Level01 through Level02 to EndScreen."""
        from explorer import ActionHistoryRecorder

        mock_ctrl = MockTelemetryController()
        runner = HybridBotRunner(mock_ctrl, routes_file=self.routes_path, max_steps=300)
        recorder = ActionHistoryRecorder("hybrid_test", {"test": True})

        # Run simulation with simulated movement towards portals
        for step in range(300):
            st = mock_ctrl.get_latest_state()
            px = st["player"]["position"]["x"]

            # Simulate natural level transitions at portal coordinates
            if st["scene"] == "Level01" and px >= 7400.0:
                mock_ctrl.state["scene"] = "Level02"
                mock_ctrl.state["player"]["position"] = {"x": 180.0, "y": 480.0}
            elif st["scene"] == "Level02" and px >= 4050.0:
                mock_ctrl.state["scene"] = "EndScreen"
                mock_ctrl.state["game_state"] = "victory"

            actions, frames, behavior, reason = runner.bot.decide_action(mock_ctrl.get_latest_state())
            if "release_all" in actions and "EndScreen" in mock_ctrl.state["scene"]:
                runner.victory = True
                break

            mock_ctrl.press_actions(actions)
            mock_ctrl.release_all()

    def test_target_coordinate_navigation_to_3117_560(self):
        """Simulates target coordinate explorer routing specifically to (3117.0, 560.0)."""
        from explorer import ActionHistoryRecorder

        mock_ctrl = MockTelemetryController()
        mock_ctrl.state["player"]["position"] = {"x": 200.0, "y": 760.0}
        runner = HybridBotRunner(
            mock_ctrl,
            routes_file=self.routes_path,
            target_level="Level01",
            target_coord=(3117.0, 560.0),
            coord_tolerance=60.0,
            max_steps=100
        )
        recorder = ActionHistoryRecorder("target_coord_test", {"coord": (3117.0, 560.0)})
        success = runner.run(recorder)
        self.assertTrue(success)
        self.assertTrue(runner.target_reached)
        final_x = mock_ctrl.state["player"]["position"]["x"]
        self.assertAlmostEqual(final_x, 3117.0, delta=70.0)
        # Verify game was paused on target reached
        self.assertEqual(mock_ctrl.state["game_state"], "paused")
        self.assertTrue(any(c.get("command") == "pause" for c in mock_ctrl.command_history))

    def test_auto_retry_on_player_death_in_runner(self):
        """Simulates player dying mid-run; validates auto-retry is issued and route resets."""
        from explorer import ActionHistoryRecorder

        mock_ctrl = MockTelemetryController()
        mock_ctrl.state["player"]["position"] = {"x": 200.0, "y": 760.0}
        runner = HybridBotRunner(
            mock_ctrl,
            routes_file=self.routes_path,
            target_level="Level01",
            target_coord=(3117.0, 560.0),
            coord_tolerance=60.0,
            max_steps=10
        )
        died_once = [False]
        orig_press = mock_ctrl.press_actions

        def death_press(actions):
            orig_press(actions)
            if not died_once[0] and mock_ctrl.state["player"]["position"]["x"] >= 320.0:
                died_once[0] = True
                mock_ctrl.state["player"]["alive"] = False
                mock_ctrl.state["game_state"] = "player_died"

        mock_ctrl.press_actions = death_press
        recorder = ActionHistoryRecorder("retry_test", {"coord": (3117.0, 560.0)})
        runner.run(recorder)
        # Verify retry command was sent to game controller
        retry_commands = [c for c in mock_ctrl.command_history if c.get("command") == "retry"]
        self.assertGreaterEqual(len(retry_commands), 1)

    def test_navigate_to_sequential_legs(self):
        """Validates that navigate_to can be called sequentially for multi-point legs."""
        mock_ctrl = MockTelemetryController()
        mock_ctrl.state["player"]["position"] = {"x": 200.0, "y": 760.0}
        runner = HybridBotRunner(
            mock_ctrl,
            routes_file=self.routes_path,
            target_level="Level01",
            coord_tolerance=60.0,
            max_steps=50
        )
        # Leg 1: (850, 750)
        reached1 = runner.navigate_to(850.0, 750.0, pause_on_reach=True)
        self.assertTrue(reached1)
        self.assertTrue(runner.target_reached)
        self.assertEqual(mock_ctrl.state["game_state"], "paused")
        self.assertAlmostEqual(mock_ctrl.state["player"]["position"]["x"], 850.0, delta=70.0)

        # Leg 2: (1500, 700)
        reached2 = runner.navigate_to(1500.0, 700.0, pause_on_reach=True)
        self.assertTrue(reached2)
        self.assertTrue(runner.target_reached)
        self.assertEqual(mock_ctrl.state["game_state"], "paused")
        self.assertAlmostEqual(mock_ctrl.state["player"]["position"]["x"], 1500.0, delta=70.0)

    def test_interactive_waypoints_explorer(self):
        """Simulates interactive terminal input for Waypoint 1 mode."""
        from explorer import InteractiveWaypointsExplorer

        mock_ctrl = MockTelemetryController()
        mock_ctrl.state["player"]["position"] = {"x": 200.0, "y": 760.0}

        inputs = iter(["850 750", "1500 700", "quit"])
        explorer = InteractiveWaypointsExplorer(
            mock_ctrl,
            routes_file=self.routes_path,
            tolerance=60.0,
            max_steps_per_point=50,
            input_fn=lambda prompt: next(inputs)
        )
        success = explorer.run()
        self.assertTrue(success)
        self.assertEqual(len(explorer.visited_waypoints), 2)
        self.assertEqual(explorer.visited_waypoints[0], (850.0, 750.0))
        self.assertEqual(explorer.visited_waypoints[1], (1500.0, 700.0))
        self.assertEqual(mock_ctrl.state["game_state"], "paused")

    def test_sequential_waypoints_explorer_preconfigured(self):
        """Simulates sequential execution with 3 seconds wait (mocked) for Waypoint 2 mode."""
        from explorer import SequentialWaypointsExplorer

        mock_ctrl = MockTelemetryController()
        mock_ctrl.state["player"]["position"] = {"x": 200.0, "y": 760.0}

        waypoints = [(850.0, 750.0), (1500.0, 700.0)]
        explorer = SequentialWaypointsExplorer(
            mock_ctrl,
            waypoints=waypoints,
            routes_file=self.routes_path,
            tolerance=60.0,
            wait_between=0.01,  # Shortened for rapid test execution
            max_steps_per_point=50
        )
        success = explorer.run()
        self.assertTrue(success)
        self.assertEqual(len(explorer.completed_waypoints), 2)
        # Verify game remains live (not paused) at final destination
        self.assertEqual(mock_ctrl.state["game_state"], "playing")

    def test_sequential_waypoints_prompt_setup(self):
        """Simulates interactive startup prompt for N coordinates in Waypoint 2 mode."""
        from explorer import SequentialWaypointsExplorer

        mock_ctrl = MockTelemetryController()
        user_inputs = iter(["2", "850 750", "1500 700"])

        explorer = SequentialWaypointsExplorer(
            mock_ctrl,
            routes_file=self.routes_path,
            input_fn=lambda prompt: next(user_inputs)
        )
        explorer.prompt_for_waypoints()
        self.assertEqual(len(explorer.waypoints), 2)
        self.assertEqual(explorer.waypoints[0], (850.0, 750.0))
        self.assertEqual(explorer.waypoints[1], (1500.0, 700.0))

    def test_waypoint_death_auto_retry_and_resumption(self):
        """Validates that dying mid-waypoint triggers auto-retry, respawns, and still completes target."""
        from explorer import SequentialWaypointsExplorer

        mock_ctrl = MockTelemetryController()
        mock_ctrl.state["player"]["position"] = {"x": 200.0, "y": 760.0}

        died_once = [False]
        orig_press = mock_ctrl.press_actions

        def death_press(actions):
            orig_press(actions)
            # Trigger death when player moves past X=400 on leg to 850
            if not died_once[0] and mock_ctrl.state["player"]["position"]["x"] >= 400.0:
                died_once[0] = True
                mock_ctrl.state["player"]["alive"] = False
                mock_ctrl.state["game_state"] = "player_died"

        mock_ctrl.press_actions = death_press

        explorer = SequentialWaypointsExplorer(
            mock_ctrl,
            waypoints=[(850.0, 750.0)],
            routes_file=self.routes_path,
            tolerance=60.0,
            wait_between=0.01,
            max_steps_per_point=60
        )
        success = explorer.run()
        self.assertTrue(success)
        self.assertEqual(len(explorer.completed_waypoints), 1)
        # Verify auto-retry happened
        retries = [c for c in mock_ctrl.command_history if c.get("command") == "retry"]
        self.assertGreaterEqual(len(retries), 1)
        # Verify destination reached despite death
        final_x = mock_ctrl.state["player"]["position"]["x"]
        self.assertAlmostEqual(final_x, 850.0, delta=70.0)

    def test_target_coordinate_stair_5778_480_preserves_steps(self):
        """Validates that for target coordinate (5778.0, 480.0), stair 1 (5720, 640) is preserved as an intermediate step."""
        mgr = LevelRouteManager(self.routes_path)
        mgr.set_target_coordinate(5778.0, 480.0)
        route = mgr.get_route("Level01")
        wps = route.get("waypoints", [])
        # Ensure wp_13_end_stair_1 (x=5720, y=640) is in the route
        stair1_found = any(wp.get("id") == "wp_13_end_stair_1" for wp in wps)
        self.assertTrue(stair1_found, "Intermediate stair wp_13_end_stair_1 must be preserved before (5778, 480)")
        # Final waypoint must be at (5778.0, 480.0)
        last_wp = wps[-1]
        self.assertEqual(last_wp.get("x"), 5778.0)
        self.assertEqual(last_wp.get("y"), 480.0)

    def test_backward_coordinate_adjustment(self):
        """Validates that when player overshoots a target coordinate, the bot steps back left with gentle pacing."""
        mgr = LevelRouteManager(self.routes_path)
        mgr.set_target_coordinate(5778.0, 480.0)
        bot = HybridBotController(mgr)
        # Advance route to final target waypoint
        mgr.current_waypoint_idx = len(mgr.get_route("Level01")["waypoints"]) - 1

        # Simulate player landing at X=5820 (past target 5778)
        state = {
            "scene": "Level01",
            "game_state": "playing",
            "player": {
                "alive": True,
                "on_floor": True,
                "position": {"x": 5820.0, "y": 480.0},
                "velocity": {"x": 0.0, "y": 0.0}
            },
            "stats": {"score": 0, "deaths": 0}
        }
        actions, frames, behavior, reason = bot.decide_action(state)
        # Must move_left to adjust backwards
        self.assertIn("move_left", actions)
        # Step frames should be small/paced (not full 18-frame sprint)
        self.assertLessEqual(frames, 8)
        self.assertIn("adjusting left/back", reason.lower())

    def test_stuck_recovery_steps_back_before_jumping(self):
        """Validates that when stuck against a wall, phase 1 steps back to gain run-up room, and phase 2 jumps."""
        mgr = LevelRouteManager(self.routes_path)
        mgr.set_target_coordinate(5778.0, 480.0)
        mgr.advance_to_current_x(5700.0)
        bot = HybridBotController(mgr)
        state = {
            "scene": "Level01",
            "game_state": "playing",
            "player": {
                "alive": True,
                "on_floor": True,
                "position": {"x": 5700.0, "y": 800.0},
                "velocity": {"x": 0.0, "y": 0.0}
            },
            "stats": {"score": 0, "deaths": 0}
        }
        # Simulate staying at exact same position for 3 ticks
        bot.last_pos_x = 5700.0
        bot.stuck_counter = 2
        actions1, frames1, behavior1, reason1 = bot.decide_action(state)
        # Phase 1: must step back left away from wall
        self.assertIn("move_left", actions1)
        self.assertIn("stepping back", reason1.lower())

        # Next action: Phase 2: running jump
        actions2, frames2, behavior2, reason2 = bot.decide_action(state)
        self.assertIn("jump", actions2)
        self.assertIn("move_right", actions2)
        self.assertIn("running jump", reason2.lower())

    def test_high_platform_zigzag_route_for_6257_80(self):
        """Validates that for target (6257.0, 80.0), a zigzag route through Stair 1, 2, Platform 1, and Ledge 2 is generated."""
        mgr = LevelRouteManager(self.routes_path)
        mgr.set_target_coordinate(6257.0, 80.0)
        route = mgr.get_route("Level01")
        wps = route.get("waypoints", [])

        # Must include all climbing waypoints:
        wp_ids = [wp.get("id") for wp in wps]
        self.assertIn("wp_13_end_stair_1", wp_ids)
        self.assertIn("wp_14_end_stair_2", wp_ids)
        self.assertIn("wp_15_end_stair_3", wp_ids)
        self.assertIn("wp_16_portal_ledge", wp_ids)

        # Final waypoint must be the zigzag left jump to high platform
        last_wp = wps[-1]
        self.assertEqual(last_wp.get("id"), "wp_zigzag_high_platform")
        self.assertEqual(last_wp.get("x"), 6257.0)
        self.assertEqual(last_wp.get("y"), 80.0)
        jump_spec = last_wp.get("jump")
        self.assertIsNotNone(jump_spec)
        self.assertEqual(jump_spec.get("direction"), "move_left")

    def test_advance_from_stair2_to_6257_80(self):
        """When player is at (5778.0, 480.0) on stair 2, auto-advances to Platform 1 (wp_15) without stepping off stairs."""
        mgr = LevelRouteManager(self.routes_path)
        mgr.set_target_coordinate(6257.0, 80.0)
        cur_wp = mgr.advance_to_current_x(5778.0, 480.0)
        self.assertIsNotNone(cur_wp)
        self.assertEqual(cur_wp.get("id"), "wp_15_end_stair_3")

        # Bot should step right toward trigger 5880 with clean 9f/5f pacing
        bot = HybridBotController(mgr)
        state = {
            "scene": "Level01",
            "game_state": "playing",
            "player": {
                "alive": True,
                "on_floor": True,
                "position": {"x": 5778.0, "y": 480.0},
                "velocity": {"x": 0.0, "y": 0.0}
            },
            "stats": {"score": 0, "deaths": 0}
        }
        actions, frames, behavior, reason = bot.decide_action(state)
        self.assertIn("move_right", actions)
        self.assertIn(frames, (5, 9))

    def test_zigzag_left_jump_execution_and_midair_steering(self):
        """Validates that on Ledge 2, the bot executes a leftward jump with mid-air left glide."""
        mgr = LevelRouteManager(self.routes_path)
        mgr.set_target_coordinate(6257.0, 80.0)
        # Advance route to the final zigzag waypoint
        mgr.current_waypoint_idx = len(mgr.get_route("Level01")["waypoints"]) - 1
        bot = HybridBotController(mgr)

        # On Ledge 2 at X=6800, Y=240
        ground_state = {
            "scene": "Level01",
            "game_state": "playing",
            "player": {
                "alive": True,
                "on_floor": True,
                "position": {"x": 6800.0, "y": 240.0},
                "velocity": {"x": 0.0, "y": 0.0}
            },
            "stats": {"score": 0, "deaths": 0}
        }
        actions, frames, behavior, reason = bot.decide_action(ground_state)
        self.assertIn("jump", actions)
        self.assertIn("move_left", actions)
        self.assertEqual(bot.current_jump_direction, "move_left")

        # Mid-air state ascending
        air_state = {
            "scene": "Level01",
            "game_state": "playing",
            "player": {
                "alive": True,
                "on_floor": False,
                "position": {"x": 6600.0, "y": 180.0},
                "velocity": {"x": -600.0, "y": -400.0}
            },
            "stats": {"score": 0, "deaths": 0}
        }
        actions2, frames2, behavior2, reason2 = bot.decide_action(air_state)
        self.assertIn("move_left", actions2)
        self.assertEqual(frames2, 9)

    def test_no_pit_trap_retry_when_target_coordinate_active(self):
        """When player is navigating to custom coordinate and touches floor past X=5920, does not issue pit-trap retry."""
        mgr = LevelRouteManager(self.routes_path)
        mgr.set_target_coordinate(6257.0, 80.0)
        bot = HybridBotController(mgr)
        state = {
            "scene": "Level01",
            "game_state": "playing",
            "player": {
                "alive": True,
                "on_floor": True,
                "position": {"x": 6050.0, "y": 800.0},
                "velocity": {"x": 0.0, "y": 0.0}
            },
            "stats": {"score": 0, "deaths": 0}
        }
        actions, frames, behavior, reason = bot.decide_action(state)
        # Must not retry! Should step left toward Stair 1 base
        self.assertNotIn("retry", actions)
        self.assertIn("move_left", actions)

    def test_simulation_5778_to_6257_zigzag(self):
        """Simulates full navigation from stair 2 (5778, 480) climbing zigzag onto high platform (6257, 80)."""
        mock_ctrl = MockTelemetryController()
        mock_ctrl.state["player"]["position"] = {"x": 5778.0, "y": 480.0}

        orig_press = mock_ctrl.press_actions
        def kinematic_press(actions):
            orig_press(actions)
            p = mock_ctrl.state["player"]["position"]
            # Platform heights along the zigzag climb:
            # Platform 1: X=6160..6480, Y=400
            if 6160.0 <= p["x"] <= 6500.0 and p["y"] > 400.0:
                p["y"] = 400.0
            # Ledge 2: X=6700..7040, Y=240
            elif p["x"] >= 6700.0 and p["y"] > 240.0:
                p["y"] = 240.0
            # High platform: X=6160..6480, Y=80 (approached from left jump)
            elif 6160.0 <= p["x"] <= 6480.0 and "move_left" in actions and p["y"] > 80.0:
                p["y"] = 80.0

        mock_ctrl.press_actions = kinematic_press

        runner = HybridBotRunner(
            mock_ctrl,
            routes_file=self.routes_path,
            target_level="Level01",
            coord_tolerance=60.0,
            max_steps=50
        )
        reached = runner.navigate_to(6257.0, 80.0, pause_on_reach=True)
        self.assertTrue(reached)
        self.assertTrue(runner.target_reached)
        final_pos = mock_ctrl.state["player"]["position"]
        self.assertAlmostEqual(final_pos["x"], 6257.0, delta=70.0)
        self.assertAlmostEqual(final_pos["y"], 80.0, delta=80.0)


if __name__ == "__main__":
    unittest.main()



