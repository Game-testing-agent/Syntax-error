# Telemetry Specification for Godot Platformer

## Log File: `game_events.jsonl`

Lines in `game_events.jsonl` follow JSON Lines formatting with the following key fields:

### 1. State Snapshot (`category == "state_snapshot"`)
Emitted periodically (~15-60 Hz) containing full game state:
- `data.player`: Position `(x, y)`, velocity `(vel_x, vel_y)`, collision flags (`on_floor`, `on_wall`, `on_ceiling`), `alive` flag.
- `data.enemies`: Total enemy count, list of active enemies, and `closest_enemy` with `distance`, `relative_x`, `relative_y`, `is_threat`, `is_stompable`, `player_is_above`.
- `data.coins`: Coins remaining, coins collected, `nearest_coin`.
- `data.stats`: Score and deaths count.
- `data.fps`: Current framerate.
- `data.scene`: Active scene file path.

### 2. Discrete Events (`category != "state_snapshot"`)
- `player_spawned`, `player_moved`, `player_landed`, `player_left_floor`, `player_died`
- `jump_started`, `jump_interrupted`, `fall_started`
- `enemy_spawned`, `enemy_started_moving`, `enemy_reversed_at_wall`, `enemy_killed`, `enemy_contact_started`
- `coin_spawned`, `coin_picked`, `coin_score_awarded`, `duplicate_pickup_attempt`
- `portal_entered`, `portal_transition_started`, `scene_loaded`
- `anomaly`: Explicit engine anomaly logged by `GameLogger.gd` with `expected`, `observed`, and `severity`.

