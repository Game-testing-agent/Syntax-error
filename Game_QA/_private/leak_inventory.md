# Leak Inventory

## Summary Counts by Kind

| Kind | Count |
| :--- | :--- |
| flag file | 39 |
| test file | 39 |
| guarded block | 108 |
| comment or label | 22 |
| autoload | 1 |
| telemetry field | 1 |
| other | 22 |

**Total Leak Sites Identified**: 232

## Telemetry Analysis
- `game_events.jsonl`: Zero flag names found in data/payload. However, 14 `bug_trigger` discrete events exist which include synthetic IDs (`bug_id: '1C'`, `bug_id: '2A'`, `bug_id: '2B'`). Telemetry will be preserved without alteration as mandated by Rule 0.2.
- `sample_game_events.jsonl`: Zero flag names and zero `bug_trigger` events.

## Detailed Inventory Table

| Location | Kind | Note |
| :--- | :--- | :--- |
| `telemetry:game_events.jsonl` | `telemetry field` | 14 'bug_trigger' events present with synthetic bug_id ('1C', '2A', '2B', etc.) |
| `real_src/Actors\Enemy.gd:6` | `guarded block` | Defect state variable or guard: @export var is_floating_bug: bool = false |
| `real_src/Actors\Enemy.gd:8` | `other` | Reference to has_triggered_floating in pipeline/doc/metadata: var has_triggered_floating: bool = false |
| `real_src/Actors\Enemy.gd:19` | `guarded block` | Conditional code guarded by flag: if BugFlags and BugFlags.map4_retry_retains_enemies: |
| `real_src/Actors\Enemy.gd:20` | `guarded block` | Conditional code guarded by flag: if BugFlags.retained_enemy_transforms.has(name): |
| `real_src/Actors\Enemy.gd:21` | `guarded block` | Conditional code guarded by flag: global_position = BugFlags.retained_enemy_transforms[name] |
| `real_src/Actors\Enemy.gd:36` | `guarded block` | Conditional code guarded by flag: if BugFlags and BugFlags.map2_floating_enemy and is_floating |
| `real_src/Actors\Enemy.gd:39` | `other` | Reference to has_triggered_floating in pipeline/doc/metadata: if not has_triggered_floating: |
| `real_src/Actors\Enemy.gd:40` | `other` | Reference to has_triggered_floating in pipeline/doc/metadata: has_triggered_floating = true |
| `real_src/Actors\Enemy.gd:71` | `comment or label` | Comment describing defect/benchmark: # TRICKY  1: Stomp Tunneling Miss on Fast Descent |
| `real_src/Actors\Player.gd:21` | `guarded block` | Defect state variable or guard: var is_wall_stuck: bool = false |
| `real_src/Actors\Player.gd:22` | `guarded block` | Defect state variable or guard: var is_stair_stuck: bool = false |
| `real_src/Actors\Player.gd:23` | `other` | Reference to stair_escape_count in pipeline/doc/metadata: var stair_escape_count: int = 0 |
| `real_src/Actors\Player.gd:25` | `guarded block` | Defect state variable or guard: var lava_timer: float = -1.0 |
| `real_src/Actors\Player.gd:82` | `guarded block` | Conditional code guarded by flag: if BugFlags and BugFlags.map1_enemy4_no_kill: |
| `real_src/Actors\Player.gd:108` | `guarded block` | Conditional code guarded by flag: if BugFlags and BugFlags.map4_delayed_lava_death: |
| `real_src/Actors\Player.gd:109` | `guarded block` | Defect state variable or guard: if lava_timer < 0.0: |
| `real_src/Actors\Player.gd:110` | `guarded block` | Defect state variable or guard: lava_timer = 3.0 |
| `real_src/Actors\Player.gd:121` | `guarded block` | Defect state variable or guard: if lava_timer > 0.0: |
| `real_src/Actors\Player.gd:122` | `guarded block` | Defect state variable or guard: lava_timer -= delta |
| `real_src/Actors\Player.gd:123` | `guarded block` | Defect state variable or guard: if lava_timer <= 0.0: |
| `real_src/Actors\Player.gd:124` | `guarded block` | Defect state variable or guard: lava_timer = -1.0 |
| `real_src/Actors\Player.gd:127` | `guarded block` | Conditional code guarded by flag: if BugFlags and BugFlags.map2_wall_stuck: |
| `real_src/Actors\Player.gd:128` | `guarded block` | Defect state variable or guard: if not is_wall_stuck and global_position.x >= 4360.0 and glo |
| `real_src/Actors\Player.gd:129` | `guarded block` | Defect state variable or guard: is_wall_stuck = true |
| `real_src/Actors\Player.gd:136` | `guarded block` | Defect state variable or guard: if is_wall_stuck: |
| `real_src/Actors\Player.gd:141` | `guarded block` | Conditional code guarded by flag: if BugFlags and BugFlags.map3_stair_stick: |
| `real_src/Actors\Player.gd:142` | `guarded block` | Defect state variable or guard: if not is_stair_stuck and is_on_floor() and global_position. |
| `real_src/Actors\Player.gd:143` | `guarded block` | Defect state variable or guard: is_stair_stuck = true |
| `real_src/Actors\Player.gd:144` | `other` | Reference to stair_escape_count in pipeline/doc/metadata: stair_escape_count = 0 |
| `real_src/Actors\Player.gd:151` | `guarded block` | Defect state variable or guard: if is_stair_stuck: |
| `real_src/Actors\Player.gd:153` | `other` | Reference to stair_escape_count in pipeline/doc/metadata: stair_escape_count += 1 |
| `real_src/Actors\Player.gd:154` | `other` | Reference to stair_escape_count in pipeline/doc/metadata: if stair_escape_count >= 3: |
| `real_src/Actors\Player.gd:155` | `guarded block` | Defect state variable or guard: is_stair_stuck = false |
| `real_src/Actors\Player.gd:156` | `guarded block` | Defect state variable or guard: if is_stair_stuck: |
| `real_src/Actors\Player.gd:246` | `guarded block` | Conditional code guarded by flag: if BugFlags and BugFlags.map1_floor_hole: |
| `real_src/Actors\Player.gd:264` | `guarded block` | Conditional code guarded by flag: if BugFlags and BugFlags.map3_tower_wall_jump and is_on_wall |
| `real_src/Actors\Player.gd:307` | `comment or label` | Comment describing defect/benchmark: # TRICKY  2: Wall-Friction Jump Dampening |
| `real_src/Autoload\GameLogger.gd:1007` | `comment or label` | Comment describing defect/benchmark: # Pause toggle / set |
| `real_src/Autoload\PlayerData.gd:11` | `guarded block` | Conditional code guarded by flag: var bug_milestone_score_tax: bool = true |
| `real_src/Autoload\PlayerData.gd:36` | `comment or label` | Comment describing defect/benchmark: # TRICKY  4: Milestone Score Regression |
| `real_src/Autoload\PlayerData.gd:40` | `guarded block` | Conditional code guarded by flag: if bug_milestone_score_tax and not is_resetting and old_scor |
| `real_src/Levels\Map2_UndergroundCaves.tscn:139` | `guarded block` | Defect state variable or guard: is_floating_bug = true |
| `real_src/Objects\Coin.gd:38` | `comment or label` | Comment describing defect/benchmark: # TRICKY  3: Sub-Frame Multi-Pickup Collision Race |
| `real_src/Objects\Coin.gd:63` | `guarded block` | Conditional code guarded by flag: if total_coins_collected == 7 and BugFlags and BugFlags.map1 |
| `real_src/Objects\Portal2D.gd:27` | `guarded block` | Conditional code guarded by flag: if BugFlags and BugFlags.map4_portal_second_touch and is_map |
| `real_src/Objects\Portal2D.gd:81` | `comment or label` | Comment describing defect/benchmark: # TRICKY  5: Airborne Portal Transition Fall-Through |
| `real_src/Tests\test_bugs.gd:8` | `test file` | Benchmark verification test script (BENCHMARK) |
| `real_src/Tests\test_bugs.gd:14` | `test file` | Benchmark verification test script (bug_flags) |
| `real_src/Tests\test_bugs.gd:18` | `test file` | Benchmark verification test script (bug_flags) |
| `real_src/Tests\test_bugs.gd:39` | `test file` | Benchmark verification test script (bug_flags) |
| `real_src/Tests\test_bugs.gd:83` | `test file` | Benchmark verification test script (bug_flags) |
| `real_src/Tests\test_bugs.gd:90` | `test file` | Benchmark verification test script (bug_flags) |
| `real_src/Tests\test_bugs.gd:91` | `test file` | Benchmark verification test script (bug_flags) |
| `real_src/Tests\test_fault_injection.gd:3` | `test file` | Benchmark verification test script (Injection) |
| `real_src/Tests\test_fault_injection.gd:5` | `test file` | Benchmark verification test script (test_fault_injection) |
| `real_src/Tests\test_fault_injection.gd:13` | `test file` | Benchmark verification test script (INJECTION) |
| `real_src/Tests\test_fault_injection.gd:165` | `test file` | Benchmark verification test script (INJECTION) |
| `real_src/Tests\test_fault_injection.gd:171` | `test file` | Benchmark verification test script (INJECTION) |
| `real_src/Tests\test_fault_injection.gd:174` | `test file` | Benchmark verification test script (INJECTION) |
| `real_src/UserInterface\RetryButton.gd:12` | `guarded block` | Conditional code guarded by flag: if BugFlags and BugFlags.map4_retry_retains_enemies: |
| `real_src/UserInterface\RetryButton.gd:14` | `guarded block` | Conditional code guarded by flag: BugFlags.retained_enemy_transforms.clear() |
| `real_src/UserInterface\RetryButton.gd:17` | `guarded block` | Conditional code guarded by flag: BugFlags.retained_enemy_transforms[e.name] = e.global_positi |
| `real_src/Utils\BugFlags.gd:3` | `flag file` | Definition/declaration of flag registry (toggle) |
| `real_src/Utils\BugFlags.gd:7` | `flag file` | Definition/declaration of flag registry (map1_enemy4_no_kill) |
| `real_src/Utils\BugFlags.gd:8` | `flag file` | Definition/declaration of flag registry (map1_floor_hole) |
| `real_src/Utils\BugFlags.gd:9` | `flag file` | Definition/declaration of flag registry (map1_seventh_coin_no_score) |
| `real_src/Utils\BugFlags.gd:12` | `flag file` | Definition/declaration of flag registry (map2_wall_stuck) |
| `real_src/Utils\BugFlags.gd:13` | `flag file` | Definition/declaration of flag registry (map2_floating_enemy) |
| `real_src/Utils\BugFlags.gd:16` | `flag file` | Definition/declaration of flag registry (map3_stair_stick) |
| `real_src/Utils\BugFlags.gd:17` | `flag file` | Definition/declaration of flag registry (map3_fourth_enemy_unstompable) |
| `real_src/Utils\BugFlags.gd:18` | `flag file` | Definition/declaration of flag registry (map3_tower_wall_jump) |
| `real_src/Utils\BugFlags.gd:21` | `flag file` | Definition/declaration of flag registry (map4_delayed_lava_death) |
| `real_src/Utils\BugFlags.gd:22` | `flag file` | Definition/declaration of flag registry (map4_portal_second_touch) |
| `real_src/Utils\BugFlags.gd:23` | `flag file` | Definition/declaration of flag registry (map4_retry_retains_enemies) |
| `real_src/Utils\BugFlags.gd:26` | `flag file` | Definition/declaration of flag registry (retained_enemy_transforms) |
| `real_src/Utils\MapRunner.gd:3` | `comment or label` | Comment describing defect/benchmark: # MapRunner.gd — Headless & CLI dispatcher for QA benchmark  |
| `real_src/project.godot:22` | `autoload` | Autoload singleton registration for BugFlags |
| `game_src/Actors\Enemy.gd:6` | `guarded block` | Defect state variable or guard: @export var is_floating_bug: bool = false |
| `game_src/Actors\Enemy.gd:8` | `other` | Reference to has_triggered_floating in pipeline/doc/metadata: var has_triggered_floating: bool = false |
| `game_src/Actors\Enemy.gd:19` | `guarded block` | Conditional code guarded by flag: if BugFlags and BugFlags.map4_retry_retains_enemies: |
| `game_src/Actors\Enemy.gd:20` | `guarded block` | Conditional code guarded by flag: if BugFlags.retained_enemy_transforms.has(name): |
| `game_src/Actors\Enemy.gd:21` | `guarded block` | Conditional code guarded by flag: global_position = BugFlags.retained_enemy_transforms[name] |
| `game_src/Actors\Enemy.gd:36` | `guarded block` | Conditional code guarded by flag: if BugFlags and BugFlags.map2_floating_enemy and is_floating |
| `game_src/Actors\Enemy.gd:39` | `other` | Reference to has_triggered_floating in pipeline/doc/metadata: if not has_triggered_floating: |
| `game_src/Actors\Enemy.gd:40` | `other` | Reference to has_triggered_floating in pipeline/doc/metadata: has_triggered_floating = true |
| `game_src/Actors\Enemy.gd:71` | `comment or label` | Comment describing defect/benchmark: # TRICKY  1: Stomp Tunneling Miss on Fast Descent |
| `game_src/Actors\Player.gd:21` | `guarded block` | Defect state variable or guard: var is_wall_stuck: bool = false |
| `game_src/Actors\Player.gd:22` | `guarded block` | Defect state variable or guard: var is_stair_stuck: bool = false |
| `game_src/Actors\Player.gd:23` | `other` | Reference to stair_escape_count in pipeline/doc/metadata: var stair_escape_count: int = 0 |
| `game_src/Actors\Player.gd:25` | `guarded block` | Defect state variable or guard: var lava_timer: float = -1.0 |
| `game_src/Actors\Player.gd:82` | `guarded block` | Conditional code guarded by flag: if BugFlags and BugFlags.map1_enemy4_no_kill: |
| `game_src/Actors\Player.gd:108` | `guarded block` | Conditional code guarded by flag: if BugFlags and BugFlags.map4_delayed_lava_death: |
| `game_src/Actors\Player.gd:109` | `guarded block` | Defect state variable or guard: if lava_timer < 0.0: |
| `game_src/Actors\Player.gd:110` | `guarded block` | Defect state variable or guard: lava_timer = 3.0 |
| `game_src/Actors\Player.gd:121` | `guarded block` | Defect state variable or guard: if lava_timer > 0.0: |
| `game_src/Actors\Player.gd:122` | `guarded block` | Defect state variable or guard: lava_timer -= delta |
| `game_src/Actors\Player.gd:123` | `guarded block` | Defect state variable or guard: if lava_timer <= 0.0: |
| `game_src/Actors\Player.gd:124` | `guarded block` | Defect state variable or guard: lava_timer = -1.0 |
| `game_src/Actors\Player.gd:127` | `guarded block` | Conditional code guarded by flag: if BugFlags and BugFlags.map2_wall_stuck: |
| `game_src/Actors\Player.gd:128` | `guarded block` | Defect state variable or guard: if not is_wall_stuck and global_position.x >= 4360.0 and glo |
| `game_src/Actors\Player.gd:129` | `guarded block` | Defect state variable or guard: is_wall_stuck = true |
| `game_src/Actors\Player.gd:136` | `guarded block` | Defect state variable or guard: if is_wall_stuck: |
| `game_src/Actors\Player.gd:141` | `guarded block` | Conditional code guarded by flag: if BugFlags and BugFlags.map3_stair_stick: |
| `game_src/Actors\Player.gd:142` | `guarded block` | Defect state variable or guard: if not is_stair_stuck and is_on_floor() and global_position. |
| `game_src/Actors\Player.gd:143` | `guarded block` | Defect state variable or guard: is_stair_stuck = true |
| `game_src/Actors\Player.gd:144` | `other` | Reference to stair_escape_count in pipeline/doc/metadata: stair_escape_count = 0 |
| `game_src/Actors\Player.gd:151` | `guarded block` | Defect state variable or guard: if is_stair_stuck: |
| `game_src/Actors\Player.gd:153` | `other` | Reference to stair_escape_count in pipeline/doc/metadata: stair_escape_count += 1 |
| `game_src/Actors\Player.gd:154` | `other` | Reference to stair_escape_count in pipeline/doc/metadata: if stair_escape_count >= 3: |
| `game_src/Actors\Player.gd:155` | `guarded block` | Defect state variable or guard: is_stair_stuck = false |
| `game_src/Actors\Player.gd:156` | `guarded block` | Defect state variable or guard: if is_stair_stuck: |
| `game_src/Actors\Player.gd:246` | `guarded block` | Conditional code guarded by flag: if BugFlags and BugFlags.map1_floor_hole: |
| `game_src/Actors\Player.gd:264` | `guarded block` | Conditional code guarded by flag: if BugFlags and BugFlags.map3_tower_wall_jump and is_on_wall |
| `game_src/Actors\Player.gd:307` | `comment or label` | Comment describing defect/benchmark: # TRICKY  2: Wall-Friction Jump Dampening |
| `game_src/Autoload\GameLogger.gd:1013` | `comment or label` | Comment describing defect/benchmark: # Pause toggle / set |
| `game_src/Autoload\PlayerData.gd:11` | `guarded block` | Conditional code guarded by flag: var bug_milestone_score_tax: bool = true |
| `game_src/Autoload\PlayerData.gd:36` | `comment or label` | Comment describing defect/benchmark: # TRICKY  4: Milestone Score Regression |
| `game_src/Autoload\PlayerData.gd:40` | `guarded block` | Conditional code guarded by flag: if bug_milestone_score_tax and not is_resetting and old_scor |
| `game_src/Levels\Map2_UndergroundCaves.tscn:139` | `guarded block` | Defect state variable or guard: is_floating_bug = true |
| `game_src/Objects\Coin.gd:38` | `comment or label` | Comment describing defect/benchmark: # TRICKY  3: Sub-Frame Multi-Pickup Collision Race |
| `game_src/Objects\Coin.gd:63` | `guarded block` | Conditional code guarded by flag: if total_coins_collected == 7 and BugFlags and BugFlags.map1 |
| `game_src/Objects\Portal2D.gd:27` | `guarded block` | Conditional code guarded by flag: if BugFlags and BugFlags.map4_portal_second_touch and is_map |
| `game_src/Objects\Portal2D.gd:81` | `comment or label` | Comment describing defect/benchmark: # TRICKY  5: Airborne Portal Transition Fall-Through |
| `game_src/Tests\test_bugs.gd:8` | `test file` | Benchmark verification test script (BENCHMARK) |
| `game_src/Tests\test_bugs.gd:14` | `test file` | Benchmark verification test script (bug_flags) |
| `game_src/Tests\test_bugs.gd:18` | `test file` | Benchmark verification test script (bug_flags) |
| `game_src/Tests\test_bugs.gd:39` | `test file` | Benchmark verification test script (bug_flags) |
| `game_src/Tests\test_bugs.gd:83` | `test file` | Benchmark verification test script (bug_flags) |
| `game_src/Tests\test_bugs.gd:90` | `test file` | Benchmark verification test script (bug_flags) |
| `game_src/Tests\test_bugs.gd:91` | `test file` | Benchmark verification test script (bug_flags) |
| `game_src/Tests\test_fault_injection.gd:3` | `test file` | Benchmark verification test script (Injection) |
| `game_src/Tests\test_fault_injection.gd:5` | `test file` | Benchmark verification test script (test_fault_injection) |
| `game_src/Tests\test_fault_injection.gd:13` | `test file` | Benchmark verification test script (INJECTION) |
| `game_src/Tests\test_fault_injection.gd:165` | `test file` | Benchmark verification test script (INJECTION) |
| `game_src/Tests\test_fault_injection.gd:171` | `test file` | Benchmark verification test script (INJECTION) |
| `game_src/Tests\test_fault_injection.gd:174` | `test file` | Benchmark verification test script (INJECTION) |
| `game_src/UserInterface\RetryButton.gd:12` | `guarded block` | Conditional code guarded by flag: if BugFlags and BugFlags.map4_retry_retains_enemies: |
| `game_src/UserInterface\RetryButton.gd:14` | `guarded block` | Conditional code guarded by flag: BugFlags.retained_enemy_transforms.clear() |
| `game_src/UserInterface\RetryButton.gd:17` | `guarded block` | Conditional code guarded by flag: BugFlags.retained_enemy_transforms[e.name] = e.global_positi |
| `game_src/Utils\BugFlags.gd:3` | `flag file` | Definition/declaration of flag registry (toggle) |
| `game_src/Utils\BugFlags.gd:7` | `flag file` | Definition/declaration of flag registry (map1_enemy4_no_kill) |
| `game_src/Utils\BugFlags.gd:8` | `flag file` | Definition/declaration of flag registry (map1_floor_hole) |
| `game_src/Utils\BugFlags.gd:9` | `flag file` | Definition/declaration of flag registry (map1_seventh_coin_no_score) |
| `game_src/Utils\BugFlags.gd:12` | `flag file` | Definition/declaration of flag registry (map2_wall_stuck) |
| `game_src/Utils\BugFlags.gd:13` | `flag file` | Definition/declaration of flag registry (map2_floating_enemy) |
| `game_src/Utils\BugFlags.gd:16` | `flag file` | Definition/declaration of flag registry (map3_stair_stick) |
| `game_src/Utils\BugFlags.gd:17` | `flag file` | Definition/declaration of flag registry (map3_fourth_enemy_unstompable) |
| `game_src/Utils\BugFlags.gd:18` | `flag file` | Definition/declaration of flag registry (map3_tower_wall_jump) |
| `game_src/Utils\BugFlags.gd:21` | `flag file` | Definition/declaration of flag registry (map4_delayed_lava_death) |
| `game_src/Utils\BugFlags.gd:22` | `flag file` | Definition/declaration of flag registry (map4_portal_second_touch) |
| `game_src/Utils\BugFlags.gd:23` | `flag file` | Definition/declaration of flag registry (map4_retry_retains_enemies) |
| `game_src/Utils\BugFlags.gd:26` | `flag file` | Definition/declaration of flag registry (retained_enemy_transforms) |
| `game_src/Utils\MapRunner.gd:3` | `comment or label` | Comment describing defect/benchmark: # MapRunner.gd — Headless & CLI dispatcher for QA benchmark  |
| `report.py:70` | `other` | Reference to Benchmark in pipeline/doc/metadata: lines.append("### 🎯 Ground Truth Benchmark Score") |
| `game_src/Actors/Enemy.gd:6` | `guarded block` | Defect state variable or guard: @export var is_floating_bug: bool = false |
| `game_src/Actors/Enemy.gd:8` | `other` | Reference to has_triggered_floating in pipeline/doc/metadata: var has_triggered_floating: bool = false |
| `game_src/Actors/Enemy.gd:19` | `guarded block` | Conditional code guarded by flag: if BugFlags and BugFlags.map4_retry_retains_enemies: |
| `game_src/Actors/Enemy.gd:20` | `guarded block` | Conditional code guarded by flag: if BugFlags.retained_enemy_transforms.has(name): |
| `game_src/Actors/Enemy.gd:21` | `guarded block` | Conditional code guarded by flag: global_position = BugFlags.retained_enemy_transforms[name] |
| `game_src/Actors/Enemy.gd:36` | `guarded block` | Conditional code guarded by flag: if BugFlags and BugFlags.map2_floating_enemy and is_floating |
| `game_src/Actors/Enemy.gd:39` | `other` | Reference to has_triggered_floating in pipeline/doc/metadata: if not has_triggered_floating: |
| `game_src/Actors/Enemy.gd:40` | `other` | Reference to has_triggered_floating in pipeline/doc/metadata: has_triggered_floating = true |
| `game_src/Actors/Enemy.gd:71` | `comment or label` | Comment describing defect/benchmark: # TRICKY  1: Stomp Tunneling Miss on Fast Descent |
| `game_src/Actors/Player.gd:21` | `guarded block` | Defect state variable or guard: var is_wall_stuck: bool = false |
| `game_src/Actors/Player.gd:22` | `guarded block` | Defect state variable or guard: var is_stair_stuck: bool = false |
| `game_src/Actors/Player.gd:23` | `other` | Reference to stair_escape_count in pipeline/doc/metadata: var stair_escape_count: int = 0 |
| `game_src/Actors/Player.gd:25` | `guarded block` | Defect state variable or guard: var lava_timer: float = -1.0 |
| `game_src/Actors/Player.gd:82` | `guarded block` | Conditional code guarded by flag: if BugFlags and BugFlags.map1_enemy4_no_kill: |
| `game_src/Actors/Player.gd:108` | `guarded block` | Conditional code guarded by flag: if BugFlags and BugFlags.map4_delayed_lava_death: |
| `game_src/Actors/Player.gd:109` | `guarded block` | Defect state variable or guard: if lava_timer < 0.0: |
| `game_src/Actors/Player.gd:110` | `guarded block` | Defect state variable or guard: lava_timer = 3.0 |
| `game_src/Actors/Player.gd:121` | `guarded block` | Defect state variable or guard: if lava_timer > 0.0: |
| `game_src/Actors/Player.gd:122` | `guarded block` | Defect state variable or guard: lava_timer -= delta |
| `game_src/Actors/Player.gd:123` | `guarded block` | Defect state variable or guard: if lava_timer <= 0.0: |
| `game_src/Actors/Player.gd:124` | `guarded block` | Defect state variable or guard: lava_timer = -1.0 |
| `game_src/Actors/Player.gd:127` | `guarded block` | Conditional code guarded by flag: if BugFlags and BugFlags.map2_wall_stuck: |
| `game_src/Actors/Player.gd:128` | `guarded block` | Defect state variable or guard: if not is_wall_stuck and global_position.x >= 4360.0 and glo |
| `game_src/Actors/Player.gd:129` | `guarded block` | Defect state variable or guard: is_wall_stuck = true |
| `game_src/Actors/Player.gd:136` | `guarded block` | Defect state variable or guard: if is_wall_stuck: |
| `game_src/Actors/Player.gd:141` | `guarded block` | Conditional code guarded by flag: if BugFlags and BugFlags.map3_stair_stick: |
| `game_src/Actors/Player.gd:142` | `guarded block` | Defect state variable or guard: if not is_stair_stuck and is_on_floor() and global_position. |
| `game_src/Actors/Player.gd:143` | `guarded block` | Defect state variable or guard: is_stair_stuck = true |
| `game_src/Actors/Player.gd:144` | `other` | Reference to stair_escape_count in pipeline/doc/metadata: stair_escape_count = 0 |
| `game_src/Actors/Player.gd:151` | `guarded block` | Defect state variable or guard: if is_stair_stuck: |
| `game_src/Actors/Player.gd:153` | `other` | Reference to stair_escape_count in pipeline/doc/metadata: stair_escape_count += 1 |
| `game_src/Actors/Player.gd:154` | `other` | Reference to stair_escape_count in pipeline/doc/metadata: if stair_escape_count >= 3: |
| `game_src/Actors/Player.gd:155` | `guarded block` | Defect state variable or guard: is_stair_stuck = false |
| `game_src/Actors/Player.gd:156` | `guarded block` | Defect state variable or guard: if is_stair_stuck: |
| `game_src/Actors/Player.gd:246` | `guarded block` | Conditional code guarded by flag: if BugFlags and BugFlags.map1_floor_hole: |
| `game_src/Actors/Player.gd:264` | `guarded block` | Conditional code guarded by flag: if BugFlags and BugFlags.map3_tower_wall_jump and is_on_wall |
| `game_src/Actors/Player.gd:307` | `comment or label` | Comment describing defect/benchmark: # TRICKY  2: Wall-Friction Jump Dampening |
| `game_src/Autoload/GameLogger.gd:1013` | `comment or label` | Comment describing defect/benchmark: # Pause toggle / set |
| `game_src/Autoload/PlayerData.gd:11` | `guarded block` | Conditional code guarded by flag: var bug_milestone_score_tax: bool = true |
| `game_src/Autoload/PlayerData.gd:36` | `comment or label` | Comment describing defect/benchmark: # TRICKY  4: Milestone Score Regression |
| `game_src/Autoload/PlayerData.gd:40` | `guarded block` | Conditional code guarded by flag: if bug_milestone_score_tax and not is_resetting and old_scor |
| `game_src/Levels/Map2_UndergroundCaves.tscn:139` | `guarded block` | Defect state variable or guard: is_floating_bug = true |
| `game_src/Objects/Coin.gd:38` | `comment or label` | Comment describing defect/benchmark: # TRICKY  3: Sub-Frame Multi-Pickup Collision Race |
| `game_src/Objects/Coin.gd:63` | `guarded block` | Conditional code guarded by flag: if total_coins_collected == 7 and BugFlags and BugFlags.map1 |
| `game_src/Objects/Portal2D.gd:27` | `guarded block` | Conditional code guarded by flag: if BugFlags and BugFlags.map4_portal_second_touch and is_map |
| `game_src/Objects/Portal2D.gd:81` | `comment or label` | Comment describing defect/benchmark: # TRICKY  5: Airborne Portal Transition Fall-Through |
| `game_src/Tests/test_bugs.gd:8` | `test file` | Benchmark verification test script (BENCHMARK) |
| `game_src/Tests/test_bugs.gd:14` | `test file` | Benchmark verification test script (bug_flags) |
| `game_src/Tests/test_bugs.gd:18` | `test file` | Benchmark verification test script (bug_flags) |
| `game_src/Tests/test_bugs.gd:39` | `test file` | Benchmark verification test script (bug_flags) |
| `game_src/Tests/test_bugs.gd:83` | `test file` | Benchmark verification test script (bug_flags) |
| `game_src/Tests/test_bugs.gd:90` | `test file` | Benchmark verification test script (bug_flags) |
| `game_src/Tests/test_bugs.gd:91` | `test file` | Benchmark verification test script (bug_flags) |
| `game_src/Tests/test_fault_injection.gd:3` | `test file` | Benchmark verification test script (Injection) |
| `game_src/Tests/test_fault_injection.gd:5` | `test file` | Benchmark verification test script (test_fault_injection) |
| `game_src/Tests/test_fault_injection.gd:13` | `test file` | Benchmark verification test script (INJECTION) |
| `game_src/Tests/test_fault_injection.gd:165` | `test file` | Benchmark verification test script (INJECTION) |
| `game_src/Tests/test_fault_injection.gd:171` | `test file` | Benchmark verification test script (INJECTION) |
| `game_src/Tests/test_fault_injection.gd:174` | `test file` | Benchmark verification test script (INJECTION) |
| `game_src/UserInterface/RetryButton.gd:12` | `guarded block` | Conditional code guarded by flag: if BugFlags and BugFlags.map4_retry_retains_enemies: |
| `game_src/UserInterface/RetryButton.gd:14` | `guarded block` | Conditional code guarded by flag: BugFlags.retained_enemy_transforms.clear() |
| `game_src/UserInterface/RetryButton.gd:17` | `guarded block` | Conditional code guarded by flag: BugFlags.retained_enemy_transforms[e.name] = e.global_positi |
| `game_src/Utils/BugFlags.gd:3` | `flag file` | Definition/declaration of flag registry (toggle) |
| `game_src/Utils/BugFlags.gd:7` | `flag file` | Definition/declaration of flag registry (map1_enemy4_no_kill) |
| `game_src/Utils/BugFlags.gd:8` | `flag file` | Definition/declaration of flag registry (map1_floor_hole) |
| `game_src/Utils/BugFlags.gd:9` | `flag file` | Definition/declaration of flag registry (map1_seventh_coin_no_score) |
| `game_src/Utils/BugFlags.gd:12` | `flag file` | Definition/declaration of flag registry (map2_wall_stuck) |
| `game_src/Utils/BugFlags.gd:13` | `flag file` | Definition/declaration of flag registry (map2_floating_enemy) |
| `game_src/Utils/BugFlags.gd:16` | `flag file` | Definition/declaration of flag registry (map3_stair_stick) |
| `game_src/Utils/BugFlags.gd:17` | `flag file` | Definition/declaration of flag registry (map3_fourth_enemy_unstompable) |
| `game_src/Utils/BugFlags.gd:18` | `flag file` | Definition/declaration of flag registry (map3_tower_wall_jump) |
| `game_src/Utils/BugFlags.gd:21` | `flag file` | Definition/declaration of flag registry (map4_delayed_lava_death) |
| `game_src/Utils/BugFlags.gd:22` | `flag file` | Definition/declaration of flag registry (map4_portal_second_touch) |
| `game_src/Utils/BugFlags.gd:23` | `flag file` | Definition/declaration of flag registry (map4_retry_retains_enemies) |
| `game_src/Utils/BugFlags.gd:26` | `flag file` | Definition/declaration of flag registry (retained_enemy_transforms) |
| `game_src/Utils/MapRunner.gd:3` | `comment or label` | Comment describing defect/benchmark: # MapRunner.gd — Headless & CLI dispatcher for QA benchmark  |
| `.agents/skills/game-qa/references/gdscript_mechanics.md:1` | `comment or label` | Comment describing defect/benchmark: # GDScript Mechanics & Known Bug Signatures |