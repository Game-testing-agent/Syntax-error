# Map 3: Sky Castle — Documented Bugs

This document details all intentional benchmark bugs planted in **Map 3: Sky Castle** (`godot-4game/src/Levels/Map3_SkyCastle.tscn`).

---

### Bug 3A: Staircase Edge Sticky State
- **Bug ID**: `3A`
- **Tile Coordinates**: `(68, 7)` — Global Position: `(5440, 560)`
- **Steps to Reproduce**:
  1. Launch Map 3: `python run_map.py --map 3`.
  2. Walk right across the sky ramparts until reaching the grand central staircase at `x ≈ 5400`.
  3. Step onto the lip of the stair step at tile `(68, 7)`.
- **Expected Behavior**:
  Player smoothly ascends or steps down the staircase with normal responsive directional controls and jumping.
- **Actual Behavior**:
  The player hangs on the stair edge in a frozen standing state. Forward movement and jumping are unresponsive until the player taps the opposite direction (`move_left`) 3 distinct times.
- **Exact BUGTRIGGER Log Line**:
  ```text
  [BUGTRIGGER] 3A: {"description":"Player stuck on stair edge at tile (68, 7)","position":[5440.0,560.0],"tile":[68,7]}
  ```

---

### Bug 3B: Unstompable 4th Enemy
- **Bug ID**: `3B`
- **Tile Coordinates**: `(88, 7)` — Global Position: `(7040, 560)`
- **Steps to Reproduce**:
  1. Launch Map 3: `python run_map.py --map 3`.
  2. Advance to the castle courtyard and locate `Enemy4` (the 4th enemy ordered left to right).
  3. Jump above `Enemy4` and stomp directly onto its head.
- **Expected Behavior**:
  The stomp detector triggers, squashes/frees the enemy, and bounces the player upward with vertical impulse.
- **Actual Behavior**:
  The stomp collision is detected and logged, and the player bounces upward, but the enemy is not destroyed and continues patrolling unaffected.
- **Exact BUGTRIGGER Log Line**:
  ```text
  [BUGTRIGGER] 3B: {"description":"Enemy4 stomped but ignored damage","enemy":"Enemy4"}
  ```

---

### Bug 3C: Final Tower Wall Double Jump Height
- **Bug ID**: `3C`
- **Tile Coordinates**: `(195, 7)` — Global Position: `(15600, 560)`
- **Steps to Reproduce**:
  1. Launch Map 3: `python run_map.py --map 3`.
  2. Advance across the fortress parapets to the base of the final tower at `x ≈ 15600`.
  3. Press against the left stone wall of the tower and press the jump button.
- **Expected Behavior**:
  Player performs a standard jump with vertical impulse `velocity.y = -1000.0`.
- **Actual Behavior**:
  Touching the tower's left wall multiplies jump strength by 2x (`velocity.y = -2000.0`), launching the player twice as high into the sky.
- **Exact BUGTRIGGER Log Line**:
  ```text
  [BUGTRIGGER] 3C: {"description":"Double jump height triggered at tower wall","jump_speed":-2000.0,"position":[15605.0,560.0]}
  ```

