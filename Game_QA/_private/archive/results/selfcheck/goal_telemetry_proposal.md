# Telemetry Proposal: Generic Goal & Level Finish Liveness Telemetry

## 1. Current State in `GameLogger.gd`
- In `state_snapshot` (lines 607–626), `GameLogger.gd` checks for nodes in the `"portals"` group. If found, it populates:
  ```json
  "goal": {
    "found": true,
    "distance_to_portal": 42.5,
    "portal_x": 7316.6,
    "portal_y": 160.0
  }
  ```
- If no node in `"portals"` is registered (the exact bug in Level01), `goal.found` defaults to `false` and `distance_to_portal` is `0.0`.
- In discrete events (lines 760–761), `GameLogger.gd` defines `"portal_entered"`, `"portal_transition_started"`, `"portal_fade_completed"`, and `"level_completed"`.

## 2. Identified Gap
There is no discrete event emitted when the player physically crosses into the exit zone or reaches proximity to the level terminus **independent** of `Portal2D`'s internal signal connection. Because `Portal2D.gd` failed silently to register or connect its collision callback, the game never emitted any event to signal that the end-of-level was reached.

## 3. Proposed Game Telemetry Additions
To make a generic, non-hardcoded liveness check possible across any level:
1. **Emit `level_terminus_reached` / `goal_proximity_entered`**:
   When the player's bounding box intersects the designated level finish Area2D or boundary:
   ```gdscript
   GameLogger.log_event("goal_proximity_entered", "portal", {
       "distance_to_goal": distance,
       "player_position": GameLogger.vec2_to_dict(global_position),
       "goal_name": name
   })
   ```
2. **Generic Invariant Rule in `checks.json`**:
   Once `goal_proximity_entered` fires, an engine liveness invariant can monitor the event stream:
   `if goal_proximity_entered occurred at t0, then portal_entered or level_completed must occur within 5.0 seconds.`
   If 5.0 seconds elapse without a transition, a deterministic Path 1 finding `Terminal Goal Liveness Timeout (Soft-Lock)` is surfaced immediately, without relying on level-specific coordinates.

