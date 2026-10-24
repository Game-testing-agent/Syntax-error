# Adjudicated Candidates for session_1792862072_26412 (Phase B3)

## Candidate 1: Score Decrement Above 500 Threshold
1. **Contract**: Conservation & Monotonicity invariants; Design Contract: Score should only increase upon collecting items/defeating enemies, never decrement without intentional restart.
2. **Code Path**: `PlayerData.gd:L33-L35` in `set_score(new_score)`.
   ```gdscript
   if not is_resetting and old_score >= 500 and new_score > old_score:
       final_score = old_score - 10
   ```
3. **Window Check**:
   First observable in window `w01` at frame 424 (t=7.53s): picking Coin8 decreased score from 500 to 490 (-10).
   Repeated across 7 occurrences: frames 424 (Coin8), 834 (Enemy4), 880 (Coin10), 1003 (Coin12), 1124 (Coin14), 1206 (Enemy8), 1706 (Coin15). Each emitted an `unexpected_score_change` anomaly.
4. **Steelman**: No penalty hazard or death event was active. The score delta was consistently -10 for every pickup or kill above 500.
5. **Reproducibility**: 100% reproducible across 7 distinct events in 5 different windows whenever `score >= 500`.
6. **Decision**: `confirmed` (Verdict: bug, Severity: high, Confidence: 0.95, Level: L3).
   - Window: `w01`
   - Suspected Code: `PlayerData.gd:L33-L35 (set_score)`
   - Dedupe Key: `PlayerData.gd:L33:score_decrements_above_500`

---

## Candidate 2: Seventh Coin Picked Gives Zero Score
1. **Contract**: Design Contract & Code Contract (`Coin.gd:L4` `@export var score: int = 100`). Picking a coin must increment score by the coin's value.
2. **Code Path**: `Coin.gd:L58-L59` in `picked()`.
   ```gdscript
   var should_award_score = true
   if total_coins_collected == 7:
       should_award_score = false
   if should_award_score:
       PlayerData.score += score
   ```
3. **Window Check**:
   In window `w03` at frame 934 (t=16.03s), Coin #7 (`Coin11`) is picked (`coin_picked`).
   `coin_score_awarded` logs `score_gain: 100`, but `score_before: 570, score_after: 570`. PlayerData.score remained 570.
4. **Steelman**: Coin11 has no special scene properties or group overrides in `Map4_LavaFortress.tscn`. The suppression is directly hardcoded on `total_coins_collected == 7`.
5. **Reproducibility**: Deterministic on the 7th coin collected.
6. **Decision**: `confirmed` (Verdict: bug, Severity: high, Confidence: 0.95, Level: L3).
   - Window: `w03`
   - Suspected Code: `Coin.gd:L58-L59 (picked)`
   - Dedupe Key: `Coin.gd:L58:seventh_coin_suppresses_score`

---

## Candidate 3: Phantom Enemy Wall Reversal Freeze (Enemy4)
1. **Contract**: AI / Autonomy & Bounds invariants: Enemy patrol must maintain non-zero horizontal velocity and properly reflect direction upon encountering walls.
2. **Code Path**: `Enemy.gd:L44-L50` in `_physics_process(delta)`.
   ```gdscript
   if is_on_wall():
       var old_dir = sign(velocity.x)
       velocity.x *= -1.0
   ```
   When `velocity.x` is 0.0, `old_dir` is 0.0 and `velocity.x *= -1.0` remains 0.0, permanently freezing the enemy.
3. **Window Check**:
   In window `w02` at frame 690 (t=11.95s), Enemy4 triggered `enemy_reversed_at_wall` with `old_direction: 0.0` and `new_direction: 0.0` at position `(5059.96, 800.0)`. Enemy4 remained motionless until stomped at frame 834. Preceded by rapid ping-pong oscillation across frames 561–673.
4. **Steelman**: Enemy.gd lacks any idle state or timer; velocity was multiplied to 0.0 by arithmetic zero-propagation.
5. **Reproducibility**: Directly traced to code arithmetic in `Enemy.gd`.
6. **Decision**: `confirmed` (Verdict: bug, Severity: high, Confidence: 0.90, Level: L3).
   - Window: `w02`
   - Suspected Code: `Enemy.gd:L44-L50 (_physics_process)`
   - Dedupe Key: `Enemy.gd:L44:phantom_wall_reversal_freeze`

---

## Candidate 4: Player Out of Bounds Void Fall Without Death
1. **Contract**: Bounds & Liveness invariants; Design Contract: Falling below `OUT_OF_BOUNDS_Y = 1400.0` is a fatal pit hazard that must invoke `die()`, increment deaths, and reset/respawn.
2. **Code Path**: `Player.gd:L214-L222` in `_physics_process(delta)`.
   ```gdscript
   if global_position.y > OUT_OF_BOUNDS_Y and not out_of_bounds_logged and GameLogger:
       out_of_bounds_logged = true
       GameLogger.log_anomaly("player_out_of_bounds", ...)
   ```
   Anomaly is logged, but `die()` is never invoked (R3: Detected is not handled).
3. **Window Check**:
   In window `w06` at frame 1820 (t=30.79s), player exceeded `OUT_OF_BOUNDS_Y` reaching Y=1412.4.
   Player continues falling unimpeded across windows `w06`, `w07`, and `w08` (frames 1820–2557), reaching Y=290,889.94 with vertical velocity 45,033.21 px/s until session termination. No `player_died` event was ever dispatched.
4. **Steelman**: No lower platform or kill volume exists below Y=1400. The player falls indefinitely through empty space.
5. **Reproducibility**: Sustained continuously across >730 frames.
6. **Decision**: `confirmed` (Verdict: bug, Severity: critical, Confidence: 0.95, Level: L3).
   - Window: `w06`
   - Suspected Code: `Player.gd:L214-L222 (_physics_process)`
   - Dedupe Key: `Player.gd:L214:void_fall_without_death`

---

## Dismissed Candidates
1. **Frame 432 Stomp on Enemy4 Without Death**:
   - **Lead**: Stomp attempt and stomp bounce triggered at frame 432 on Enemy4, but Enemy4 was not killed.
   - **Reason**: Attacker was moving upward (`player_velocity_y: -1233.33`) into Enemy4's bottom collision box (`attacker_area_y: 735.34 > stomp_area_y: 733.47`). Per `Enemy.gd:L68-L69`, entering from below is rejected. Legitimate kill followed at frame 834 when stomped from above (`player_velocity_y: 1108.33`).
2. **Enemy Contact Hazards**:
   - Zero sideways contact events occurred in the session; no hazard bypass was exercised.
3. **Corner Pin & Step Align Traps**:
   - Player position never entered the trap bounding boxes in this session.

