# Source Sanitization Rules (Proposal)

## 1. Files & Configurations to Drop in `game_src/`
- **Flag Registry File**: Drop `src/Utils/BugFlags.gd`.
- **Benchmark Test Files & Scenes**:
  - Drop `src/Tests/test_bugs.gd` (benchmark verification checks).
  - Drop `src/Tests/test_fault_injection.gd` (fault injection suite).
  - (Keep `test_gameplay_flow.gd` and `test_logger_suite.gd` if they represent standard runtime test suites, unless requested to drop all test scripts).
- **Project Configuration (`project.godot`)**:
  - Remove autoload entry line: `BugFlags="*res://src/Utils/BugFlags.gd"`.
- **Debug UI**:
  - Drop any debug UI controls dedicated to toggle inspection (none exist in the current UI scenes).

## 2. Guard Substitution Rules (Preserving Executed Behavior)
For each guard in gameplay scripts referencing a flag:
- **If the confirmed runtime flag is `true`**:
  - The guarded behavior was active during the run.
  - Simplify condition by removing `BugFlags and BugFlags.<flag_name>`.
  - If the flag was the sole condition of an `if` block, unwrap the block body so the logic executes unconditionally.
  - If compounded (e.g., `if BugFlags and BugFlags.map2_floating_enemy and is_floating_bug:`), reduce to `if is_floating_bug:`.
- **If the confirmed runtime flag is `false`**:
  - The guarded branch was inactive during the run.
  - Remove the dead conditional branch entirely.
- **Specific Guard Sites Identified**:
  1. `src/Actors/Player.gd`:
     - Line 110: `BugFlags and BugFlags.map1_enemy4_no_kill`
     - Line 127: `BugFlags and BugFlags.map2_wall_stuck`
     - Line 141: `BugFlags and BugFlags.map3_stair_stick`
     - Line 162: `BugFlags and BugFlags.map3_tower_wall_jump`
     - Line 275: `BugFlags and BugFlags.map4_delayed_lava_death`
  2. `src/Actors/Enemy.gd`:
     - Line 20: `BugFlags.retained_enemy_transforms`
     - Line 36: `BugFlags and BugFlags.map2_floating_enemy`
     - Line 74: `BugFlags and BugFlags.map3_fourth_enemy_unstompable`
  3. `src/Objects/Coin.gd`:
     - Line 63: `BugFlags and BugFlags.map1_seventh_coin_no_score`
  4. `src/Objects/Portal2D.gd`:
     - Line 41: `BugFlags and BugFlags.map4_portal_second_touch`
  5. `src/Autoload/PlayerData.gd`:
     - Line 40: `bug_milestone_score_tax` (substitute boolean value directly)
  6. `src/Levels/LevelTemplate.gd`:
     - Line 18: `BugFlags and BugFlags.map1_floor_hole`
     - Line 28: `BugFlags.retained_enemy_transforms`

## 3. Comment, String, and Identifier Sanitization
- **Comments to Strip**:
  - Remove all `# TRICKY <N>: ...` milestone defect annotations in `PlayerData.gd`.
  - Remove all explanatory comments in `BugFlags.gd` / `LevelTemplate.gd` describing intentional benchmark defects.
- **Identifiers to Keep vs Review**:
  - Keep ordinary gameplay identifiers: `lava_timer`, `velocity`, `is_wall_stuck`, `stair_escape_count`.
  - Review: `is_floating_bug`, `is_unstompable_bug` in `Enemy.gd` (these were exported boolean flags on enemy nodes in scenes). Propose renaming to clean domain terms (e.g. `is_floating`, `is_armored`) or evaluating if their removal/unconditional behavior is required once runtime values are confirmed.

## 4. Preservation Invariant
- No logic is fixed, altered, or reordered outside the exact guard reductions.
- Line numbers will shift deterministically, recorded in `_private/truth_line_map.md` during S8.

