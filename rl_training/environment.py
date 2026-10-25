"""
environment.py — Lightweight Godot 2D Platformer RL Simulation Environment

Abstracts the physics, kinematics, and entities of the Godot platformer levels
(such as Level01 and Map1_GreenHills) to enable offline reinforcement learning.

Attributes & Mechanics Mirrored from Godot Game:
  - Player Kinematics: x, y, velocity_x, velocity_y, is_on_floor, is_on_wall
  - Gravity: 1000.0 px/s^2, Terminal Fall: 1500.0 px/s, Jump Impulse: -950.0 px/s
  - Out of Bounds: Y > 1400.0 triggers death (matches OUT_OF_BOUNDS_Y in Player.gd)
  - Patrolling Enemies: Horizontal pacing with stomp vulnerability from above
  - Collectibles & Goal: Coin collection bonuses and waypoint/portal completion
"""

import math
import random
from typing import Dict, Any, Tuple, List, Optional


# Discrete Action Space
ACTION_IDLE = 0
ACTION_MOVE_LEFT = 1
ACTION_MOVE_RIGHT = 2
ACTION_JUMP = 3
ACTION_JUMP_RIGHT = 4
ACTION_JUMP_LEFT = 5

ACTION_NAMES = {
    ACTION_IDLE: "wait",
    ACTION_MOVE_LEFT: "move_left",
    ACTION_MOVE_RIGHT: "move_right",
    ACTION_JUMP: "jump",
    ACTION_JUMP_RIGHT: "jump_right",
    ACTION_JUMP_LEFT: "jump_left",
}
NUM_ACTIONS = len(ACTION_NAMES)


class Platform:
    """Represents a solid horizontal terrain segment in Godot."""
    def __init__(self, x_start: float, x_end: float, y: float):
        self.x_start = x_start
        self.x_end = x_end
        self.y = y


class Enemy:
    """Simulates a patrolling platformer enemy with stomp mechanics."""
    def __init__(self, x: float, y: float, patrol_min: float, patrol_max: float, speed: float = 120.0):
        self.x = x
        self.y = y
        self.patrol_min = patrol_min
        self.patrol_max = patrol_max
        self.speed = speed
        self.direction = 1  # 1 = right, -1 = left
        self.alive = True
        self.width = 40.0
        self.height = 40.0

    def update(self, dt: float):
        if not self.alive:
            return
        self.x += self.direction * self.speed * dt
        if self.x >= self.patrol_max:
            self.x = self.patrol_max
            self.direction = -1
        elif self.x <= self.patrol_min:
            self.x = self.patrol_min
            self.direction = 1


class GodotPlatformerEnv:
    """
    Simulation environment modeling the Godot 2D Platformer gameplay mechanics.
    Exposes a standard step(action) -> (next_state, reward, done, info) interface.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        cfg = config or {}
        rewards_cfg = cfg.get("rewards", {})
        physics_cfg = cfg.get("physics", {})

        # Rewards
        self.reward_goal = rewards_cfg.get("goal_reached", 100.0)
        self.reward_progress = rewards_cfg.get("progress_scale", 0.15)
        self.reward_stomp = rewards_cfg.get("enemy_stomped", 50.0)
        self.reward_coin = rewards_cfg.get("coin_collected", 20.0)
        self.penalty_death = rewards_cfg.get("death_penalty", -100.0)
        self.cost_step = rewards_cfg.get("step_cost", -1.0)

        # Physics Constants (Matching Godot Player.gd)
        self.gravity = physics_cfg.get("gravity", 1000.0)
        self.move_speed = physics_cfg.get("max_horizontal_speed", 600.0)
        self.jump_velocity = physics_cfg.get("jump_velocity", -950.0)
        self.dt = physics_cfg.get("delta_time", 0.05)
        self.out_of_bounds_y = physics_cfg.get("out_of_bounds_y", 1400.0)
        self.max_steps = cfg.get("max_steps_per_episode", 200)

        # World Geometry: Platforms with a hazard gap
        self.platforms = [
            Platform(0.0, 420.0, 500.0),       # Initial platform
            Platform(520.0, 950.0, 500.0),     # Second platform across a 100px gap
            Platform(980.0, 1300.0, 420.0),    # Elevated platform leading to goal
        ]

        # Target Waypoint / Level Portal
        self.goal_x = 1150.0
        self.goal_y = 420.0

        # State Variables
        self.player_x = 50.0
        self.player_y = 500.0
        self.player_vel_x = 0.0
        self.player_vel_y = 0.0
        self.on_floor = True
        self.on_wall = False
        self.alive = True
        self.step_count = 0
        self.score = 0
        self.enemies: List[Enemy] = []
        self.coins: List[Tuple[float, float, bool]] = []  # (x, y, collected)

        self.reset()

    def reset(self) -> str:
        """Resets the environment to the initial state of the level."""
        self.player_x = 50.0
        self.player_y = 500.0
        self.player_vel_x = 0.0
        self.player_vel_y = 0.0
        self.on_floor = True
        self.on_wall = False
        self.alive = True
        self.step_count = 0
        self.score = 0

        # Spawn enemies on platforms
        self.enemies = [
            Enemy(x=280.0, y=500.0, patrol_min=200.0, patrol_max=380.0, speed=100.0),
            Enemy(x=700.0, y=500.0, patrol_min=580.0, patrol_max=850.0, speed=120.0),
        ]

        # Spawn collectible coins
        self.coins = [
            [250.0, 440.0, False],
            [470.0, 380.0, False],  # Above the gap (reward for daring jump)
            [800.0, 440.0, False],
        ]

        return self.get_discrete_state()

    def step(self, action: int) -> Tuple[str, float, bool, Dict[str, Any]]:
        """
        Executes one action step and returns (discrete_state, reward, done, info).
        """
        self.step_count += 1
        reward = self.cost_step
        done = False
        info = {
            "event": "step",
            "enemy_stomped": False,
            "coin_picked": False,
            "goal_reached": False,
            "player_died": False,
        }

        prev_dist_to_goal = math.hypot(self.goal_x - self.player_x, self.goal_y - self.player_y)

        # 1. Apply Action Inputs to Horizontal & Vertical Velocities
        if action == ACTION_MOVE_LEFT:
            self.player_vel_x = -self.move_speed
        elif action == ACTION_MOVE_RIGHT:
            self.player_vel_x = self.move_speed
        elif action == ACTION_JUMP:
            if self.on_floor:
                self.player_vel_y = self.jump_velocity
                self.on_floor = False
        elif action == ACTION_JUMP_RIGHT:
            self.player_vel_x = self.move_speed
            if self.on_floor:
                self.player_vel_y = self.jump_velocity
                self.on_floor = False
        elif action == ACTION_JUMP_LEFT:
            self.player_vel_x = -self.move_speed
            if self.on_floor:
                self.player_vel_y = self.jump_velocity
                self.on_floor = False
        elif action == ACTION_IDLE:
            self.player_vel_x *= 0.5  # Ground friction

        # 2. Physics Integration
        self.player_vel_y += self.gravity * self.dt
        if self.player_vel_y > 1500.0:
            self.player_vel_y = 1500.0

        self.player_x += self.player_vel_x * self.dt
        self.player_y += self.player_vel_y * self.dt

        # Bounds clamp on the left boundary
        if self.player_x < 10.0:
            self.player_x = 10.0
            self.player_vel_x = 0.0

        # 3. Collision Resolution with Platforms
        was_on_floor = self.on_floor
        self.on_floor = False
        for p in self.platforms:
            if p.x_start <= self.player_x <= p.x_end:
                # Land on platform from above
                if self.player_vel_y >= 0 and abs(self.player_y - p.y) <= 22.0:
                    self.player_y = p.y
                    self.player_vel_y = 0.0
                    self.on_floor = True
                    break

        # 4. Update Enemies & Resolve Combat Interactions
        for enemy in self.enemies:
            if not enemy.alive:
                continue
            enemy.update(self.dt)

            dist_x = abs(self.player_x - enemy.x)
            dist_y = self.player_y - enemy.y

            # Check Stomp Interaction: Player falling onto enemy from above
            if dist_x <= 35.0 and -45.0 <= dist_y <= 5.0 and self.player_vel_y > 50.0:
                enemy.alive = False
                self.player_vel_y = -600.0  # Bounce impulse
                reward += self.reward_stomp
                info["enemy_stomped"] = True
                info["event"] = "enemy_stomped"
            # Body Collision: Player touched enemy without downward stomp
            elif dist_x <= 25.0 and abs(dist_y) <= 20.0:
                self.alive = False
                done = True
                reward += self.penalty_death
                info["player_died"] = True
                info["event"] = "player_died_by_enemy"
                return self.get_discrete_state(), reward, done, info

        # 5. Check Coin Pickups
        for coin in self.coins:
            if not coin[2]:  # not yet collected
                if math.hypot(self.player_x - coin[0], self.player_y - coin[1]) <= 30.0:
                    coin[2] = True
                    self.score += 10
                    reward += self.reward_coin
                    info["coin_picked"] = True

        # 6. Check Out-of-Bounds / Pit Death (Contract Invariant)
        if self.player_y >= self.out_of_bounds_y:
            self.alive = False
            done = True
            reward += self.penalty_death
            info["player_died"] = True
            info["event"] = "player_died_out_of_bounds"
            return self.get_discrete_state(), reward, done, info

        # 7. Check Goal / Waypoint Completion
        dist_to_goal = math.hypot(self.goal_x - self.player_x, self.goal_y - self.player_y)
        if dist_to_goal <= 40.0:
            done = True
            reward += self.reward_goal
            info["goal_reached"] = True
            info["event"] = "goal_reached"
            return self.get_discrete_state(), reward, done, info

        # 8. Distance Shaping Reward (encourages forward progression toward target)
        dist_improvement = prev_dist_to_goal - dist_to_goal
        reward += dist_improvement * self.reward_progress

        # 9. Max Steps Exceeded
        if self.step_count >= self.max_steps:
            done = True
            info["event"] = "time_limit_reached"

        return self.get_discrete_state(), reward, done, info

    def get_discrete_state(self) -> str:
        """
        Discretizes the continuous Godot platformer state into a compact tuple string:
        (rel_x_bin, rel_y_bin, on_floor, enemy_hazard, gap_ahead)
        """
        # 1. Relative X to Goal
        dx = self.goal_x - self.player_x
        if dx < -150.0:
            x_bin = "far_past"
        elif dx < -40.0:
            x_bin = "past"
        elif dx <= 40.0:
            x_bin = "at_target"
        elif dx <= 250.0:
            x_bin = "near"
        else:
            x_bin = "far_ahead"

        # 2. Relative Y to Goal
        dy = self.goal_y - self.player_y
        if dy < -40.0:
            y_bin = "above"
        elif dy <= 40.0:
            y_bin = "level"
        else:
            y_bin = "below"

        # 3. Floor status
        floor_bin = "floor" if self.on_floor else "air"

        # 4. Enemy Hazard Sensing
        enemy_hazard = "safe"
        for enemy in self.enemies:
            if not enemy.alive:
                continue
            edx = enemy.x - self.player_x
            edy = enemy.y - self.player_y
            if abs(edx) < 140.0 and abs(edy) < 60.0:
                if edy > 10.0 and self.player_vel_y > 0:
                    enemy_hazard = "stompable"
                elif edx > 0:
                    enemy_hazard = "enemy_ahead"
                else:
                    enemy_hazard = "enemy_behind"
                break

        # 5. Gap / Pit Hazard Sensing ahead
        gap_ahead = "no_gap"
        forward_x = self.player_x + 60.0
        has_platform = False
        for p in self.platforms:
            if p.x_start <= forward_x <= p.x_end:
                has_platform = True
                break
        if not has_platform and self.on_floor:
            gap_ahead = "gap_near"

        return f"{x_bin}|{y_bin}|{floor_bin}|{enemy_hazard}|{gap_ahead}"

    def get_raw_telemetry(self) -> Dict[str, Any]:
        """Returns telemetry in a format directly matching Godot latest_state.json."""
        return {
            "player": {
                "x": round(self.player_x, 1),
                "y": round(self.player_y, 1),
                "vel_x": round(self.player_vel_x, 1),
                "vel_y": round(self.player_vel_y, 1),
                "on_floor": 1 if self.on_floor else 0,
                "alive": 1 if self.alive else 0,
            },
            "goal": {
                "x": self.goal_x,
                "y": self.goal_y,
                "distance": round(math.hypot(self.goal_x - self.player_x, self.goal_y - self.player_y), 1),
            },
            "enemies": [
                {"x": round(e.x, 1), "y": round(e.y, 1), "alive": 1 if e.alive else 0}
                for e in self.enemies
            ],
            "step": self.step_count,
            "score": self.score,
        }
