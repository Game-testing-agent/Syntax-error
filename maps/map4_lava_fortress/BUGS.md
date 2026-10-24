# Map 4: Lava Fortress — Documented Bugs

This document details all intentional benchmark bugs planted in **Map 4: Lava Fortress** (`godot-4game/src/Levels/Map4_LavaFortress.tscn`).

---

### Bug 4A: Delayed Lava Death with 3-Second Grace Period
- **Bug ID**: `4A`
- **Tile Coordinates**: `x=43..53, y=10..12` — Global Position: `x=3480..4280, y=800..960`
- **Steps to Reproduce**:
  1. Launch Map 4: `python run_map.py --map 4`.
  2. Run right across the initial battlement bridge directly into `LavaPit1`.
- **Expected Behavior**:
  Touching lethal lava instantly kills the player, halts inputs, and triggers the death sequence.
- **Actual Behavior**:
  Lava contact does not kill instantly. A 3-second grace period timer initiates, during which the player can jump out, collect coins, and run freely before death finally executes.
- **Exact BUGTRIGGER Log Line**:
  ```text
  [BUGTRIGGER] 4A: {"description":"Lava contact delayed death initiated (3 seconds grace period)","position":[3520.0,820.0]}
  ```

---

### Bug 4B: Goal Portal Requires Two Touches
- **Bug ID**: `4B`
- **Tile Coordinates**: `(215, 6)` — Global Position: `(17200, 480)`
- **Steps to Reproduce**:
  1. Launch Map 4: `python run_map.py --map 4`.
  2. Traverse through the fortress to reach the goal `Portal2D` at the far right.
  3. Walk into the portal area for the first time.
- **Expected Behavior**:
  Touching the portal triggers the completion overlay and teleports to the next level immediately.
- **Actual Behavior**:
  The first contact is registered and logged, but teleportation fails to trigger. The player must step back out and touch the portal a second time to trigger the victory teleport.
- **Exact BUGTRIGGER Log Line**:
  ```text
  [BUGTRIGGER] 4B: {"description":"Portal first touch ignored, activation requires second touch","required_touches":2,"teleport_triggered":false,"touch_count":1}
  ```

---

### Bug 4C: Retry Preserves Enemy Coordinates
- **Bug ID**: `4C`
- **Tile Coordinates**: Global Level Scope
- **Steps to Reproduce**:
  1. Launch Map 4: `python run_map.py --map 4`.
  2. Run forward so patrol enemies (e.g., `Enemy1`, `Enemy2`) walk away from their initial spawn origins.
  3. Pause the game or die and click "Retry".
- **Expected Behavior**:
  Level restart completely reloads the scene tree, resetting all enemy positions and orientations back to their default scene file coordinates.
- **Actual Behavior**:
  While the player respawns at the starting point, all enemies retain their mid-patrol coordinates and orientations from before the retry.
- **Exact BUGTRIGGER Log Line**:
  ```text
  [BUGTRIGGER] 4C: {"description":"Retry triggered without resetting enemy positions","enemy_count":12}
  ```

