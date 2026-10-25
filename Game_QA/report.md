# 🎮 Game_QA Post-Run Evaluation Report

> Automated Dual-Path QA Analysis for Godot 2D Platformer (`Syntax-error`)

## 📊 Executive Summary

- **Sessions Analyzed**: `1`
- **Total Findings**: `21`
- **Path 1 (Deterministic Invariants & Engine Anomalies)**: `0`
- **Path 2 (LLM / Semantic Window Review)**: `21`

| Severity | Count |
| :--- | :--- |
| 🔴 **Critical** | 9 |
| 🟠 **High** | 8 |
| 🟡 **Medium** | 4 |
| 🔵 **Low** | 0 |

---

## 🕹️ Session: `session_1792887612_53424`
*(Events logged: 764 | Telemetry snapshots: 32)*

### 🎯 Ground Truth Benchmark Score
- **Expected Bugs Caught**: `7 / 7`
- **False Positives**: `0`

| Expected Anomaly / Bug | Caught? | Detection Path | Target |
| :--- | :--- | :--- | :--- |
| `Enemy4 collision does not kill player (1A)` | ✅ YES | `path2` | `path2` |
| `Gap in level floor causing endless void fall (1B)` | ✅ YES | `path2` | `path2` |
| `Collecting 7th coin gives 0 points (1C)` | ✅ YES | `path2` | `path2` |
| `Player wedged in narrow ceiling block gap / stuck in wall (2A)` | ✅ YES | `path2` | `path2` |
| `Enemy patrols off platform and floats in air (2B)` | ✅ YES | `path2` | `path2` |
| `Player stuck on staircase edge until left taps (3A)` | ✅ YES | `path2` | `path2` |
| `Goal portal missing next_scene property (4B)` | ✅ YES | `path2` | `path2` |

### 🔍 Detailed Findings

#### 1. [CRITICAL] Player wedged and permanently stuck in wall geometry (Bug 2A)
- **Detection Mechanism**: `Path 2 (Semantic / LLM)` (🤖 Auto-Verified)
- **Confidence**: `0.99`
- **Evidence Frame(s)**: `[1520, 1535, 1540, 1585]`
- **Suspected Component**: `Player.gd:L135-L148 (_physics_process / map2_wall_stuck)`
- **Details**:
  > At frame 1540, the player character traverses into narrow wall and ceiling geometry at coordinates (4400.0, 640.0) / Tile (55, 8) in Map 2 (Underground Caves). In Player.gd:L135-L148, map2_wall_stuck activates and sets is_wall_stuck to true, forcing velocity = Vector2.ZERO unconditionally every physics frame. The collision geometry lacks pushback or slide resolution, permanently trapping the player inside the wall with zero ability to walk or jump. Emits [BUGTRIGGER] 2A.

#### 2. [CRITICAL] Enemy collision fails to inflict lethal damage on player (Bug 1A)
- **Detection Mechanism**: `Path 2 (Semantic / LLM)` (🤖 Auto-Verified)
- **Confidence**: `0.98`
- **Evidence Frame(s)**: `[870, 892, 915, 940]`
- **Suspected Component**: `Player.gd:L79-L94 (_on_EnemyDetector_body_entered)`
- **Details**:
  > At frame 892, the player collides with Enemy4 at coordinates (3040.0, 560.0) / Tile (38, 7) in Map 1. In Player.gd:L79-L94, the body_entered signal evaluates BugFlags.map1_enemy4_no_kill and finds can_kill_player=false on Enemy4 (Enemy.gd:L17). Instead of logging enemy_contact_death and calling die(), the handler early-returns and logs [BUGTRIGGER] 1A. The player safely overlaps and walks straight through the enemy without taking damage, violating core hazard fatality rules.

#### 3. [CRITICAL] Portal2D next_scene is null or empty (missing_expected_object)
- **Detection Mechanism**: `Path 2 (Semantic / LLM)` (🤖 Auto-Verified)
- **Confidence**: `0.95`
- **Evidence Frame(s)**: `[2166, 2321]`
- **Suspected Component**: `Portal2D.gd:L56-L67 (teleport)`
- **Details**:
  > At frame 2321, the player touches Portal2D at (17104.99, 486.31) triggering portal_entered, but next_scene is null, logging missing_expected_object and portal_target_missing. Portal2D.gd:L56-L67 (teleport) sets is_teleporting to true and early returns, blocking scene change and preventing level completion. This violates the lifecycle and progression contract that reaching the goal portal must advance to the next level.

#### 4. [CRITICAL] Exit portal missing next_scene property, blocking level progression
- **Detection Mechanism**: `Path 2 (Semantic / LLM)` (🤖 Auto-Verified)
- **Confidence**: `0.95`
- **Evidence Frame(s)**: `[4023, 4026, 4036]`
- **Suspected Component**: `Objects/Portal2D.gd:L56-L67`
- **Details**:
  > At frame 4023, the player touches Portal2D at the end of Map3, but Portal2D.gd:L56 aborts transition because next_scene is null, emitting missing_expected_object. In Map3_SkyCastle.tscn:L40, Portal2D is instanced without a next_scene assignment, violating the progression contract and soft-locking completion.

#### 5. [CRITICAL] Player falling below level boundary does not trigger death (player_out_of_bounds)
- **Detection Mechanism**: `Path 2 (Semantic / LLM)` (🤖 Auto-Verified)
- **Confidence**: `0.95`
- **Evidence Frame(s)**: `[2502, 2542, 3385]`
- **Suspected Component**: `Player.gd:L254-L270 (_physics_process)`
- **Details**:
  > At frame 2502, the player falls below OUT_OF_BOUNDS_Y (1400.0) reaching y=1412.43, logging player_out_of_bounds anomaly. Traced to Player.gd:L254-L270 where detection logs an anomaly but never calls die(), causing the player to fall indefinitely through the void past y=320,000 without dying or respawning. This violates the physical and design invariant that falling out of the world must be fatal.

#### 6. [CRITICAL] Player Out of Bounds Void Fall Without Death
- **Detection Mechanism**: `Path 2 (Semantic / LLM)` (🤖 Auto-Verified)
- **Confidence**: `0.95`
- **Evidence Frame(s)**: `[1820, 1821, 1824, 1827, 2557]`
- **Suspected Component**: `Player.gd:L214-L222 (_physics_process)`
- **Details**:
  > At frame 1820, player exceeded the level threshold (OUT_OF_BOUNDS_Y = 1400.0) reaching Y=1412.4, triggering player_out_of_bounds anomaly. In Player.gd:L214-L222, the anomaly is logged but die() is never called, causing the player to fall continuously past Y=290,889 without death or respawn.

#### 7. [CRITICAL] Exit portal missing next_scene property, blocking level progression
- **Detection Mechanism**: `Path 2 (Semantic / LLM)` (🤖 Auto-Verified)
- **Confidence**: `0.95`
- **Evidence Frame(s)**: `[4023, 4026, 4036]`
- **Suspected Component**: `Objects/Portal2D.gd:L56-L67`
- **Details**:
  > At frame 4023, the player touches Portal2D at the end of Map3, but Portal2D.gd:L56 aborts transition because next_scene is null, emitting missing_expected_object. In Map3_SkyCastle.tscn:L40, Portal2D is instanced without a next_scene assignment, violating the progression contract and soft-locking completion.

#### 8. [CRITICAL] Player Out of Bounds Void Fall Without Death
- **Detection Mechanism**: `Path 2 (Semantic / LLM)` (🤖 Auto-Verified)
- **Confidence**: `0.95`
- **Evidence Frame(s)**: `[826, 827, 830, 1150, 1190]`
- **Suspected Component**: `Player.gd:L214-L223 (_physics_process)`
- **Details**:
  > At frame 826, player exceeded boundary (OUT_OF_BOUNDS_Y = 1400.0) reaching Y=1431.17, triggering player_out_of_bounds anomaly. In Player.gd:L214-L223 (_physics_process), the anomaly is logged but die() is never invoked, causing the player to fall continuously across window w03 from Y=1472.01 past Y=70,000 without death or respawn, resulting in an unrecoverable soft-lock.

#### 9. [CRITICAL] Player Out of Bounds (Void Fall Without Death)
- **Detection Mechanism**: `Path 2 (Semantic / LLM)` (⚠️ Human Review Recommended)
- **Confidence**: `0.75`
- **Evidence Frame(s)**: `[2677, 2678, 2679, 2680, 2681, 2976, 2977, 2978, 2979, 2980]`
- **Suspected Component**: `Player.gd (_physics_process: boundary_check)`
- **Details**:
  > Player exceeded level boundary threshold (OUT_OF_BOUNDS_Y = 1400.0), reaching Y=126494.8 across frames 2677–7476 without dying, resetting, or respawning. Violates death pit invariant.

#### 10. [HIGH] Player pinned to zero velocity on stairs in Map3
- **Detection Mechanism**: `Path 2 (Semantic / LLM)` (🤖 Auto-Verified)
- **Confidence**: `0.95`
- **Evidence Frame(s)**: `[2130, 2140, 2142, 2162, 2177, 2224, 2280]`
- **Suspected Component**: `Actors/Player.gd:L149-L167`
- **Details**:
  > At frame 2130, the player lands on Map3 stairs at coordinates (5458, 560), setting is_stair_stuck in Player.gd:L150. Frame 2140 jump and frame 2142 right inputs produce zero velocity because Player.gd:L165 forces velocity to Vector2.ZERO until 3 rapid left inputs occur, violating the kinematics invariant.

#### 11. [HIGH] Score Decrements When Earning Points Above 500 Threshold
- **Detection Mechanism**: `Path 2 (Semantic / LLM)` (🤖 Auto-Verified)
- **Confidence**: `0.95`
- **Evidence Frame(s)**: `[417, 424, 613, 664, 702, 763, 834, 880, 1003, 1124, 1206, 1706]`
- **Suspected Component**: `PlayerData.gd:L33-L35 (set_score)`
- **Details**:
  > At frame 417, PlayerData.set_score dropped score from 500 to 490 (-10) after collecting a coin, triggering unexpected_score_change. Defect repeatedly manifested across window w02 at frames 613, 664, 702, and 763. Traced to PlayerData.gd:L33-L35 where gaining score when old_score >= 500 calculates final_score = old_score - 10, violating score monotonicity and core reward contracts.

#### 12. [HIGH] Seventh Coin Collection Suppresses Score Award
- **Detection Mechanism**: `Path 2 (Semantic / LLM)` (🤖 Auto-Verified)
- **Confidence**: `0.95`
- **Evidence Frame(s)**: `[469]`
- **Suspected Component**: `Coin.gd:L58-L63 (picked)`
- **Details**:
  > At frame 469, Coin7 (Coin8 in scene) was collected triggering coin_picked with score 100, but coin_score_awarded logged score_before: 490 and score_after: 490. Traced to Coin.gd:L58-L63 (picked) where total_coins_collected == 7 forcibly sets should_award_score = false, violating the design contract that collecting a collectible awards score.

#### 13. [HIGH] Seventh Coin Collection Suppresses Score Award
- **Detection Mechanism**: `Path 2 (Semantic / LLM)` (🤖 Auto-Verified)
- **Confidence**: `0.95`
- **Evidence Frame(s)**: `[934]`
- **Suspected Component**: `Coin.gd:L58-L59 (picked)`
- **Details**:
  > At frame 934, Coin11 was picked (total_coins_collected == 7) but PlayerData.score remained 570 despite coin_score_awarded logging a score gain of 100. In Coin.gd:L58-L59, should_award_score is explicitly disabled for the 7th coin, violating collectible reward contracts.

#### 14. [HIGH] Phantom Enemy Wall Reversal Freezes Patrol at Zero Velocity
- **Detection Mechanism**: `Path 2 (Semantic / LLM)` (🤖 Auto-Verified)
- **Confidence**: `0.90`
- **Evidence Frame(s)**: `[561, 597, 633, 653, 673, 690]`
- **Suspected Component**: `Enemy.gd:L44-L50 (_physics_process)`
- **Details**:
  > At frame 690, Enemy4 triggered enemy_reversed_at_wall with old_direction: 0.0 and new_direction: 0.0 at position (5059.96, 800.0) following rapid wall reversals (frames 561-673). In Enemy.gd, multiplying velocity.x (0.0) by -1.0 permanently stops patrol velocity, violating AI autonomy contracts.

#### 15. [HIGH] Semantic Anomaly: duplicate_pickup_attempt
- **Detection Mechanism**: `Path 2 (Semantic / LLM)` (🤖 Auto-Verified)
- **Confidence**: `0.85`
- **Evidence Frame(s)**: `[1091, 1408]`
- **Suspected Component**: `Coin.gd (_on_body_entered)`
- **Details**:
  > Duplicate overlap detected on already-collected coin at frame 1408 in Level02 following player retry. Violates idempotence contract C_PICKUP_IDEMPOTENT. Traced to Coin.gd (_on_body_entered) where collision monitoring remains active during the picked animation.

#### 16. [HIGH] Phantom Enemy Wall Reversal (Enemy Frozen)
- **Detection Mechanism**: `Path 2 (Semantic / LLM)` (⚠️ Human Review Recommended)
- **Confidence**: `0.75`
- **Evidence Frame(s)**: `[1260]`
- **Suspected Component**: `Enemy.gd (_physics_process: is_on_wall)`
- **Details**:
  > Enemy attempted wall reversal at frame 1260 but old_direction and new_direction were both 0.0, causing the enemy to freeze.

#### 17. [HIGH] Semantic Anomaly: unexpected_player_removal
- **Detection Mechanism**: `Path 2 (Semantic / LLM)` (⚠️ Human Review Recommended)
- **Confidence**: `0.75`
- **Evidence Frame(s)**: `[3385]`
- **Suspected Component**: `Player.gd (_exit_tree)`
- **Details**:
  > White-box audit verified 'unexpected_player_removal' at frame 3385. Expected: Player removal should occur on death or scene transition | Observed: Player exited scene tree without death flag or transition. Traced to logic in Player.gd (_exit_tree).

#### 18. [MEDIUM] Enemy floats in mid-air defying gravity (floating_enemy)
- **Detection Mechanism**: `Path 2 (Semantic / LLM)` (🤖 Auto-Verified)
- **Confidence**: `0.95`
- **Evidence Frame(s)**: `[896]`
- **Suspected Component**: `Enemy.gd:L36-L47 (_physics_process)`
- **Details**:
  > At frame 896, FloatingEnemy walks off the ledge at position (7200, 550) without falling, triggering bug_trigger 2B. In Enemy.gd:L36-L47, velocity.y is forcibly zeroed when is_floating_bug is active and the enemy is not on the floor, instead of applying gravity via super._physics_process. This violates the physical kinematic invariant that unsupported airborne entities must accelerate downward under gravity.

#### 19. [MEDIUM] Player immobilized on Map3 stairs due to velocity zeroing (stair_stick)
- **Detection Mechanism**: `Path 2 (Semantic / LLM)` (🤖 Auto-Verified)
- **Confidence**: `0.95`
- **Evidence Frame(s)**: `[806, 927, 993, 1028, 1057, 1089]`
- **Suspected Component**: `Player.gd:L150-L167 (_physics_process)`
- **Details**:
  > Between frames 806 and 1089, the player is trapped at stair coordinates [68, 7] (position x≈5426-5458, y≈559) with velocity forced to zero despite directional movement inputs. Traced to Player.gd:L150-L167, which clamps velocity to zero on Map3 within a hardcoded bounding box until multiple leftward inputs are registered. This violates the kinematic contract that unobstructed geometry must permit player movement.

#### 20. [MEDIUM] Duplicate Coin Pickup Attempt Due to Missing Collision Disabling
- **Detection Mechanism**: `Path 2 (Semantic / LLM)` (🤖 Auto-Verified)
- **Confidence**: `0.95`
- **Evidence Frame(s)**: `[923, 940, 947]`
- **Suspected Component**: `Coin.gd:L19-L35 (_on_body_entered)`
- **Details**:
  > At frame 940, Coin5 triggered duplicate_pickup_attempt anomaly when the player re-entered its collision area during its picked animation. Traced to Coin.gd:L19-L35 (_on_body_entered) where picked() does not disable CollisionShape2D or disconnect body_entered, violating uniqueness and idempotent collectible pickup invariants.

#### 21. [MEDIUM] Duplicate body_entered overlap on collected coin (duplicate_pickup_attempt)
- **Detection Mechanism**: `Path 2 (Semantic / LLM)` (🤖 Auto-Verified)
- **Confidence**: `0.92`
- **Evidence Frame(s)**: `[762, 776, 786]`
- **Suspected Component**: `Coin.gd:L21-L36 (_on_body_entered)`
- **Details**:
  > At frame 776, coin_overlap_started fired for Coin11 at (5440, 500) while jumping, triggering duplicate_pickup_attempt after Coin11 was already collected at frame 762. In Coin.tscn, the 'picked' animation sets monitorable to false instead of monitoring, leaving collision detection active during the 0.4s despawn animation. This violates the interaction invariant that collected items must not accept further collision triggers.

---
