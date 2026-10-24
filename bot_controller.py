#!/usr/bin/env python3
"""
bot_controller.py — Reactive Hybrid Game Bot for GDQuest 2D Platformer

Combines predefined level routes (level_routes.json) with real-time reactive
behavior priorities:
  1. Priority 1: Recovery (death recovery, anti-stuck, gap/wall recovery)
  2. Priority 2: Enemy Stomp & Threat Handling (jump timing, air steering, stomp confirmation)
  3. Priority 3: Objective Execution (portal transition, platform reaching, coin collection)
  4. Priority 4: Waypoint Navigation (kinematic guidance toward level waypoints)
  5. Priority 5: Controlled Exploration Variations (seeded jump offsets, optional coin detours)
"""

import os
import json
import random
import time
from enum import Enum
from typing import Dict, Any, List, Optional, Tuple


class BehaviorState(Enum):
    RECOVERY = "recovery"
    COMBAT_STOMP = "combat_stomp"
    OBJECTIVE = "objective"
    NAVIGATE = "navigate"
    VARIATION = "variation"


class LevelRouteManager:
    """Manages progression through predefined level waypoints and scene transitions."""

    def __init__(self, routes_file: Optional[str] = None):
        if not routes_file:
            routes_file = os.path.join(os.path.dirname(__file__), "level_routes.json")
        self.routes_file = routes_file
        self.routes_data: Dict[str, Any] = {}
        self.raw_routes_data: Dict[str, Any] = {}
        self.current_level: str = "Level01"
        self.current_waypoint_idx: int = 0
        self.completed_waypoints: List[str] = []
        self.target_coord: Optional[Tuple[float, Optional[float]]] = None
        self.load_routes()

    def load_routes(self) -> None:
        if not os.path.exists(self.routes_file):
            raise FileNotFoundError(f"Route configuration not found: {self.routes_file}")
        with open(self.routes_file, "r", encoding="utf-8") as f:
            self.raw_routes_data = json.load(f).get("routes", {})
            self.routes_data = json.loads(json.dumps(self.raw_routes_data))
        if self.target_coord is not None:
            self.set_target_coordinate(self.target_coord[0], self.target_coord[1])

    def get_route(self, level_name: str) -> Optional[Dict[str, Any]]:
        return self.routes_data.get(level_name)

    def current_waypoint(self) -> Optional[Dict[str, Any]]:
        route = self.get_route(self.current_level)
        if not route:
            return None
        waypoints = route.get("waypoints", [])
        if 0 <= self.current_waypoint_idx < len(waypoints):
            return waypoints[self.current_waypoint_idx]
        return None

    def update_scene(self, scene_name: str) -> bool:
        """Detects level transition and updates active route."""
        clean_name = scene_name
        if "Level01" in scene_name:
            clean_name = "Level01"
        elif "Level02" in scene_name:
            clean_name = "Level02"
        elif "EndScreen" in scene_name:
            clean_name = "EndScreen"

        if clean_name != self.current_level:
            prev = self.current_level
            self.current_level = clean_name
            self.current_waypoint_idx = 0
            print(f"[LevelRouteManager] Scene changed: {prev} -> {clean_name}. Route reset to waypoint 0.")
            return True
        return False

    def advance_waypoint(self) -> Optional[Dict[str, Any]]:
        wp = self.current_waypoint()
        if wp:
            self.completed_waypoints.append(wp.get("id", f"wp_{self.current_waypoint_idx}"))
        self.current_waypoint_idx += 1
        new_wp = self.current_waypoint()
        if new_wp:
            print(f"[LevelRouteManager] Advanced to Waypoint [{self.current_waypoint_idx}]: {new_wp.get('id')} ({new_wp.get('description', '')})")
        else:
            print(f"[LevelRouteManager] Completed all waypoints for {self.current_level}!")
        return new_wp

    def advance_to_current_x(self, px: float, py: Optional[float] = None) -> Optional[Dict[str, Any]]:
        """Automatically skips past waypoints that the player has already crossed horizontally."""
        route = self.get_route(self.current_level)
        if not route:
            return None
        waypoints = route.get("waypoints", [])
        while self.current_waypoint_idx < len(waypoints) - 1:
            wp = waypoints[self.current_waypoint_idx]
            tol_x = float(wp.get("tolerance_x", 60.0))
            wx = float(wp.get("x", 0.0))
            wy = float(wp.get("y", 0.0))
            # Never auto-skip the final portal exit waypoint or custom coordinate target
            if wp.get("objective") in ("reach_portal", "reach_target"):
                break
            # If waypoint requires reach_platform, do not auto-advance if player is far below platform elevation
            if wp.get("objective") == "reach_platform" and py is not None and py > wy + 120.0:
                break
            # If player is already on or above platform elevation and past horizontal entry, waypoint is satisfied
            if wp.get("objective") == "reach_platform" and py is not None and py <= wy + 80.0 and px >= wx - tol_x:
                self.completed_waypoints.append(wp.get("id", f"wp_{self.current_waypoint_idx}"))
                self.current_waypoint_idx += 1
                new_wp = self.current_waypoint()
                print(f"[LevelRouteManager] Auto-advanced past already reached platform Waypoint [{self.current_waypoint_idx}]: {new_wp.get('id') if new_wp else 'None'} (px={round(px, 1)}, py={round(py, 1)})")
                continue
            if px > wx + tol_x:
                self.completed_waypoints.append(wp.get("id", f"wp_{self.current_waypoint_idx}"))
                self.current_waypoint_idx += 1
                new_wp = self.current_waypoint()
                print(f"[LevelRouteManager] Auto-advanced to Waypoint [{self.current_waypoint_idx}]: {new_wp.get('id')} (px={round(px, 1)} > {wx})")
            else:
                break
        return self.current_waypoint()

    def set_target_coordinate(self, tx: float, ty: Optional[float] = None, tolerance_x: float = 60.0) -> None:
        """Adapts and truncates the active route to lead directly to a specific target coordinate (tx, ty)."""
        self.target_coord = (tx, ty)
        route = self.get_route(self.current_level)
        if not route:
            return
        waypoints = self.raw_routes_data.get(self.current_level, {}).get("waypoints", [])

        # Check if target in Level01 is on the high platform above Platform 1 (e.g. (6257, 80))
        # High platform spans X=6160..6480 at Y=80. Reaching Y=80 requires climbing via Ledge 2 (X=6800, Y=240)
        # and then jumping zigzag to the LEFT onto the high platform.
        is_level01_high_platform = (
            self.current_level == "Level01"
            and 6050.0 <= tx <= 6550.0
            and ty is not None
            and ty <= 200.0
        )

        if is_level01_high_platform:
            filtered_wps = []
            for wp in waypoints:
                if wp.get("id") in ("wp_17_enter_portal",):
                    continue
                wp_copy = dict(wp)
                if wp.get("id") == "wp_16_portal_ledge":
                    wp_copy["x"] = 6800.0
                    filtered_wps.append(wp_copy)
                    break
                filtered_wps.append(wp_copy)

            # Zigzag jump left from Ledge 2 onto the high platform
            filtered_wps.append({
                "id": "wp_zigzag_high_platform",
                "x": tx,
                "y": ty,
                "tolerance_x": tolerance_x,
                "jump": {
                    "trigger_x": 6820.0,
                    "direction": "move_left",
                    "min_frames": 36
                },
                "objective": "reach_target",
                "description": f"Zigzag jump left from ledge onto high platform target ({tx}, {ty})"
            })
            route["waypoints"] = filtered_wps
            self.current_waypoint_idx = 0
            print(f"[LevelRouteManager] Target coordinate set to ({tx}, {ty}) via high platform zigzag route ({len(filtered_wps)} waypoints).")
            return

        filtered_wps = []
        for wp in waypoints:
            wx = float(wp.get("x", 0.0))
            if wx < tx - 15.0:
                filtered_wps.append(dict(wp))
            else:
                jump_spec = wp.get("jump")
                if jump_spec and float(jump_spec.get("trigger_x", wx)) < tx:
                    wp_copy = dict(wp)
                    wp_copy["id"] = "wp_jump_to_target"
                    wp_copy["x"] = tx
                    if ty is not None:
                        wp_copy["y"] = ty
                    wp_copy["objective"] = "reach_target"
                    wp_copy["description"] = f"Jump to custom coordinate target ({tx}, {ty})"
                    filtered_wps.append(wp_copy)
                break

        if not filtered_wps or filtered_wps[-1].get("objective") != "reach_target":
            # If target requires climbing onto an elevated platform/stair (e.g. ty <= 680)
            # and previous waypoint was on ground or lower elevation, equip with a jump maneuver
            last_y = float(filtered_wps[-1].get("y", 800.0)) if filtered_wps else 800.0
            jump_info = None
            if ty is not None and ty < last_y - 80.0:
                jump_info = {
                    "trigger_x": tx - 140.0,
                    "direction": "move_right",
                    "min_frames": 34
                }
            filtered_wps.append({
                "id": "wp_reach_target",
                "x": tx,
                "y": ty if ty is not None else 800.0,
                "tolerance_x": tolerance_x,
                "jump": jump_info,
                "objective": "reach_target",
                "description": f"Reach custom coordinate target ({tx}, {ty})"
            })

        route["waypoints"] = filtered_wps
        self.current_waypoint_idx = 0
        print(f"[LevelRouteManager] Target coordinate set to ({tx}, {ty}). Route truncated to {len(filtered_wps)} waypoints.")

    def reset_current_level(self) -> None:
        self.current_waypoint_idx = 0
        print(f"[LevelRouteManager] Reset route for {self.current_level} to waypoint 0.")


class HybridBotController:
    """Reactive game controller using telemetry, behavior priorities, and level routes."""

    # Godot platformer kinematic constants
    PLAYER_SPEED_X = 700.0
    PLAYER_JUMP_VELOCITY = -1350.0
    GRAVITY = 3500.0

    def __init__(self, route_manager: LevelRouteManager, variation_mode: bool = False,
                 seed: int = 42, max_recovery_attempts: int = 5):
        self.route_manager = route_manager
        self.variation_mode = variation_mode
        self.seed = seed
        self.rng = random.Random(seed)
        self.max_recovery_attempts = max_recovery_attempts

        # Runtime tracking state
        self.current_behavior = BehaviorState.NAVIGATE
        self.recovery_attempts = 0
        self.stuck_counter = 0
        self.last_pos_x: Optional[float] = None
        self.last_pos_y: Optional[float] = None
        self.in_jump_maneuver: bool = False
        self.jump_frames_remaining: int = 0
        self.active_stomp_target: Optional[str] = None
        self.stomped_enemies: List[str] = []
        self.last_score: int = 0
        self.stomp_attempts: int = 0
        self.stomp_successes: int = 0
        self.wp_jump_executed: bool = False
        self.current_wp_id: Optional[str] = None
        self.current_jump_is_full: bool = True
        self.current_jump_direction: str = "move_right"
        self.last_deaths: int = 0
        self.retry_in_progress: bool = False
        self.retry_tick_counter: int = 0
        self.stuck_recovery_phase: int = 0

    def decide_action(self, state: Optional[Dict[str, Any]]) -> Tuple[List[str], int, BehaviorState, str]:
        """
        Evaluates current state against behavior priorities.
        Returns: (actions_list, frames, behavior_state, reason_description)
        """
        if not state:
            return (["move_right"], 20, BehaviorState.NAVIGATE, "No state available, advancing right")

        scene_name = state.get("scene", "Unknown")
        self.route_manager.update_scene(scene_name)

        # Check victory / game completion
        if "EndScreen" in scene_name or state.get("game_state") == "victory":
            return (["release_all"], 10, BehaviorState.OBJECTIVE, "Game Complete! At EndScreen")

        player = state.get("player") or {}
        lifecycle = player.get("lifecycle_state", "alive")
        game_state = state.get("game_state", "playing")
        player_alive = bool(player.get("alive", False)) and lifecycle not in ("dead",)
        on_floor = bool(player.get("on_floor", False))
        pos = player.get("position") or {}
        px = pos.get("x", 0.0) or 0.0
        py = pos.get("y", 0.0) or 0.0
        stats = state.get("stats") or {}
        score = stats.get("score", 0)
        deaths = stats.get("deaths", 0)

        # Track score updates for stomp/coin verification
        if score > self.last_score:
            diff = score - self.last_score
            self.last_score = score
            if self.active_stomp_target:
                self.stomp_successes += 1
                print(f"[COMBAT SUCCESS] Stomp verified! Score +{diff} (Target: {self.active_stomp_target})")
                self.stomped_enemies.append(self.active_stomp_target)
                self.active_stomp_target = None
        elif score < self.last_score:
            self.last_score = score

        # ----------------------------------------------------------------------
        # PRIORITY 1: RECOVERY
        # ----------------------------------------------------------------------
        # Player death detection: trigger retry if player is dead, unspawned after death, or paused with no active player
        is_dead = (not player_alive) or game_state == "player_died" or (game_state == "paused" and not player_alive) or deaths > self.last_deaths
        if is_dead and game_state != "scene_transitioning":
            self.recovery_attempts += 1
            self.route_manager.reset_current_level()
            self.in_jump_maneuver = False
            self.wp_jump_executed = False
            self.stuck_counter = 0
            self.last_score = 0
            if self.retry_tick_counter > 0:
                self.retry_tick_counter -= 1
                return (["wait"], 10, BehaviorState.RECOVERY, f"Waiting for level reload... (tick {self.retry_tick_counter})")
            else:
                self.retry_tick_counter = 3
                self.retry_in_progress = True
                return (["retry"], 40, BehaviorState.RECOVERY, f"Player death detected (recovery attempt {self.recovery_attempts})")

        # If level is initializing, transitioning, or player is genuinely spawning at start: WAIT
        if (game_state in ("scene_transitioning", "waiting_for_player") or lifecycle in ("spawning", "transitioning")) and not is_dead:
            return (["wait"], 6, BehaviorState.RECOVERY, f"Waiting for scene/player to be ready (state={game_state}, lifecycle={lifecycle})")

        # Player is alive: clear retry in progress
        self.retry_tick_counter = 0
        self.retry_in_progress = False
        self.last_deaths = deaths

        # Auto-resync: if player is at spawn position on floor but waypoint index has advanced
        if on_floor and px < 350.0 and self.route_manager.current_waypoint_idx >= 2:
            print(f"[RECOVERY] Player position ({round(px, 1)}) is at level start but route is at waypoint {self.route_manager.current_waypoint_idx}. Resynchronizing route.")
            self.route_manager.reset_current_level()
            self.in_jump_maneuver = False
            self.wp_jump_executed = False
            self.stuck_counter = 0

        # Stuck detection: only count when grounded
        if on_floor and self.last_pos_x is not None and abs(px - self.last_pos_x) < 4.0:
            self.stuck_counter += 1
        else:
            self.stuck_counter = 0
            self.stuck_recovery_phase = 0
        self.last_pos_x = px
        self.last_pos_y = py

        if self.stuck_counter >= 3:
            self.wp_jump_executed = False
            self.recovery_attempts += 1
            if self.recovery_attempts > self.max_recovery_attempts:
                print(f"[RECOVERY] Max recovery attempts ({self.max_recovery_attempts}) exceeded. Retrying level.")
                self.recovery_attempts = 0
                self.stuck_counter = 0
                self.stuck_recovery_phase = 0
                return (["retry"], 40, BehaviorState.RECOVERY, "Stuck against obstacle, issuing level restart")

            wp = self.route_manager.current_waypoint()
            wx = float(wp.get("x", px + 100.0)) if wp else px + 100.0
            dx_to_wp = wx - px

            # Phase 1: Step back away from the wall to create run-up distance
            if self.stuck_recovery_phase == 0:
                self.stuck_recovery_phase = 1
                if dx_to_wp >= 0:
                    return (["move_left"], 10, BehaviorState.RECOVERY,
                            f"Stuck against wall at X={round(px, 1)}: stepping back left to create run-up room")
                else:
                    return (["move_right"], 10, BehaviorState.RECOVERY,
                            f"Stuck against wall at X={round(px, 1)}: stepping back right to create run-up room")
            else:
                # Phase 2: Launch forward running jump with momentum
                self.stuck_recovery_phase = 0
                self.stuck_counter = 0
                self.in_jump_maneuver = True
                self.current_jump_is_full = True
                if dx_to_wp >= 0:
                    return (["move_right", "jump"], 34, BehaviorState.RECOVERY,
                            "Stuck against wall: launching forward running jump over obstacle")
                else:
                    return (["move_left", "jump"], 34, BehaviorState.RECOVERY,
                            "Stuck against wall: launching backward running jump over obstacle")

        # Pit trap detection: In Level01, if player fell to the ground past X=5920,
        # the cliff wall at X=7120 is 640px tall and unclimbable from the floor.
        if scene_name == "Level01" and px > 5920.0 and py >= 780.0 and on_floor:
            if self.route_manager.target_coord is not None:
                # Target coordinate navigation: do not abort with pit trap retry!
                # If target is elevated, step back left toward Stair 1 base to climb back up
                ty = self.route_manager.target_coord[1]
                if ty is not None and ty <= 600.0:
                    self.route_manager.current_waypoint_idx = self._find_waypoint_idx("wp_13_end_stair_1")
                    self.wp_jump_executed = False
                    self.in_jump_maneuver = False
                    if px > 5450.0:
                        return (["move_left"], 9, BehaviorState.RECOVERY,
                                f"Fell to floor (px={round(px, 1)}): moving left toward Stair 1 base to climb back up")
            else:
                self.recovery_attempts += 1
                print(f"[RECOVERY] Player fell from stairs to floor (px={round(px, 1)}, py={round(py, 1)}). Retrying level.", flush=True)
                self.route_manager.reset_current_level()
                self.in_jump_maneuver = False
                self.wp_jump_executed = False
                self.stuck_counter = 0
                return (["retry"], 40, BehaviorState.RECOVERY, "Fell from stairs to floor, issuing level restart")

        # ----------------------------------------------------------------------
        # PRIORITY 2: ENEMY STOMP & THREAT ENGAGEMENT
        # ----------------------------------------------------------------------
        enemies_info = state.get("enemies") or {}
        raw_enemies = enemies_info.get("all") or []
        if not raw_enemies and enemies_info.get("closest_enemy"):
            raw_enemies = [enemies_info.get("closest_enemy")]

        # Locate the closest threatening enemy in player's forward path
        threat_enemy = None
        min_ahead_dist = 9999.0

        for e in raw_enemies:
            ex = float(e.get("x", 0.0))
            ey = float(e.get("y", 0.0))
            erel_x = ex - px
            erel_y = ey - py
            edist = float(e.get("distance", (erel_x ** 2 + erel_y ** 2) ** 0.5))

            # Threat criteria: Ahead of player or directly under airborne player, on similar vertical stratum
            # erel_x: -40 to 550 px ahead; erel_y: -140 to 140 px
            if -40.0 <= erel_x <= 550.0 and -140.0 <= erel_y <= 140.0:
                if edist < min_ahead_dist:
                    min_ahead_dist = edist
                    threat_enemy = {
                        "name": e.get("name", "Enemy"),
                        "x": ex,
                        "y": ey,
                        "distance": edist,
                        "relative_x": erel_x,
                        "relative_y": erel_y,
                        "player_is_above": bool(e.get("player_is_above", False)) or (py < ey - 15.0),
                        "is_stompable": bool(e.get("is_stompable", False)) or (py < ey - 15.0)
                    }

        # Fallback to closest_enemy if no raw_enemies matched
        if not threat_enemy and enemies_info.get("closest_enemy"):
            ce = enemies_info["closest_enemy"]
            cerel_x = float(ce.get("relative_x", 0.0))
            cerel_y = float(ce.get("relative_y", 0.0))
            if -40.0 <= cerel_x <= 550.0 and -140.0 <= cerel_y <= 140.0:
                threat_enemy = {
                    "name": ce.get("name", "Enemy"),
                    "x": float(ce.get("x", 0.0)),
                    "y": float(ce.get("y", 0.0)),
                    "distance": float(ce.get("distance", 9999.0)),
                    "relative_x": cerel_x,
                    "relative_y": cerel_y,
                    "player_is_above": bool(ce.get("player_is_above", False)) or (py < float(ce.get("y", 0.0)) - 15.0),
                    "is_stompable": bool(ce.get("is_stompable", False)) or (py < float(ce.get("y", 0.0)) - 15.0)
                }

        if threat_enemy and player_alive:
            enemy_name = threat_enemy["name"]
            rel_x = threat_enemy["relative_x"]
            rel_y = threat_enemy["relative_y"]
            player_above = threat_enemy["player_is_above"]
            is_stompable = threat_enemy["is_stompable"]

            # Condition A: Airborne -> Air-steer directly onto enemy head
            if not on_floor:
                self.active_stomp_target = enemy_name
                if rel_x > 20.0:
                    return (["move_right"], 6, BehaviorState.COMBAT_STOMP, f"Air steering right onto {enemy_name} for stomp (rel_x={round(rel_x, 1)})")
                elif rel_x < -20.0:
                    return (["move_left"], 6, BehaviorState.COMBAT_STOMP, f"Air steering left onto {enemy_name} for stomp (rel_x={round(rel_x, 1)})")
                else:
                    return (["wait"], 4, BehaviorState.COMBAT_STOMP, f"Descending directly onto {enemy_name} stomp area (rel_x={round(rel_x, 1)})")

            # Condition B: On floor, enemy ahead in threat zone -> JUMP TO STOMP
            if on_floor:
                if 0.0 <= rel_x <= 480.0:
                    self.active_stomp_target = enemy_name
                    self.stomp_attempts += 1
                    self.in_jump_maneuver = True
                    jump_dur = 28
                    if self.variation_mode:
                        jump_dur += self.rng.randint(-2, 2)
                    return (["move_right", "jump"], jump_dur, BehaviorState.COMBAT_STOMP,
                            f"Initiating forward stomp jump onto approaching {enemy_name} (dx={round(rel_x, 1)}px)")

        # Ongoing jump execution (when not actively tracking a threat enemy)
        if self.in_jump_maneuver and not on_floor:
            # Check if player has already reached or passed horizontal position of current waypoint
            target_wp = self.route_manager.current_waypoint() or {}
            target_wx = float(target_wp.get("x", px + 100.0))
            vy = player.get("velocity", {}).get("y", 0.0)
            j_dir = getattr(self, "current_jump_direction", "move_right") or "move_right"

            # Check if player has reached or passed horizontal position of target platform
            reached_target_x = (px >= target_wx - 20.0) if j_dir == "move_right" else (px <= target_wx + 20.0)
            if reached_target_x:
                return (["wait"], 5, BehaviorState.NAVIGATE, f"Airborne over target platform {target_wp.get('id', '')} (px={round(px, 1)}), descending")
            elif vy < -150.0 and self.current_jump_is_full:
                return ([j_dir, "jump"], 9, BehaviorState.NAVIGATE, f"Airborne ascent toward platform (holding {j_dir}+jump)")
            else:
                return ([j_dir], 9, BehaviorState.NAVIGATE, f"Airborne glide toward waypoint platform ({j_dir})")
        else:
            self.in_jump_maneuver = False

        # ----------------------------------------------------------------------
        # PRIORITY 3 & 4: WAYPOINT NAVIGATION & OBJECTIVES
        # ----------------------------------------------------------------------
        self.route_manager.advance_to_current_x(px, py)
        wp = self.route_manager.current_waypoint()
        if not wp:
            # Reached end of waypoints for this scene; push right toward portal
            return (["move_right"], 20, BehaviorState.NAVIGATE, "All waypoints finished, pushing toward level exit")

        w_id = wp.get("id", "unknown")
        if w_id != self.current_wp_id:
            self.current_wp_id = w_id
            self.wp_jump_executed = False

        wx = float(wp.get("x", 0.0))
        wy = float(wp.get("y", 0.0))
        tol_x = float(wp.get("tolerance_x", 60.0))
        objective = wp.get("objective", "navigate")

        dx = wx - px
        dy = wy - py

        # Check Waypoint Completion
        # If player has already crossed this waypoint horizontally, advance immediately
        if px > wx + tol_x and objective not in ("reach_portal", "reach_target"):
            self.route_manager.advance_waypoint()
            self.wp_jump_executed = False
            self.current_wp_id = (self.route_manager.current_waypoint() or {}).get("id")
            return (["move_right"], 12, BehaviorState.NAVIGATE, f"Waypoint {w_id} already crossed (px={round(px, 1)} > {wx}), advancing")

        # Arrived at waypoint horizontal threshold or already passed it
        has_jump = wp.get("jump") is not None
        can_complete = True
        if has_jump and not self.wp_jump_executed:
            if objective == "reach_platform" and on_floor and (py <= wy + 80.0):
                can_complete = True
            else:
                can_complete = False

        if can_complete and (abs(dx) <= tol_x or (dx < 0 and abs(dx) > tol_x and objective not in ("reach_portal", "reach_target"))):
            # If objective is reach_target
            if objective == "reach_target":
                if on_floor and (wy is None or py <= wy + 80.0):
                    return (["wait"], 10, BehaviorState.OBJECTIVE, f"Target coordinate reached at ({wx}, {wy})")
                elif not on_floor:
                    return (["wait"], 6, BehaviorState.OBJECTIVE, f"Descending onto target coordinate ({wx}, {wy})")

            # If objective is reach_portal
            if objective == "reach_portal":
                # Step right into portal area
                return (["move_right"], 15, BehaviorState.OBJECTIVE, f"Entering portal at ({wx}, {wy})")

            # If objective is stomp_enemy and enemy is already eliminated
            if objective == "stomp_enemy":
                e_name = wp.get("enemy_name", "")
                if threat_enemy and threat_enemy.get("name") == e_name and threat_enemy.get("distance", 999) < 200:
                    # Still need to stomp
                    pass
                else:
                    self.route_manager.advance_waypoint()
                    self.wp_jump_executed = False
                    self.current_wp_id = (self.route_manager.current_waypoint() or {}).get("id")
                    next_wp = self.route_manager.current_waypoint()
                    if next_wp and next_wp.get("jump") and on_floor:
                        j_spec = next_wp.get("jump")
                        t_x = float(j_spec.get("trigger_x", float(next_wp.get("x", 0.0)) - 150.0))
                        if px >= t_x - 80.0:
                            self.in_jump_maneuver = True
                            self.wp_jump_executed = True
                            self.current_wp_id = next_wp.get("id")
                            min_f = int(j_spec.get("min_frames", 28))
                            self.current_jump_is_full = (min_f >= 24)
                            j_dir = j_spec.get("direction", "move_right")
                            self.current_jump_direction = j_dir
                            actions = [j_dir, "jump"] if j_dir else ["jump"]
                            return (actions, min_f, BehaviorState.NAVIGATE,
                                    f"Objective {w_id} complete -> immediately launching jump for {next_wp.get('id')}")
                    return (["move_right"], 9, BehaviorState.OBJECTIVE, f"Enemy objective {w_id} completed, advancing")

            # If objective is reach_platform: ensure on_floor at or above platform height (py <= wy + 80)
            if objective == "reach_platform":
                if on_floor and (py <= wy + 80.0):
                    self.route_manager.advance_waypoint()
                    self.wp_jump_executed = False
                    self.current_wp_id = (self.route_manager.current_waypoint() or {}).get("id")
                    next_wp = self.route_manager.current_waypoint()
                    if next_wp and next_wp.get("jump") and on_floor:
                        j_spec = next_wp.get("jump")
                        t_x = float(j_spec.get("trigger_x", float(next_wp.get("x", 0.0)) - 150.0))
                        if px >= t_x - 80.0:
                            self.in_jump_maneuver = True
                            self.wp_jump_executed = True
                            self.current_wp_id = next_wp.get("id")
                            min_f = int(j_spec.get("min_frames", 28))
                            self.current_jump_is_full = (min_f >= 24)
                            j_dir = j_spec.get("direction", "move_right")
                            self.current_jump_direction = j_dir
                            actions = [j_dir, "jump"] if j_dir else ["jump"]
                            return (actions, min_f, BehaviorState.NAVIGATE,
                                    f"Platform {w_id} reached -> immediately launching planned jump for {next_wp.get('id')}")
                        else:
                            step_frames = 5 if abs(t_x - px) < 100.0 else 9
                            return (["move_right"], step_frames, BehaviorState.NAVIGATE,
                                    f"Platform {w_id} reached, advancing toward next trigger at X={t_x}")
                    return (["move_right"], 9, BehaviorState.OBJECTIVE, f"Reached platform {w_id} (py={round(py, 1)}), advancing")
            else:
                self.route_manager.advance_waypoint()
                self.wp_jump_executed = False
                self.current_wp_id = (self.route_manager.current_waypoint() or {}).get("id")
                next_wp = self.route_manager.current_waypoint()
                if next_wp and next_wp.get("jump") and on_floor:
                    j_spec = next_wp.get("jump")
                    t_x = float(j_spec.get("trigger_x", float(next_wp.get("x", 0.0)) - 150.0))
                    if px >= t_x - 80.0:
                        self.in_jump_maneuver = True
                        self.wp_jump_executed = True
                        self.current_wp_id = next_wp.get("id")
                        min_f = int(j_spec.get("min_frames", 28))
                        self.current_jump_is_full = (min_f >= 24)
                        j_dir = j_spec.get("direction", "move_right")
                        self.current_jump_direction = j_dir
                        actions = [j_dir, "jump"] if j_dir else ["jump"]
                        return (actions, min_f, BehaviorState.NAVIGATE,
                                f"Waypoint {w_id} reached -> immediately launching planned jump for {next_wp.get('id')}")
                    else:
                        step_frames = 5 if abs(t_x - px) < 100.0 else 9
                        return (["move_right"], step_frames, BehaviorState.NAVIGATE,
                                f"Waypoint {w_id} reached, advancing toward next trigger at X={t_x}")
                return (["move_right"], 9, BehaviorState.NAVIGATE, f"Waypoint {w_id} reached, advancing")

        # Check if waypoint specifies a jump maneuver
        jump_spec = wp.get("jump")
        if jump_spec and on_floor and not self.wp_jump_executed:
            jump_dir = jump_spec.get("direction", "move_right")
            trigger_x = float(jump_spec.get("trigger_x", wx - 150.0))
            if self.variation_mode:
                trigger_x += self.rng.uniform(-25.0, 25.0)

            if jump_dir == "move_left":
                is_overshot = px < wx - 15.0
                can_trigger = px <= trigger_x + 80.0
            else:
                is_overshot = px > wx + 15.0
                can_trigger = px >= trigger_x - 80.0

            if not is_overshot and can_trigger:
                min_frames = int(jump_spec.get("min_frames", 28))
                if self.variation_mode:
                    min_frames += self.rng.randint(-3, 3)
                self.in_jump_maneuver = True
                self.current_jump_direction = jump_dir
                self.wp_jump_executed = True
                self.current_jump_is_full = (min_frames >= 24)
                actions = [jump_dir, "jump"] if jump_dir else ["jump"]
                return (actions, min_frames, BehaviorState.NAVIGATE,
                        f"Executing planned jump for {w_id} at X={round(px, 1)} (trigger={round(trigger_x, 1)})")

        # ----------------------------------------------------------------------
        # PRIORITY 5: OPTIONAL COLLECTIBLE DETOUR
        # ----------------------------------------------------------------------
        coins = state.get("coins") or {}
        nearest_coin = coins.get("nearest_coin")
        if nearest_coin and on_floor:
            c_dist = nearest_coin.get("distance", 9999.0)
            c_rel_x = nearest_coin.get("relative_x", 0.0)
            c_rel_y = nearest_coin.get("relative_y", 0.0)

            # If coin is close and safely ahead
            if c_dist < 140.0 and abs(c_rel_y) < 50.0:
                if c_rel_x > 15.0:
                    return (["move_right"], 12, BehaviorState.OBJECTIVE, "Collecting nearby coin")
                elif c_rel_x < -15.0 and self.variation_mode:
                    return (["move_left"], 10, BehaviorState.VARIATION, "Optional collectible detour: grabbing left coin")

        # Clean 9f / 5f pacing: 9 frames for normal travel, 5 frames for close or fine adjustment
        dist = abs(dx)
        if dist > 100.0:
            step_frames = 9
        else:
            step_frames = 5

        # Jump trigger approach pacing
        if jump_spec and on_floor:
            trigger_x = float(jump_spec.get("trigger_x", wx - 150.0))
            dist_to_trigger = abs(trigger_x - px)
            if dist_to_trigger < 100.0:
                step_frames = 5

        # Threat handling pacing
        if threat_enemy and threat_enemy.get("distance", 9999.0) < 650.0 and threat_enemy.get("relative_x", -1.0) > 0:
            step_frames = 5

        # Micro-alignment / direction decision
        if dx > 12.0:
            return (["move_right"], step_frames, BehaviorState.NAVIGATE,
                    f"Advancing right toward {w_id} (dx={round(dx, 1)}, {step_frames}f)")
        elif dx < -12.0:
            return (["move_left"], step_frames, BehaviorState.NAVIGATE,
                    f"Adjusting left/back toward {w_id} (dx={round(dx, 1)}, {step_frames}f)")
        else:
            # Horizontally aligned within ±12px
            return (["release_all"], 5, BehaviorState.NAVIGATE,
                    f"Centered on {w_id} (dx={round(dx, 1)}), settling")

    def _find_waypoint_idx(self, wp_id: str) -> int:
        route = self.route_manager.get_route(self.route_manager.current_level)
        if not route:
            return 0
        waypoints = route.get("waypoints", [])
        for i, wp in enumerate(waypoints):
            if wp.get("id") == wp_id:
                return i
        return 0


class HybridBotRunner:
    """Orchestrates running the HybridBotController against the live GameController."""

    def __init__(self, controller: Any, routes_file: Optional[str] = None,
                 variation_mode: bool = False, seed: int = 42, max_steps: int = 350,
                 tick_delay: float = 0.02, target_level: str = "Level01",
                 target_coord: Optional[Tuple[float, Optional[float]]] = None,
                 coord_tolerance: float = 60.0):
        self.controller = controller
        self.target_level = target_level
        self.target_coord = target_coord
        self.coord_tolerance = coord_tolerance
        self.route_manager = LevelRouteManager(routes_file)
        self.route_manager.current_level = target_level
        if target_coord is not None:
            self.route_manager.set_target_coordinate(target_coord[0], target_coord[1], tolerance_x=coord_tolerance)
        self.bot = HybridBotController(self.route_manager, variation_mode=variation_mode, seed=seed)
        self.max_steps = max_steps
        self.tick_delay = tick_delay
        self.completed_levels: List[str] = []
        self.victory: bool = False
        self.target_reached: bool = False

    def navigate_to(self, tx: float, ty: Optional[float] = None,
                    tolerance: Optional[float] = None,
                    max_steps: Optional[int] = None,
                    history_recorder: Optional[Any] = None,
                    pause_on_reach: bool = True) -> bool:
        """Navigates the hybrid bot to a specific target coordinate (tx, ty), avoiding enemies and obstacles."""
        if tolerance is not None:
            self.coord_tolerance = tolerance
        self.target_coord = (tx, ty)
        self.target_reached = False
        self.victory = False
        steps_limit = max_steps if max_steps is not None else self.max_steps

        self.route_manager.set_target_coordinate(tx, ty, tolerance_x=self.coord_tolerance)

        print("\n" + "=" * 80, flush=True)
        print(f"   >>> HYBRID BOT NAVIGATING TO TARGET: ({tx}, {ty})", flush=True)
        print(f"     Target Tolerance : ±{self.coord_tolerance}px", flush=True)
        print(f"     Max Steps Limit  : {steps_limit}", flush=True)
        print(f"     Pause On Reach   : {pause_on_reach}", flush=True)
        print("=" * 80, flush=True)

        # Ensure game is unpaused so player can move
        if hasattr(self.controller, "pause"):
            self.controller.pause(False)

        # Wait for valid state and ensure player is alive
        t0 = time.time()
        ready = False
        while time.time() - t0 < 6.0:
            st = self.controller.get_latest_state()
            if st and st.get("player") and st.get("scene"):
                p_data = st.get("player", {})
                if p_data.get("position") is not None:
                    if p_data.get("alive", False) and st.get("game_state") != "player_died":
                        ready = True
                        break
                    else:
                        print("[INFO] Player dead at start of navigation, issuing retry...", flush=True)
                        self.controller.release_all()
                        self.controller.retry()
                        time.sleep(1.0)
            time.sleep(0.1)

        # Sync waypoint route index with current player position
        st_init = self.controller.get_latest_state()
        p_init = (st_init.get("player") or {}) if st_init else {}
        pos_init = p_init.get("position") or {}
        px_init = float(pos_init.get("x", 200.0))
        py_init = float(pos_init.get("y", 760.0))
        self.route_manager.advance_to_current_x(px_init, py_init)

        for step_idx in range(1, steps_limit + 1):
            state_before = self.controller.get_latest_state()
            event_id_before = self.controller.get_latest_event_id() if hasattr(self.controller, "get_latest_event_id") else 0
            p_before = (state_before.get("player") or {}) if state_before else {}
            pos_before = p_before.get("position", {}) or {}
            bx = float(pos_before.get("x", 0.0))
            by = float(pos_before.get("y", 0.0))

            # Target coordinate check before action
            dx = abs(bx - tx)
            dy = abs(by - ty) if ty is not None else 0.0
            on_f = p_before.get("on_floor", False)
            y_reached = True if ty is None else (dy <= 80.0 or (on_f and by <= ty + 80.0))
            alive = p_before.get("alive", False) and state_before.get("game_state") != "player_died"
            if alive and dx <= self.coord_tolerance and y_reached:
                print("\n" + "*" * 80, flush=True)
                print(f"   [TARGET REACHED] Successfully arrived at target: ({bx}, {by})!", flush=True)
                print(f"     Target was        : X={tx}, Y={ty}", flush=True)
                print(f"     Stomp Successes   : {self.bot.stomp_successes}", flush=True)
                print(f"     Score             : {(state_before.get('stats') or {}).get('score', 0)}", flush=True)
                print("*" * 80, flush=True)
                self.victory = True
                self.target_reached = True
                self.controller.release_all()
                if pause_on_reach and hasattr(self.controller, "pause"):
                    self.controller.pause(True)
                break

            # Automatic retry on death before deciding action
            p_alive_before = (p_before.get("alive", False) if state_before else False) and (state_before.get("game_state") != "player_died")
            if state_before and not p_alive_before and state_before.get("game_state") != "scene_transitioning":
                print("\n[AUTO-RETRY] Player death detected! Issuing automatic retry to continue navigation...", flush=True)
                self.controller.release_all()
                self.controller.retry()
                t_respawn = time.time()
                while time.time() - t_respawn < 5.0:
                    time.sleep(0.1)
                    st_re = self.controller.get_latest_state()
                    if st_re and (st_re.get("player") or {}).get("alive", False) and st_re.get("game_state") not in ("player_died", "scene_transitioning"):
                        print(f"[AUTO-RETRY] Respawn successful. Resuming navigation toward ({tx}, {ty}) from start.", flush=True)
                        break
                self.route_manager.reset_current_level()
                self.bot.in_jump_maneuver = False
                self.bot.wp_jump_executed = False
                self.bot.stuck_counter = 0
                self.bot.retry_tick_counter = 0
                self.bot.retry_in_progress = False
                continue

            # Decide reactive action
            actions, frames, behavior, reason = self.bot.decide_action(state_before)
            dur_sec = round(frames / float(self.controller.fps), 4)

            wp = self.route_manager.current_waypoint()
            wp_str = wp.get("id") if wp else f"TARGET({tx})"
            print(f"[{step_idx:03d}/{steps_limit}] [{behavior.value.upper()}] WP: {wp_str} | Actions: {actions} ({dur_sec}s, {frames}f)", flush=True)
            print(f"       Reason: {reason}", flush=True)

            # Send actions to game
            if "retry" in actions:
                self.controller.retry()
                self.controller.wait_seconds(dur_sec)
                t_respawn = time.time()
                while time.time() - t_respawn < 5.0:
                    time.sleep(0.1)
                    st_re = self.controller.get_latest_state()
                    if st_re and (st_re.get("player") or {}).get("alive", False) and st_re.get("game_state") not in ("player_died", "scene_transitioning"):
                        break
                self.route_manager.reset_current_level()
                self.bot.in_jump_maneuver = False
                self.bot.wp_jump_executed = False
                self.bot.stuck_counter = 0
                self.bot.retry_tick_counter = 0
                self.bot.retry_in_progress = False
            elif "release_all" in actions or "wait" in actions:
                self.controller.release_all()
                self.controller.wait_seconds(dur_sec)
            else:
                self.controller.press_actions(actions)
                self.controller.wait_seconds(dur_sec)
                if "jump" in actions:
                    st_interim = self.controller.get_latest_state()
                    p_interim = (st_interim.get("player") or {}) if st_interim else {}
                    vy = p_interim.get("velocity", {}).get("y", 0.0)
                    ascending = vy < -100.0 and not p_interim.get("on_floor", False)
                    if not (self.bot.in_jump_maneuver and ascending):
                        if hasattr(self.controller, "release_actions"):
                            self.controller.release_actions(["jump"])
                        elif hasattr(self.controller, "send_command"):
                            self.controller.send_command({"release": ["jump"]})
                        elif hasattr(self.controller, "release_all"):
                            self.controller.release_all()

            if self.tick_delay > 0:
                time.sleep(self.tick_delay)

            state_after = self.controller.get_latest_state()
            events = self.controller.get_events_since(event_id_before) if hasattr(self.controller, "get_events_since") else []

            if history_recorder is not None:
                history_recorder.record_step(step_idx, actions, dur_sec, state_before, state_after,
                                             "success", events, checkpoint_result=f"{behavior.value}: {reason}")

            p_after = (state_after.get("player") or {}) if state_after else {}
            pos_after = p_after.get("position", {}) or {}
            stats_after = (state_after.get("stats") or {}) if state_after else {}
            ax = pos_after.get("x", 0.0)
            ay = pos_after.get("y", 0.0)
            print(f"       -> Pos: ({ax}, {ay}) | Grounded: {p_after.get('on_floor')} | Score: {stats_after.get('score')} | Deaths: {stats_after.get('deaths')}", flush=True)

            # Automatic retry on death after action execution
            p_alive_after = (p_after.get("alive", False) if state_after else False) and (state_after.get("game_state") != "player_died")
            if state_after and not p_alive_after and state_after.get("game_state") != "scene_transitioning":
                print("\n[AUTO-RETRY] Player died during action execution! Issuing automatic retry...", flush=True)
                self.controller.release_all()
                self.controller.retry()
                t_respawn = time.time()
                while time.time() - t_respawn < 5.0:
                    time.sleep(0.1)
                    st_re = self.controller.get_latest_state()
                    if st_re and (st_re.get("player") or {}).get("alive", False) and st_re.get("game_state") not in ("player_died", "scene_transitioning"):
                        print(f"[AUTO-RETRY] Respawn successful. Resuming navigation toward ({tx}, {ty}) from start.", flush=True)
                        break
                self.route_manager.reset_current_level()
                self.bot.in_jump_maneuver = False
                self.bot.wp_jump_executed = False
                self.bot.stuck_counter = 0
                self.bot.retry_tick_counter = 0
                self.bot.retry_in_progress = False
                continue

            # Target coordinate check after action
            dx = abs(ax - tx)
            dy = abs(ay - ty) if ty is not None else 0.0
            on_f = p_after.get("on_floor", False)
            y_reached = True if ty is None else (dy <= 80.0 or (on_f and ay <= ty + 80.0))
            alive = p_after.get("alive", False) and state_after.get("game_state") != "player_died"
            if alive and dx <= self.coord_tolerance and y_reached:
                print("\n" + "*" * 80, flush=True)
                print(f"   [TARGET REACHED] Successfully arrived at target: ({ax}, {ay})!", flush=True)
                print(f"     Target was        : X={tx}, Y={ty}", flush=True)
                print(f"     Stomp Successes   : {self.bot.stomp_successes}", flush=True)
                print(f"     Final Score       : {stats_after.get('score', 0)}", flush=True)
                print("*" * 80, flush=True)
                self.victory = True
                self.target_reached = True
                self.controller.release_all()
                if pause_on_reach and hasattr(self.controller, "pause"):
                    self.controller.pause(True)
                break

        if self.target_reached or self.victory:
            self.controller.release_all()
            if pause_on_reach and hasattr(self.controller, "pause"):
                self.controller.pause(True)

        return self.target_reached

    def run(self, history_recorder: Any) -> bool:
        if self.target_coord is not None:
            return self.navigate_to(
                tx=self.target_coord[0],
                ty=self.target_coord[1],
                tolerance=self.coord_tolerance,
                max_steps=self.max_steps,
                history_recorder=history_recorder,
                pause_on_reach=True
            )

        if self.bot.variation_mode:
            mode_label = "HYBRID BOT (VARIATION MODE)"
        else:
            mode_label = "HYBRID BOT (BASELINE MODE)"

        print("\n" + "=" * 80, flush=True)
        print(f"   >>> RUNNING {mode_label}", flush=True)
        print(f"     Seed              : {self.bot.seed}", flush=True)
        print(f"     Max Steps         : {self.max_steps}", flush=True)
        print(f"     Target Level      : {self.target_level}", flush=True)
        print("=" * 80, flush=True)

        # Wait for valid initial state from Godot
        print("[INFO] Waiting for Godot game state to initialize...", flush=True)
        t0 = time.time()
        ready = False
        while time.time() - t0 < 8.0:
            st = self.controller.get_latest_state()
            if st and st.get("player") and st.get("scene"):
                player_data = st.get("player", {})
                if player_data.get("position") is not None:
                    if player_data.get("alive", False) and st.get("game_state") != "player_died":
                        print(f"[INFO] Game state initialized. Scene: {st.get('scene')}, Player Pos: {player_data.get('position')}", flush=True)
                        ready = True
                        break
                    else:
                        print("[INFO] Player dead or unspawned at start, issuing retry...", flush=True)
                        self.controller.retry()
                        time.sleep(1.0)
            time.sleep(0.1)

        if not ready:
            print("[WARN] Timed out waiting for complete initial state, proceeding with fallback...", flush=True)

        for step_idx in range(1, self.max_steps + 1):
            state_before = self.controller.get_latest_state()
            event_id_before = self.controller.get_latest_event_id()
            p_before = (state_before.get("player") or {}) if state_before else {}
            pos_before = p_before.get("position", {}) or {}
            bx = float(pos_before.get("x", 0.0))
            by = float(pos_before.get("y", 0.0))

            # Check for victory / end screen
            cur_scene = state_before.get("scene", "") if state_before else ""
            if "EndScreen" in cur_scene or (state_before and state_before.get("game_state") == "victory"):
                print("\n" + "*" * 80, flush=True)
                print("   [VICTORY] HYBRID BOT SUCCESSFULLY COMPLETED BOTH LEVELS!", flush=True)
                print("*" * 80, flush=True)
                self.victory = True
                self.completed_levels = ["Level01", "Level02"]
                self.controller.release_all()
                if hasattr(self.controller, "pause"):
                    self.controller.pause(True)
                break

            # If targeting a specific coordinate instead of the end portal:
            if self.target_coord is not None:
                tx, ty = self.target_coord
                dx = abs(bx - tx)
                dy = abs(by - ty) if ty is not None else 0.0
                on_f = p_before.get("on_floor", False)
                y_reached = True if ty is None else (dy <= 80.0 or (on_f and by <= ty + 80.0))
                alive = p_before.get("alive", False)
                if alive and dx <= self.coord_tolerance and y_reached:
                    print("\n" + "*" * 80, flush=True)
                    print(f"   [VICTORY] TARGET COORDINATE REACHED: ({bx}, {by})!", flush=True)
                    print(f"     Target was        : X={tx}, Y={ty}", flush=True)
                    print(f"     Stomp Successes   : {self.bot.stomp_successes}", flush=True)
                    print(f"     Final Score       : {(state_before.get('stats') or {}).get('score', 0)}", flush=True)
                    print("*" * 80, flush=True)
                    self.victory = True
                    self.target_reached = True
                    self.controller.release_all()
                    if hasattr(self.controller, "pause"):
                        self.controller.pause(True)
                    break

            # If target is Level01 and scene moved to Level02 or portal reached:
            if self.target_level == "Level01" and ("Level02" in cur_scene or bx >= 7300.0 or (state_before and state_before.get("game_state") == "scene_transitioning" and bx > 7000.0)):
                print("\n" + "*" * 80, flush=True)
                print("   [VICTORY] LEVEL 01 SUCCESSFULLY CLEARED!", flush=True)
                print(f"     Portal Entered at X={bx}, Y={by}", flush=True)
                print(f"     Stomp Successes   : {self.bot.stomp_successes}", flush=True)
                print(f"     Final Score       : {(state_before.get('stats') or {}).get('score', 0)}", flush=True)
                print("*" * 80, flush=True)
                self.victory = True
                self.completed_levels = ["Level01"]
                self.controller.release_all()
                if hasattr(self.controller, "pause"):
                    self.controller.pause(True)
                break

            # Automatic retry on death before deciding action
            p_alive_before = (p_before.get("alive", False) if state_before else False) and (state_before.get("game_state") != "player_died")
            if state_before and not p_alive_before and state_before.get("game_state") != "scene_transitioning":
                print("\n[AUTO-RETRY] Player death detected! Issuing automatic retry to continue navigation...", flush=True)
                self.controller.release_all()
                self.controller.retry()
                t_respawn = time.time()
                while time.time() - t_respawn < 5.0:
                    time.sleep(0.1)
                    st_re = self.controller.get_latest_state()
                    if st_re and (st_re.get("player") or {}).get("alive", False) and st_re.get("game_state") not in ("player_died", "scene_transitioning"):
                        print(f"[AUTO-RETRY] Respawn successful. Resuming navigation from start.", flush=True)
                        break
                self.route_manager.reset_current_level()
                self.bot.in_jump_maneuver = False
                self.bot.wp_jump_executed = False
                self.bot.stuck_counter = 0
                self.bot.retry_tick_counter = 0
                self.bot.retry_in_progress = False
                continue

            # Track level completion transitions
            if "Level02" in cur_scene and "Level01" not in self.completed_levels:
                self.completed_levels.append("Level01")
                print("\n[MILESTONE] Level 01 Completed! Now in Level 02.\n", flush=True)

            # Decide reactive action
            actions, frames, behavior, reason = self.bot.decide_action(state_before)
            dur_sec = round(frames / float(self.controller.fps), 4)

            # Waypoint display info
            wp = self.route_manager.current_waypoint()
            wp_str = wp.get("id") if wp else "END"

            print(f"[{step_idx:03d}/{self.max_steps}] [{behavior.value.upper()}] WP: {wp_str} | Actions: {actions} ({dur_sec}s, {frames}f)", flush=True)
            print(f"       Reason: {reason}", flush=True)

            # Send actions to game
            if "retry" in actions:
                self.controller.retry()
                self.controller.wait_seconds(dur_sec)
                t_respawn = time.time()
                while time.time() - t_respawn < 5.0:
                    time.sleep(0.1)
                    st_re = self.controller.get_latest_state()
                    if st_re and (st_re.get("player") or {}).get("alive", False) and st_re.get("game_state") not in ("player_died", "scene_transitioning"):
                        break
                self.route_manager.reset_current_level()
                self.bot.in_jump_maneuver = False
                self.bot.wp_jump_executed = False
                self.bot.stuck_counter = 0
                self.bot.retry_tick_counter = 0
                self.bot.retry_in_progress = False
            elif "release_all" in actions or "wait" in actions:
                self.controller.release_all()
                self.controller.wait_seconds(dur_sec)
            else:
                self.controller.press_actions(actions)
                self.controller.wait_seconds(dur_sec)
                # Ensure jump action is released at step boundary so subsequent jumps can trigger,
                # but preserve jump if still actively ascending in an ongoing jump maneuver
                if "jump" in actions:
                    st_interim = self.controller.get_latest_state()
                    p_interim = (st_interim.get("player") or {}) if st_interim else {}
                    vy = p_interim.get("velocity", {}).get("y", 0.0)
                    ascending = vy < -100.0 and not p_interim.get("on_floor", False)
                    if not (self.bot.in_jump_maneuver and ascending):
                        if hasattr(self.controller, "release_actions"):
                            self.controller.release_actions(["jump"])
                        elif hasattr(self.controller, "send_command"):
                            self.controller.send_command({"release": ["jump"]})
                        elif hasattr(self.controller, "release_all"):
                            self.controller.release_all()

            if self.tick_delay > 0:
                time.sleep(self.tick_delay)

            state_after = self.controller.get_latest_state()
            events = self.controller.get_events_since(event_id_before)

            # Record step history for full reproducibility
            history_recorder.record_step(step_idx, actions, dur_sec, state_before, state_after,
                                         "success", events, checkpoint_result=f"{behavior.value}: {reason}")

            # Telemetry readout
            p_after = (state_after.get("player") or {}) if state_after else {}
            pos_after = p_after.get("position", {}) or {}
            stats_after = (state_after.get("stats") or {}) if state_after else {}
            ax = pos_after.get("x", 0.0)
            ay = pos_after.get("y", 0.0)
            print(f"       -> Pos: ({ax}, {ay}) | Grounded: {p_after.get('on_floor')} | Score: {stats_after.get('score')} | Deaths: {stats_after.get('deaths')}", flush=True)

            # Automatic retry on death after action execution
            p_alive_after = (p_after.get("alive", False) if state_after else False) and (state_after.get("game_state") != "player_died")
            if state_after and not p_alive_after and state_after.get("game_state") != "scene_transitioning":
                print("\n[AUTO-RETRY] Player died during action execution! Issuing automatic retry...", flush=True)
                self.controller.release_all()
                self.controller.retry()
                t_respawn = time.time()
                while time.time() - t_respawn < 5.0:
                    time.sleep(0.1)
                    st_re = self.controller.get_latest_state()
                    if st_re and (st_re.get("player") or {}).get("alive", False) and st_re.get("game_state") not in ("player_died", "scene_transitioning"):
                        print(f"[AUTO-RETRY] Respawn successful. Resuming navigation from start.", flush=True)
                        break
                self.route_manager.reset_current_level()
                self.bot.in_jump_maneuver = False
                self.bot.wp_jump_executed = False
                self.bot.stuck_counter = 0
                self.bot.retry_tick_counter = 0
                self.bot.retry_in_progress = False
                continue

            # Target coordinate check after action
            if self.target_coord is not None:
                tx, ty = self.target_coord
                dx = abs(ax - tx)
                dy = abs(ay - ty) if ty is not None else 0.0
                on_f = p_after.get("on_floor", False)
                y_reached = True if ty is None else (dy <= 80.0 or (on_f and ay <= ty + 80.0))
                alive = p_after.get("alive", False)
                if alive and dx <= self.coord_tolerance and y_reached:
                    print("\n" + "*" * 80, flush=True)
                    print(f"   [VICTORY] TARGET COORDINATE REACHED: ({ax}, {ay})!", flush=True)
                    print(f"     Target was        : X={tx}, Y={ty}", flush=True)
                    print(f"     Stomp Successes   : {self.bot.stomp_successes}", flush=True)
                    print(f"     Final Score       : {stats_after.get('score', 0)}", flush=True)
                    print("*" * 80, flush=True)
                    self.victory = True
                    self.target_reached = True
                    self.controller.release_all()
                    if hasattr(self.controller, "pause"):
                        self.controller.pause(True)
                    break

            # Level 01 portal completion check after action
            if self.target_level == "Level01" and (ax >= 7300.0 or (state_after and state_after.get("game_state") == "scene_transitioning" and ax > 7000.0)):
                print("\n" + "*" * 80, flush=True)
                print("   [VICTORY] LEVEL 01 SUCCESSFULLY CLEARED!", flush=True)
                print(f"     Portal Entered at X={ax}, Y={ay}", flush=True)
                print(f"     Stomp Successes   : {self.bot.stomp_successes}", flush=True)
                print(f"     Final Score       : {stats_after.get('score', 0)}", flush=True)
                print("*" * 80, flush=True)
                self.victory = True
                self.completed_levels = ["Level01"]
                self.controller.release_all()
                if hasattr(self.controller, "pause"):
                    self.controller.pause(True)
                break

        # Ensure all actions released and game paused when target or victory reached
        if self.target_reached or self.victory:
            self.controller.release_all()
            if hasattr(self.controller, "pause"):
                self.controller.pause(True)

        print("\n" + "=" * 80, flush=True)
        if self.target_reached:
            status_msg = f"SUCCESS (TARGET REACHED AT {self.target_coord})"
        elif self.victory:
            status_msg = f"SUCCESS ({self.target_level} CLEARED)"
        else:
            status_msg = f"FINISHED ({len(self.completed_levels)} levels cleared)"
        print(f"   [DONE] HYBRID BOT RUN FINISHED: {status_msg}", flush=True)
        print(f"     Stomp Attempts   : {self.bot.stomp_attempts}", flush=True)
        print(f"     Stomp Successes  : {self.bot.stomp_successes}", flush=True)
        print(f"     Recovery Count   : {self.bot.recovery_attempts}", flush=True)
        print("=" * 80, flush=True)
        return self.victory
