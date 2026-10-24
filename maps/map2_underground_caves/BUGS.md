# Map 2: Underground Caves — Documented Bugs

This document details all intentional benchmark bugs planted in **Map 2: Underground Caves** (`godot-4game/src/Levels/Map2_UndergroundCaves.tscn`).

---

### Bug 2A: Permanent Ceiling Gap Wall Wedge
- **Bug ID**: `2A`
- **Tile Coordinates**: `(55, 8)` — Global Position: `(4400, 640)`
- **Steps to Reproduce**:
  1. Launch Map 2: `python run_map.py --map 2`.
  2. Advance right through the cavern tunnels to tile column `x = 55`.
  3. Jump or step into the low-clearance narrow crevice between the upper ceiling stalactite blocks and floor.
- **Expected Behavior**:
  Player should either be prevented from entering by solid collision or slide through smoothly when crouching/moving.
- **Actual Behavior**:
  The player becomes permanently wedged inside the wall geometry. Horizontal and vertical velocities drop to zero, jumps fail, and only pressing "Retry" or restarting the level recovers the player.
- **Exact BUGTRIGGER Log Line**:
  ```text
  [BUGTRIGGER] 2A: {"description":"Player wedged in narrow ceiling gap at tile (55, 8)","position":[4400.0,640.0],"tile":[55,8]}
  ```

---

### Bug 2B: Enemy Floats Mid-Air Past Platform Edge
- **Bug ID**: `2B`
- **Tile Coordinates**: `(94, 4)` — Global Position: `(7520, 320)`
- **Steps to Reproduce**:
  1. Launch Map 2: `python run_map.py --map 2`.
  2. Advance to the high cave terrace at `x ≈ 7200..7520`.
  3. Observe `FloatingEnemy` patrol toward the right edge of the raised platform at `x = 7520`.
- **Expected Behavior**:
  Enemy should either turn around at the cliff edge or succumb to gravity and fall to the cavern floor below.
- **Actual Behavior**:
  The enemy ignores ledge detection and gravity, walking straight off the cliff and floating horizontally through mid-air indefinitely.
- **Exact BUGTRIGGER Log Line**:
  ```text
  [BUGTRIGGER] 2B: {"description":"Enemy continued horizontal motion past platform edge without falling","enemy":"FloatingEnemy","position":{"x":7525.0,"y":320.0}}
  ```

