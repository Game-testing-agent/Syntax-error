# GDScript Component Contracts and Invariant Oracle

## 1. Actor (`Actors/Actor.gd`)
- **Inherits**: `CharacterBody2D`
- **Exports**: `speed = Vector2(400.0, 500.0)`, `gravity = 3500.0`
- **Functions**: `_physics_process(delta)`
- **Contracts**:
  - Imparts constant downward gravitational acceleration (`velocity.y += gravity * delta`).
- **Fragile Spots**: None directly; base class for Player and Enemy.

## 2. Player (`Actors/Player.gd`)
- **Inherits**: `Actor`
- **Groups**: `player`
- **Collision**: Mask 14 (layers 2, 3, 4: world/enemies/bumpers). StompDetector mask 18. EnemyDetector mask 2.
- **Exports**:
  - `stomp_impulse: float = 600.0` (in `Player.tscn` overridden to `1600.0`)
  - `is_invincible: bool = false` (Godmode toggle)
  - `bug_wall_friction_jump: bool = true` (Dampens upward velocity by 35% when scraping wall during ascent)
- **Constants**: `OUT_OF_BOUNDS_Y = 1400.0`, `FALL_DISTANCE_THRESHOLD = 400.0`
- **Functions & Contracts**:
  - `_ready()`: Registers with `GameLogger`, adds to `"player"` group, emits `player_spawned`.
  - `_exit_tree()`: Logs `player_removed`; flags anomaly `unexpected_player_removal` if unprompted by death or scene transition.
  - `_on_StompDetector_area_entered(area)`: Stomps enemy, calls `calculate_stomp_velocity()` imparting bounce impulse, emits `enemy_stomped`.
  - `_on_EnemyDetector_body_entered(body)`: Kills player on body contact unless invincible, calls `die()`.
  - `die(force)`: Increments `PlayerData.deaths`, logs `player_died`, calls `queue_free()`.
- **Fragile Spots**:
  - Line 78: Exemption `if body.name == "Enemy4" or body.get_index() == 3 ... return` bypasses player death on contact with 4th enemy.
  - Line 227: `_velocity.y *= 0.65` wall-friction jump damping stunts upward leap when wall scraping.
  - Out of bounds at $Y > 1400.0$ logs anomaly but requires external pit trigger to force respawn/death.

## 3. Enemy (`Actors/Enemy.gd`)
- **Inherits**: `Actor`
- **Groups**: `enemies`
- **Collision**: StompArea2D on layer 16, monitors attacker areas.
- **Exports**:
  - `score: int = 100`
  - `can_kill_player: bool = true`
  - `bug_stomp_tunneling: bool = true` (Shifts threshold by -14px if attacker velocity.y > 500px/s)
- **Functions & Contracts**:
  - `_ready()`: Initializes `velocity.x = -speed.x`, joins `"enemies"` group, logs `enemy_spawned`.
  - `_physics_process(delta)`: Reverses horizontal direction upon hitting wall (`if is_on_wall(): velocity.x *= -1.0`).
  - `_on_StompArea2D_area_entered(area)`: If attacker area $Y \le$ stomp threshold, executes `die()`.
  - `die()`: Sets `is_dead = true`, awards `PlayerData.score += score`, logs `enemy_killed`, queues free.
- **Fragile Spots**:
  - Line 31-33: `velocity.x *= -1.0` if `velocity.x == 0.0` results in `0.0 * -1.0 = 0.0`, permanently freezing the enemy in place (zero-velocity deadlock).
  - Line 31-33: Tight patrol bounding walls can cause rapid ping-pong oscillation without forward exploration progress.
  - Lines 57-63: Fast downward stomps shift threshold, permitting stomping bounce without triggering `die()`.

## 4. PlayerData Autoload (`Autoload/PlayerData.gd`)
- **Signals**: `updated`, `died`, `reset`
- **Properties**:
  - `score: int` (custom setter `set_score`)
  - `deaths: int` (custom setter `set_deaths`)
  - `bug_milestone_score_tax: bool = true`
- **Contracts**:
  - Monotonicity Invariant: `score` must only increase during gameplay or reset to 0 upon death/restart (`reset_data()`).
  - `deaths` increments strictly on player demise.
- **Fragile Spots**:
  - Lines 40-41: Milestone tax logic `if bug_milestone_score_tax and not is_resetting and old_score >= 500 and new_score > old_score: final_score = old_score - 10`. Spontaneously deducts 10 points on collectible pickups once score reaches $\ge 500$, violating score monotonicity.

## 5. Coin Collectible (`Objects/Coin.gd`)
- **Groups**: `coins`
- **Collision**: Area2D detecting Player body entered.
- **Exports**: `score: int = 100`, `bug_deferred_pickup_race: bool = true`
- **Contracts**:
  - Idempotency Invariant: Coin can only be collected once; increments score by 100 via `PlayerData.score += score`, plays picked animation, removes from group.
- **Fragile Spots**:
  - Line 41: `await get_tree().physics_frame` when sprinting $> 300\text{ px/s}$ allows a concurrent body_entered query on the same frame to trigger duplicate pickup anomalies.

## 6. Portal2D (`Objects/Portal2D.gd`)
- **Groups**: `portals`
- **Collision**: Area2D detecting Player body entered (`collision_layer = 0`, mask 1).
- **Exports**: `next_scene: PackedScene`, `bug_airborne_portal_unpause: bool = true`
- **Contracts**:
  - Lifecycle Progression Invariant: Touching portal triggers `_on_body_entered()`, emits `portal_entered`, pauses scene tree, plays fade animation, and transitions scene via `change_scene_to_packed()`. Reaching the final level portal completes level.
  - Registration Invariant: In `_ready()`, `if not Engine.is_editor_hint(): add_to_group("portals")`.
- **Fragile Spots**:
  - Line 11: `if not Engine.is_editor_hint(): add_to_group("portals")` fails if tool script lifecycle or missing registration fails to register in group, leaving `goal.found: false` across all telemetry snapshots.
  - Softlock: If player reaches level terminus and portal transition fails to fire, player is stranded indefinitely.
  - Line 68: Airborne portal unpause allows falling into void during transition fade.

## 7. GameLogger (`Autoload/GameLogger.gd`)
- **Role**: Emits structured JSONL telemetry for state snapshots and discrete events.
- **Contracts**:
  - Evaluates snapshot fields: `player`, `enemies`, `coins`, `goal`, `inputs`, `stats`.
  - Flags anomalies: `unexpected_score_change`, `player_out_of_bounds`, `duplicate_pickup_attempt`, `runtime_error_observed`.
