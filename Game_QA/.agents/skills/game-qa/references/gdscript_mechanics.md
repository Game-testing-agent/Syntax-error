# GDScript Mechanics & Known Bug Signatures

This document lists ground-truth mechanics and code bug patterns for the 2D platformer.

## 1. Player Collision & Invincibility
- **File**: `game_src/Actors/Player.gd`
- **Method**: `_on_EnemyDetector_body_entered(body: PhysicsBody2D)`
- **Working Behavior**: When player collides with an enemy from the side (`player_is_above == false`), `die()` must be called, incrementing `PlayerData.deaths` and queuing player removal.
- **Invariants**: Lateral hazard contact must result in damage or death; invincibility frames should only exist if explicitly granted by design.

## 2. Enemy Wall Reversal
- **File**: `game_src/Actors/Enemy.gd`
- **Method**: `_physics_process(delta)`
- **Working Behavior**: When an enemy hits a wall (`is_on_wall() == true`), `velocity.x *= -1.0` flips direction.
- **Invariants**: Patrol velocity must remain non-zero; enemies should not become stationary or oscillate indefinitely at boundaries.

## 3. Score Monotonicity
- **File**: `game_src/Autoload/PlayerData.gd`
- **Method**: `set_score(new_score)`
- **Working Behavior**: Score reflects accumulated gameplay achievements.
- **Invariants**: Score must change monotonically non-negative (only increasing during active play, or resetting upon intentional player/level restart).

## 4. Collectibles Lifecycle
- **File**: `game_src/Objects/Coin.gd`
- **Method**: `_on_body_entered(body)`
- **Working Behavior**: When a valid player overlaps a coin, the coin triggers collection, disables further interaction, awards points, and plays animation before cleanup.
- **Invariants**: Collectible pickup must be idempotent; a single entity must not award score or trigger pickup events multiple times.

