# Source Code Contracts & Fragile Spots (Phase B2)

## 1. Actor.gd (`game_src/Actors/Actor.gd`)
- **Class / Inheritance**: `extends CharacterBody2D`, `class_name Actor` (`Actor.gd:L1-L2`).
- **Exports & Constants**:
  - `@export var speed: Vector2 = Vector2(400.0, 500.0)` (`Actor.gd:L5`).
  - `@export var gravity: float = 3500.0` (`Actor.gd:L6`).
- **Functions**:
  - `_physics_process(delta)`: Applies gravity `velocity.y += gravity * delta` (`Actor.gd:L9-L10`).
- **Couplings**: Base class for `Player.gd` and `Enemy.gd`.

## 2. Enemy.gd (`game_src/Actors/Enemy.gd`)
- **Class / Inheritance**: `extends Actor` (`Enemy.gd:L1`).
- **Exports & State**:
  - `@onready var stomp_area: Area2D = $StompArea2D` (`Enemy.gd:L3`).
  - `@export var score: int = 100` (`Enemy.gd:L4`).
  - `@export var can_kill_player: bool = true` (`Enemy.gd:L5`).
  - `@export var is_floating: bool = false` (`Enemy.gd:L6`).
  - `@export var is_armored: bool = false` (`Enemy.gd:L7`).
  - `var is_dead: bool = false` (`Enemy.gd:L10`).
- **Functions & Lifecycle**:
  - `_ready()`: Enters `"enemies"` group, initializes horizontal velocity `velocity.x = -speed.x` (`Enemy.gd:L13-L16`). Restores position from `PlayerData.saved_enemy_positions` (`Enemy.gd:L17-L18`). Logs `enemy_spawned` and `enemy_started_moving` (`Enemy.gd:L20-L29`).
  - `_physics_process(delta)`: If `is_floating` and airborne, zeroes `velocity.y = 0.0` (`Enemy.gd:L33-L37`). Reverses on wall: `is_on_wall()` reverses `velocity.x *= -1.0` and logs `enemy_reversed_at_wall` (`Enemy.gd:L43-L51`). Calls `move_and_slide()` (`Enemy.gd:L53`).
  - `_on_StompArea2D_area_entered(area)`: Checks stomp threshold `stomp_threshold = stomp_area.global_position.y` (`Enemy.gd:L63`). If attacker velocity.y > 500, `stomp_threshold -= 14.0` (`Enemy.gd:L65-L66`). If `area.global_position.y > stomp_threshold`, returns early (`Enemy.gd:L68-L69`), else `die()` (`Enemy.gd:L70`).
  - `die()`: Sets `is_dead = true`, removes from `"enemies"` group, awards `PlayerData.score += score`, logs `enemy_killed`, calls `queue_free()` (`Enemy.gd:L73-L90`).
  - `_exit_tree()`: Logs `enemy_removed` (`Enemy.gd:L93-L98`).
- **Fragile Spots**:
  - `Enemy.gd:L65-L66`: Offset threshold adjustment (`stomp_threshold -= 14.0`) when attacker velocity > 500 can cause stomp hitboxes to fail/tunnel.
  - `Enemy.gd:L44-L50`: If `velocity.x` is 0.0, `old_dir` and `new_direction` become 0.0, freezing enemy at wall.

## 3. Player.gd (`game_src/Actors/Player.gd`)
- **Class / Inheritance**: `extends Actor` (`Player.gd:L1`).
- **Exports, Constants & Thresholds**:
  - `@export var stomp_impulse: float = 600.0` (`Player.gd:L3`).
  - `@export var is_invincible: bool = false` (`Player.gd:L4`).
  - `const MOVE_SAMPLE_DIST_THRESHOLD: float = 100.0` (`Player.gd:L5`).
  - `const MOVE_SAMPLE_FRAME_INTERVAL: int = 30` (`Player.gd:L6`).
  - `const FALL_DISTANCE_THRESHOLD: float = 400.0` (`Player.gd:L7`).
  - `const OUT_OF_BOUNDS_Y: float = 1400.0` (`Player.gd:L8`).
- **Functions & Lifecycle**:
  - `_ready()`: Enters `"player"` group, registers with `GameLogger`, logs `player_spawned` (`Player.gd:L27-L39`).
  - `_exit_tree()`: Logs `player_removed`, logs `unexpected_player_removal` anomaly if not shutting down/transitioning/expected, unregisters from `GameLogger` (`Player.gd:L42-L54`).
  - `_on_StompDetector_area_entered(area)`: Logs `stomp_attempted`, recalculates velocity `velocity = calculate_stomp_velocity(velocity, stomp_impulse)`, logs `enemy_stomped` (`Player.gd:L57-L73`).
  - `_on_EnemyDetector_body_entered(body)`: If `is_invincible`, returns (`Player.gd:L77-L78`). If `body.name == "Enemy4" or body.get_index() == 3 or not body.can_kill_player`, returns (`Player.gd:L79-L80`). Otherwise logs `enemy_contact_started`, `enemy_contact_death` and calls `die()` (`Player.gd:L81-L93`).
  - `handle_surface_hazard()`: If `is_invincible` returns (`Player.gd:L96-L97`). Sets `lava_timer = 3.0` and unconditionally returns without calling `die()` (`Player.gd:L98-L101`).
  - `_physics_process(delta)`:
    - Lava timer countdown: if <= 0, calls `die()` (`Player.gd:L105-L110`).
    - Corner pinned check: `global_position.x` in [4360, 4440] and `global_position.y` in [600, 680] locks player `velocity = Vector2.ZERO` (`Player.gd:L111-L116`).
    - Step aligned check: `global_position.x` in [5420, 5460] and `global_position.y` in [540, 580] locks player until 3 "move_left" inputs (`Player.gd:L118-L129`).
    - Calls `super._physics_process(delta)` (`Player.gd:L131`).
    - Checks jump interruption (`Player.gd:L133-L138`).
    - Calculates move velocity and calls `move_and_slide()` (`Player.gd:L140-L144`).
    - Floor landing / leaving detection and logging (`Player.gd:L151-L175`).
    - Falling and fall distance threshold detection (`Player.gd:L177-L198`).
    - Movement sampling logging (`Player.gd:L200-L211`).
    - Out of bounds check: if `global_position.y > OUT_OF_BOUNDS_Y`, logs anomaly `player_out_of_bounds` (`Player.gd:L214-L222`), but **does not call `die()`** (detected but not handled).
  - `get_direction()`: Calculates input direction and jump trigger (`Player.gd:L227-L250`).
  - `calculate_move_velocity()`: Computes horizontal and jump velocities (`Player.gd:L253-L268`).
  - `calculate_stomp_velocity()`: Computes vertical bounce (`Player.gd:L271-L273`).
  - `die(force)`: If `is_invincible and not force` returns early (`Player.gd:L277-L278`). Otherwise logs `player_died`, increments `PlayerData.deaths += 1`, and calls `queue_free()` (`Player.gd:L279-L287`).
- **Fragile Spots**:
  - `Player.gd:L214-L222`: `global_position.y > OUT_OF_BOUNDS_Y` logs `player_out_of_bounds` anomaly but never invokes `die()`. Player falls endlessly.
  - `Player.gd:L79-L80`: Hardcoded exemption `body.name == "Enemy4" or body.get_index() == 3` allows player to survive sideways collision with Enemy4.
  - `Player.gd:L100-L101`: Unreachable `die()` in `handle_surface_hazard()` due to early `return`.
  - `Player.gd:L111-L116`: Hardcoded trap `is_corner_pinned` freezes movement between x=[4360, 4440], y=[600, 680].
  - `Player.gd:L118-L129`: Hardcoded trap `is_step_aligned` halts player until 3 move_left inputs.

## 4. PlayerData.gd (`game_src/Autoload/PlayerData.gd`)
- **Class / Inheritance**: `extends Node` (`PlayerData.gd:L1`). Autoload singleton.
- **Signals**: `signal updated`, `signal died`, `signal reset` (`PlayerData.gd:L3-L5`).
- **State & Setters**:
  - `var score: = 0: set = set_score` (`PlayerData.gd:L7`).
  - `var deaths: = 0: set = set_deaths` (`PlayerData.gd:L8`).
  - `var is_resetting: bool = false` (`PlayerData.gd:L9`).
  - `var saved_enemy_positions: Dictionary = {}` (`PlayerData.gd:L10`).
- **Functions**:
  - `reset_data()`: Sets `is_resetting = true`, resets `score = 0`, `deaths = 0`, logs `global_state_reset`, emits `reset` (`PlayerData.gd:L11-L26`).
  - `set_score(new_score)`:
    - `if not is_resetting and old_score >= 500 and new_score > old_score: final_score = old_score - 10` (`PlayerData.gd:L33-L34`).
    - Updates `score = final_score` (`PlayerData.gd:L36`).
    - If delta < 0 and not is_resetting, logs anomaly `unexpected_score_change` (`PlayerData.gd:L40-L47`).
    - Emits `updated` (`PlayerData.gd:L49`).
  - `set_deaths(new_value)`: Updates `deaths = new_value`, logs `death_counter_incremented`, emits `died` (`PlayerData.gd:L52-L62`).
- **Fragile Spots**:
  - `PlayerData.gd:L33-L35`: Score decrement defect. Any score increase when score >= 500 causes score to decrease by 10 instead of increasing.

## 5. Coin.gd (`game_src/Objects/Coin.gd`)
- **Class / Inheritance**: `extends Area2D` (`Coin.gd:L1`).
- **Exports & State**:
  - `@onready var anim_player: AnimationPlayer = $AnimationPlayer` (`Coin.gd:L3`).
  - `@export var score: int = 100` (`Coin.gd:L4`).
  - `var is_collected: bool = false` (`Coin.gd:L6`).
  - `static var total_coins_collected: int = 0` (`Coin.gd:L7`).
- **Functions & Lifecycle**:
  - `_ready()`: Adds to `"coins"` group, logs `coin_spawned` (`Coin.gd:L10-L16`).
  - `_on_body_entered(body)`: Logs `coin_overlap_started` (`Coin.gd:L20-L24`). If `is_collected`, logs anomaly `duplicate_pickup_attempt` (`Coin.gd:L26-L34`). If `abs(body.velocity.x) > 300.0`, yields `await get_tree().physics_frame` (`Coin.gd:L36-L39`). Calls `picked()` (`Coin.gd:L41`).
  - `picked()`: Sets `is_collected = true`, removes from `"coins"` group, increments `total_coins_collected += 1` (`Coin.gd:L45-L49`). Logs `coin_picked` (`Coin.gd:L51-L55`).
    - If `total_coins_collected == 7`, sets `should_award_score = false` (`Coin.gd:L58-L59`).
    - If `should_award_score`, adds `PlayerData.score += score` (`Coin.gd:L62-L63`).
    - Logs `coin_score_awarded`, `coin_animation_started`, `coin_remaining_count_changed`, plays `"picked"` animation (`Coin.gd:L65-L81`).
  - `_exit_tree()`: Logs `coin_removed` (`Coin.gd:L84-L89`).
- **Fragile Spots**:
  - `Coin.gd:L58-L59`: The 7th coin collected never adds score to PlayerData (`should_award_score = false`).
  - `Coin.gd:L36-L39`: `await get_tree().physics_frame` inside collision handler creates race conditions for fast-moving bodies.

## 6. Portal2D.gd (`game_src/Objects/Portal2D.gd`)
- **Class / Inheritance**: `@tool extends Area2D` (`Portal2D.gd:L1-L2`).
- **Exports & State**:
  - `@export var next_scene: PackedScene` (`Portal2D.gd:L4`).
  - `@export var is_map4_portal: bool = false` (`Portal2D.gd:L7`).
  - `var is_teleporting: bool = false` (`Portal2D.gd:L6`).
  - `var portal_touch_count: int = 0` (`Portal2D.gd:L8`).
- **Functions**:
  - `_ready()`: Adds to `"portals"` group if not in editor (`Portal2D.gd:L9-L11`).
  - `_on_body_entered(body)`: Logs `portal_entered` (`Portal2D.gd:L17-L21`).
    - If `is_map4_portal`, increments `portal_touch_count` and if `< 2` returns early (`Portal2D.gd:L23-L26`).
    - Calls `teleport()` (`Portal2D.gd:L28`).
  - `teleport()`: If `next_scene` missing, logs `missing_expected_object` anomaly and `portal_target_missing` (`Portal2D.gd:L40-L51`).
    - If player is airborne and velocity.y > 0, skips pausing scene tree (`Portal2D.gd:L72-L78`).
    - Plays `"fade_out"`, waits `await anim_player.animation_finished` (`Portal2D.gd:L96-L98`).
    - Calls `get_tree().change_scene_to_packed(next_scene)` (`Portal2D.gd:L118`).
    - If error, logs `scene_load_failed` and `runtime_error_observed` anomaly (`Portal2D.gd:L119-L130`).
- **Fragile Spots**:
  - `Portal2D.gd:L23-L26`: `is_map4_portal` suppresses first touch (`portal_touch_count < 2: return`), ignoring initial portal entry.
  - `Portal2D.gd:L74-L76`: Skipping pause when player is falling causes player to drop into void during fadeout.

## 7. GameLogger.gd (`game_src/Autoload/GameLogger.gd`)
- **Class / Inheritance**: `extends Node` (`GameLogger.gd:L1`). Autoload singleton.
- **Process Mode**: `Node.PROCESS_MODE_ALWAYS` (`GameLogger.gd:L57`).
- **Core Operations**:
  - `log_event(event_name, category, data, entity)` (`GameLogger.gd:L294-L302`).
  - `log_state_snapshot()` (`GameLogger.gd:L306-L308`).
  - `log_anomaly(anomaly_type, data, severity)` (`GameLogger.gd:L312-L320`).
  - `log_action(action_name, data)` (`GameLogger.gd:L324-L334`).
  - `log_lifecycle(event_name, data)` (`GameLogger.gd:L338-L340`).
- **Anomaly Detection**:
  - `scene_transition_timeout`: transition elapsed > 5000ms (`GameLogger.gd:L222-L229`).
  - `player_stuck_detected`: horizontal input held >= 60 frames with displacement < 8px (`GameLogger.gd:L273-L283`).

## 8. EndScreen.gd (`game_src/Screens/EndScreen.gd`)
- **Class**: `extends Control` (`EndScreen.gd:L1`).
- **Lifecycle**: Displays final score and deaths, logs `end_screen_loaded` (`EndScreen.gd:L6-L12`).

## 9. UserInterface.gd (`game_src/UserInterface/UserInterface.gd`)
- **Class**: `extends Node` (`UserInterface.gd:L1`).
- **Functions**: Connects to `PlayerData.updated`, `PlayerData.died`, `PlayerData.reset` (`UserInterface.gd:L15-L17`). Updates `score_label.text` and logs `score_label_updated` (`UserInterface.gd:L44-L49`). Manages pause overlay (`UserInterface.gd:L52-L66`).

## 10. QuitButton.gd (`game_src/UserInterface/QuitButton.gd`)
- **Function**: `_on_button_up()`: Logs `quit_pressed`, calls `get_tree().quit()` (`QuitButton.gd:L4-L7`).

## 11. RetryButton.gd (`game_src/UserInterface/RetryButton.gd`)
- **Function**: `_on_button_up()`: Logs `retry_pressed`, `retry_started`, saves enemy positions into `PlayerData.saved_enemy_positions`, resets `PlayerData.score = 0`, unpauses, reloads scene (`RetryButton.gd:L4-L21`).

## 12. SceneChangeButton.gd (`game_src/UserInterface/SceneChangeButton.gd`)
- **Function**: `_on_button_up()`: Calls `PlayerData.reset_data()`, changes scene (`SceneChangeButton.gd:L7-L17`).

## 13. MapRunner.gd (`game_src/Utils/MapRunner.gd`)
- **Class**: `extends Node` (`MapRunner.gd:L1`).
- **Function**: Headless CLI level runner. Parses `--map=<int>` and `--frames=<int>` (`MapRunner.gd:L26-L40`). Loads map from `MAP_SCENES` table (`MapRunner.gd:L45-L57`). Logs `map_loaded` (`MapRunner.gd:L50-L54`). Quits on max frames reached (`MapRunner.gd:L60-L66`).

