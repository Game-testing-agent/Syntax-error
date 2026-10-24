# Telemetry Orientation & Sessions (Phase B1)

## Session Summary
- **Session ID**: `session_1792862072_26412`
- **Total Events**: 1264
- **Total Snapshots**: 42
- **Duration**: 0.00s (frame 0) to 43.47s (frame 2557)
- **Log Source**: `C:\Users\hunne\Documents\Syntax-error\game_events.jsonl`

---

## Distinct Event Types, Frequencies & Payloads

| Event Name | Category | Count | Payload Fields |
|---|---|---|---|
| `player_moved` | `player_movement` | 874 | `distance`, `from_position`, `to_position`, `velocity`, `player`, `entity`, `game_state` |
| `coin_spawned` | `collectible` | 25 | `position`, `score_value`, `player`, `entity`, `game_state` |
| `coin_removed` | `collectible` | 25 | `position`, `was_collected`, `player`, `entity`, `game_state` |
| `move_right_pressed` | `input` | 25 | `action`, `pressed`, `strength`, `player`, `entity`, `game_state` |
| `move_right_released` | `input` | 25 | `action`, `pressed`, `player`, `entity`, `game_state` |
| `jump_pressed` | `input` | 21 | `action`, `pressed`, `strength`, `player`, `entity`, `game_state` |
| `jump_released` | `input` | 21 | `action`, `pressed`, `player`, `entity`, `game_state` |
| `fall_started` | `player_movement` | 20 | `start_position`, `velocity`, `player`, `entity`, `game_state` |
| `player_landed` | `player_movement` | 19 | `fall_distance`, `horizontal_displacement`, `position`, `was_jumping`, `player`, `entity`, `game_state` |
| `jump_started` | `player_movement` | 16 | `initial_velocity`, `speed`, `start_position`, `player`, `entity`, `game_state` |
| `move_left_pressed` | `input` | 16 | `action`, `pressed`, `strength`, `player`, `entity`, `game_state` |
| `move_left_released` | `input` | 16 | `action`, `pressed`, `player`, `entity`, `game_state` |
| `score_label_updated` | `ui` | 14 | `displayed_score`, `player`, `entity`, `game_state` |
| `enemy_spawned` | `enemy` | 12 | `position`, `score_value`, `speed`, `player`, `entity`, `game_state` |
| `enemy_started_moving` | `enemy` | 12 | `direction_x`, `velocity_x`, `player`, `entity`, `game_state` |
| `enemy_removed` | `enemy` | 12 | `position`, `was_killed`, `player`, `entity`, `game_state` |
| `coin_overlap_started` | `collectible` | 10 | `collector`, `position`, `player`, `entity`, `game_state` |
| `coin_picked` | `collectible` | 10 | `position`, `score`, `player`, `entity`, `game_state` |
| `coin_score_awarded` | `collectible` | 10 | `score_after`, `score_before`, `score_gain`, `player`, `entity`, `game_state` |
| `coin_animation_started` | `collectible` | 10 | `animation`, `player`, `entity`, `game_state` |
| `coin_remaining_count_changed` | `collectible` | 10 | `remaining_count`, `player`, `entity`, `game_state` |
| `jump_interrupted` | `player_movement` | 9 | `position`, `velocity_before`, `player`, `entity`, `game_state` |
| `unexpected_score_change` | `anomaly` | 7 | `anomaly_type`, `details`, `expected`, `observed`, `severity`, `player`, `entity`, `game_state` |
| `enemy_reversed_at_wall` | `enemy` | 7 | `new_direction`, `old_direction`, `position`, `player`, `entity`, `game_state` |
| `stomp_attempted` | `enemy` | 5 | `area_name`, `enemy_position`, `player_position`, `player_velocity_y`, `player`, `entity`, `game_state` |
| `enemy_stomped` | `enemy` | 5 | `bounce_velocity`, `stomp_impulse`, `player`, `entity`, `game_state` |
| `enemy_stomp_area_entered` | `enemy` | 5 | `attacker_area_y`, `stomp_area_y`, `player`, `entity`, `game_state` |
| `bug_trigger` | `bug` | 5 | `bug_id`, `details`, `player`, `entity`, `game_state` |
| `enemy_killed` | `enemy` | 4 | `position`, `score_after`, `score_before`, `score_gain`, `player`, `entity`, `game_state` |
| `player_left_floor` | `player_movement` | 3 | `position`, `velocity`, `player`, `entity`, `game_state` |
| `fall_distance_threshold_reached` | `player_movement` | 2 | `fall_distance`, `position`, `threshold`, `player`, `entity`, `game_state` |
| `session_end` | `scene_lifecycle` | 2 | `session_duration_ms`, `total_events`, `player`, `entity`, `game_state` |
| `session_start` | `scene_lifecycle` | 1 | `godot_version`, `log_destinations`, `os`, `project_name`, `schema_version`, `player`, `entity`, `game_state` |
| `map_loaded` | `scene_lifecycle` | 1 | `map_index`, `scene_path`, `player`, `entity`, `game_state` |
| `player_spawned` | `player_lifecycle` | 1 | `position`, `speed`, `stomp_impulse`, `player`, `entity`, `game_state` |
| `scene_loaded` | `scene_lifecycle` | 1 | `previous_scene`, `scene`, `player`, `entity`, `game_state` |
| `level_loaded` | `scene_lifecycle` | 1 | `scene`, `player`, `entity`, `game_state` |
| `player_out_of_bounds` | `anomaly` | 1 | `anomaly_type`, `details`, `expected`, `observed`, `severity`, `player`, `entity`, `game_state` |
| `player_removed` | `player_lifecycle` | 1 | `position`, `player`, `entity`, `game_state` |

---

## Telemetry Observability & Blind Spots
1. **Unobservable Internal Physics Ticks**: Snapshots are sampled periodically (42 snapshots over 2557 frames ~ every 60 frames / 1.0s). Physics states occurring between snapshot intervals (sub-frame raycasts, exact contact normals, instantaneous frame-by-frame velocities) are unobservable unless explicitly logged as discrete events.
2. **Enemy Internal State**: Only discrete events (`enemy_spawned`, `enemy_started_moving`, `enemy_reversed_at_wall`, `enemy_stomp_area_entered`, `enemy_stomped`, `enemy_killed`, `enemy_removed`) log enemy state. Enemy positions are not continuously snapshotted in `snapshots.enemies` across all frames.
3. **Portal & Level Transition Completion**: No `portal_entered` or `scene_transition_completed` events were emitted in this session. Level 4 was loaded (`map_loaded`), but session ended before or upon player removal.
4. **Collision Shapes & TileMap Geometry**: Collision layers, masks, and exact tile boundaries are not streamed in telemetry payloads; they must be verified directly against scene wiring (`.tscn`) and GDScript contracts.

