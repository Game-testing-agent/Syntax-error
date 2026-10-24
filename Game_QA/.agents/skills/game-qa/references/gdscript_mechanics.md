# GDScript Mechanics & Known Bug Signatures

This document lists ground-truth mechanics and code bug patterns for the 2D platformer.

## 1. Player Collision & Invincibility
- **File**: `game_src/Actors/Player.gd`
- **Method**: `_on_EnemyDetector_body_entered(body: PhysicsBody2D)`
- **Working Behavior**: When player collides with an enemy from the side (`player_is_above == false`), `die()` must be called, incrementing `PlayerData.deaths` and queuing player removal.
- **Bug Signatures**:
  - `is_invincible == true`: Player touches enemy without taking damage or dying.
  - Hardcoded exemption: `if body.name == "Enemy4" or body.get_index() == 3 ... return` prevents the 4th enemy from damaging the player.

## 2. Enemy Wall Reversal
- **File**: `game_src/Actors/Enemy.gd`
- **Method**: `_physics_process(delta)`
- **Working Behavior**: When an enemy hits a wall (`is_on_wall() == true`), `velocity.x *= -1.0` flips direction.
- **Bug Signature**:
  - `old_direction == 0.0 and new_direction == 0.0`: Enemy gets stuck in a wall without moving.

## 3. Score Monotonicity
- **File**: `game_src/Autoload/PlayerData.gd`
- **Method**: `set_score(new_score)`
- **Working Behavior**: Score can only increase or reset to 0 upon death/restart (`is_resetting == true`).
- **Bug Signature**:
  - Score decreasing during active gameplay without reset.

## 4. Coin Double-Collection
- **File**: `game_src/Objects/Coin.gd`
- **Method**: `_on_body_entered(body)`
- **Working Behavior**: Coin sets `is_collected = true` and emits `coin_picked`.
- **Bug Signature**:
  - If physics frames trigger duplicate `_on_body_entered` events before the node is freed, `duplicate_pickup_attempt` is logged.

