# Game Log Schema v3

This schema matches the current `GameLogger.gd` convention: every event record has
`session_id`, an incrementing `event_id`, `event_name`, `category`,
`timestamp_unix_ms`, `elapsed_ms`, `physics_frame`, `scene`, player context,
game state, entity context, recent actions, evidence, and event-specific `data`.

## Record identity and ordering

- `unique_id` is the **first attribute in each converted record**.
- When available, `unique_id` is formed as `session_id:event_id`, e.g.
  `session_1792771787_87516:42`. Since event IDs restart each session,
  combining these fields distinguishes events across sessions.
- If a legacy source record is missing either `session_id` or `event_id`, the
  converter uses `legacy-line:<source line number>` as a unique fallback within
  this conversion of the input file.

- `session_id`: identifies the session. It changes for a new logger session.
- `event_id`: monotonically increments within a session and starts again at 1
  for the next session. Use `unique_id` as the logical event key; it is derived from `(session_id, event_id)`.
- `timestamp_unix_ms`: event time in Unix milliseconds, at the root record; `null` is retained if a malformed/legacy source record has no timestamp.
- `elapsed_ms`: milliseconds since the current session began.
- `physics_frame`: physics frame when the event was built.
- `frame`: process-frame counter from a state snapshot's `data.frame`.
- `state_physics_frame`: nested snapshot's physics frame, kept separate from the
  event-level `physics_frame`.
- `state_timestamp_unix_ms`: snapshot's own timestamp, normalized from
  `data.timestamp` (seconds) if present. This can differ slightly from the event
  timestamp.
- The converter retains every valid event by default. It does not collapse events
  with the same timestamp or second. Use `--latest-per-second` only if you
  intentionally want a lossy reduction.
- Records are sorted by event timestamp; same-time records retain input order.
  Records without timestamps are retained at the end with `timestamp_unix_ms: null`.

## Top-level keys

| Key | Meaning |
|---|---|
| `unique_id` | First field; `session_id:event_id`, or a legacy line fallback when source IDs are unavailable. |
| `schema_version` | Version of the source logger schema. |
| `session_id` | Session identifier; combine with `event_id` for identity. |
| `event_id` | Sequential identifier assigned by `_build_record()`, resets each session. |
| `event_name` | Name of the event, e.g. `session_start`, `state_snapshot`, `coin_picked`. |
| `category` | Event category, e.g. `state_snapshot`, `input`, `collectible`, `anomaly`. |
| `timestamp_unix_ms` | Canonical event timestamp in milliseconds. |
| `elapsed_ms` | Time elapsed in session at event creation. |
| `physics_frame` | Event-level physics frame. |
| `frame` | Process frame from the state payload, when present. |
| `state_physics_frame` | Physics frame inside the state-snapshot payload, when present. |
| `state_timestamp_unix_ms` | Snapshot timestamp converted to milliseconds, when present. |
| `session_time` | Snapshot session time in seconds, if available. |
| `fps` | Frames per second from the snapshot, if available. |
| `scene` | Scene path or name from the event envelope. |
| `state_scene` | Scene name from the detailed state snapshot. |
| `game_state` | State string such as `playing`, `paused`, `player_died`, `victory`, or `main_menu`. |
| `paused` | Pause flag taken from the event envelope's `game_state` object; `null` if unavailable. |
| `stats` | `[score, deaths]`. |
| `player_instance_id` | Player's Godot instance ID when available. |
| `player` | Fixed player array, or `null`. |
| `inputs` | Fixed input array, or `null`. |
| `coins` | `[coins_collected, coins_remaining, nearest_coin, all_coins]`, or `null`. |
| `enemies` | `[count, closest_enemy, all_enemies]`, or `null`. |
| `goal` | `[found, portal_x, portal_y, distance_to_portal, relative_x, relative_y]`, or `null`. |
| `entity` | Event's entity object, preserved as an object or `null`. |
| `recent_actions` | Recent actions, each encoded as `[action, physics_frame, timestamp_unix_ms]`. |
| `evidence` | Evidence object, usually containing `screenshot_path`. |
| `extra` | Event-specific data or unrecognized source fields not represented elsewhere. |

## Positional arrays

Every array uses a fixed order. `null` means unavailable. Boolean values in arrays
are encoded as `1` (true) and `0` (false); numeric zero remains `0`.

### `stats`

`[score, deaths]`
- 0: current score.
- 1: current death count.

### `player` — 16 positions

`[alive, x, y, velocity_x, velocity_y, on_floor, on_wall, on_ceiling, facing, stomp_impulse, speed_max_x, speed_max_y, hitbox_width, hitbox_height, distance_to_ground, distance_to_wall_ahead]`

| Index | Field | Meaning |
|---:|---|---|
| 0 | `alive` | 1 if present/alive, 0 if not, null if unknown |
| 1 | `x` | Player world X coordinate |
| 2 | `y` | Player world Y coordinate |
| 3 | `velocity_x` | Horizontal velocity |
| 4 | `velocity_y` | Vertical velocity |
| 5 | `on_floor` | 1 if on floor, 0 if not |
| 6 | `on_wall` | 1 if touching a wall |
| 7 | `on_ceiling` | 1 if touching the ceiling |
| 8 | `facing` | Typically 1=right, -1=left |
| 9 | `stomp_impulse` | Configured stomp/bounce impulse |
| 10 | `speed_max_x` | Configured maximum horizontal speed |
| 11 | `speed_max_y` | Configured maximum vertical speed |
| 12 | `hitbox_width` | Hitbox width in game units |
| 13 | `hitbox_height` | Hitbox height in game units |
| 14 | `distance_to_ground` | Raycast distance; -1 may mean no ground hit |
| 15 | `distance_to_wall_ahead` | Raycast distance ahead; -1 may mean no wall hit |

The separate top-level `player_instance_id` preserves the instance ID from the event-level player object.

### `inputs` — 7 positions

`[move_left, move_right, jump, jump_just_pressed, pause, raw_direction_x, raw_direction_y]`

| Index | Field | Meaning |
|---:|---|---|
| 0 | `move_left` | 1 if left input is pressed |
| 1 | `move_right` | 1 if right input is pressed |
| 2 | `jump` | 1 if jump is held |
| 3 | `jump_just_pressed` | 1 if jump was newly pressed this frame |
| 4 | `pause` | 1 if pause input is pressed |
| 5 | `raw_direction_x` | Right strength minus left strength |
| 6 | `raw_direction_y` | Vertical component supplied by the logger |

### Coin row — 6 positions

`[id, x, y, distance, relative_x, relative_y]`

| Index | Field | Meaning |
|---:|---|---|
| 0 | `id` | Coin instance ID |
| 1 | `x` | Coin world X coordinate |
| 2 | `y` | Coin world Y coordinate |
| 3 | `distance` | Player-to-coin distance |
| 4 | `relative_x` | Coin X minus player X; positive means right |
| 5 | `relative_y` | Coin Y minus player Y |

`coins = [coins_collected, coins_remaining, nearest_coin, all_coins]`.

### Enemy row — 11 positions

`[id, name, x, y, velocity_x, distance, relative_x, relative_y, player_is_above, is_stompable, is_threat]`

| Index | Field | Meaning |
|---:|---|---|
| 0 | `id` | Enemy instance ID |
| 1 | `name` | Enemy node/name |
| 2 | `x` | Enemy world X coordinate |
| 3 | `y` | Enemy world Y coordinate |
| 4 | `velocity_x` | Enemy horizontal velocity |
| 5 | `distance` | Player-to-enemy distance |
| 6 | `relative_x` | Enemy X minus player X |
| 7 | `relative_y` | Enemy Y minus player Y |
| 8 | `player_is_above` | 1 if the logger's above-player test is true |
| 9 | `is_stompable` | 1 if the logger flags the enemy as stompable |
| 10 | `is_threat` | 1 if the logger flags the enemy as a threat |

`enemies = [count, closest_enemy, all_enemies]`.

### `goal` — 6 positions

`[found, portal_x, portal_y, distance_to_portal, relative_x, relative_y]`

- 0: whether a portal was found (1=true, 0=false).
- 1–2: portal's world X and Y coordinates.
- 3: distance from player to portal.
- 4–5: portal position relative to player.

### Recent-action row — 3 positions

`[action, physics_frame, timestamp_unix_ms]`
- 0: action name.
- 1: physics frame when the action occurred.
- 2: Unix timestamp in milliseconds when it occurred.

## Event-specific information

The converter retains event payloads that do not fit the common state arrays under
`extra.data`. For snapshot payloads, it stores otherwise-unmapped payload keys
under `extra.data_extra`. Unexpected root fields are preserved under
`extra.root_extra`. `entity` and `evidence` are kept as their own top-level fields.

## Usage

```bash
python convert_game_events_to_schema_v3.py
```

Read `game_events.jsonl` and write `converted_game_events.jsonl`.

To optionally keep only the latest record per second **within each session**:

```bash
python convert_game_events_to_schema_v3.py --latest-per-second
```

That option drops intermediate events and should not be used if every event matters.
