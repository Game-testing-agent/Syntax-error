# QA Auditor Self-Assessment (Phase D3)

## 1. Findings & Evidence Ladder Calibration
All four confirmed findings achieved **Level L3** on the evidence ladder (telemetry anomaly observed + root cause traced directly to GDScript + mechanism prediction verified):

1. **Score Decrements When Earning Points Above 500 Threshold**:
   - **Ladder Level**: `L3` (Confidence: `0.95`, Severity: `high`)
   - **Grounding**: 7 telemetry anomalies (`unexpected_score_change` at frames 424, 834, 880, 1003, 1124, 1206, 1706) traced directly to `PlayerData.gd:L33-L35` (`final_score = old_score - 10`). Prediction verified across every single coin pickup and enemy kill while score was >= 500.

2. **Phantom Enemy Wall Reversal Freezes Patrol at Zero Velocity**:
   - **Ladder Level**: `L3` (Confidence: `0.90`, Severity: `high`)
   - **Grounding**: At frame 690, Enemy4 emitted `enemy_reversed_at_wall` with `old_direction: 0.0` and `new_direction: 0.0` at position `(5059.96, 800.0)`. Traced to `Enemy.gd:L44-L50` multiplying 0.0 velocity by -1.0. Enemy4 remained stationary until stomped at frame 834.

3. **Seventh Coin Collection Suppresses Score Award**:
   - **Ladder Level**: `L3` (Confidence: `0.95`, Severity: `high`)
   - **Grounding**: At frame 934, Coin11 was collected (7th coin picked). Telemetry recorded `coin_score_awarded` with gain=100, but `score_before` and `score_after` were both 570 (delta 0). Traced to `Coin.gd:L58-L59` (`if total_coins_collected == 7: should_award_score = false`).

4. **Player Out of Bounds Void Fall Without Death**:
   - **Ladder Level**: `L3` (Confidence: `0.95`, Severity: `critical`)
   - **Grounding**: At frame 1820, player crossed below `OUT_OF_BOUNDS_Y = 1400.0` reaching Y=1412.4 (`player_out_of_bounds`). Traced to `Player.gd:L214-L222`, where the anomaly is logged but `die()` is never called (Detected is not handled). Player fell continuously across frames 1820–2557 down to Y=290,889.94 without dying, resetting, or respawning.

---

## 2. Hypotheses Left `unsure` & Required Data to Settle
- **Stomp Area Entry from Below (Frame 432)**:
  - *Hypothesis*: At frame 432, Player jumped upward into Enemy4's stomp area (`player_velocity_y: -1233.33`), receiving a stomp bounce velocity (-1350.0) without killing Enemy4 (`attacker_area_y: 735.34 > stomp_area_y: 733.47`).
  - *Missing Data*: Settling whether giving a bounce on an invalid/non-fatal stomp is a defect or intended forgiving platformer design requires Godot collision normal telemetry and designer specification for upward stomp interactions.
- **Rapid Wall Oscillation Preceding Freeze (Frames 561–673)**:
  - *Hypothesis*: Enemy4 reversed direction 6 times in under 120 frames between x=4923 and x=5160.
  - *Missing Data*: Settling whether this is a level geometry defect (wall collision shapes too close together) or an enemy raycast/velocity issue requires TileMap collision polygon data in telemetry.

---

## 3. Areas Unjudgeable (Telemetry Blind Spots & Sampling)
- **Sub-frame Physics Coordinates**: Snapshots occur ~every 60 frames (1 Hz). Instantaneous physics changes between snapshot ticks are unobservable unless explicitly logged as discrete events.
- **Continuous Enemy Positions**: Enemies do not stream position logs unless interacting with walls or the player.
- **Portal & Level Clear Sequence**: The player fell into the void at frame 1820 and never reached the exit portal at the end of Level 4, leaving portal transition completion unobservable in this run.
- **Surface Hazard Interactions**: No lava or surface hazard was touched during this run.

---

## 4. Workspace Artifacts Naming, Toggling, or Listing Defects (File & Line Only)
- `game_src/Actors/Player.gd:4`
- `game_src/Actors/Player.gd:79`
- `game_src/Actors/Player.gd:111`
- `game_src/Actors/Player.gd:118`
- `game_src/Actors/Enemy.gd:9`
- `game_src/Objects/Coin.gd:5`
- `game_src/Objects/Coin.gd:58`
- `game_src/Objects/Portal2D.gd:7`
- `game_src/Objects/Portal2D.gd:66`
- `game_src/Autoload/PlayerData.gd:33`

---

## 5. Three Concrete Proposed Edits to SKILL.md
1. **Explicit Stride Synchronization in Tooling Instructions**:
   - *Proposal*: Add a note in Section 10 stating: *"When submitting findings via `tools/native_submit.py`, pass the exact `--stride` value intended for `eval.py` (e.g. `--stride 1` for short sessions), so the content-addressed review window digests match identically."*
2. **Clarification of Pydantic Schema vs. Extended Reporting Fields**:
   - *Proposal*: Update Section 10 to clarify that `schemas.Finding` only validates the 9 standard Pydantic model fields (`verdict`, `severity`, `confidence`, `title`, `explanation`, `evidence_frames`, `suspected_code`, `path`, `needs_human_review`). Explicitly instruct that auxiliary fields (`category`, `dedupe_key`, `repro_hint`) belong in a separate sidecar extras JSON.
3. **Guidance on Merging Loader Anomalies with Root Cause Findings**:
   - *Proposal*: Add guidance under Phase 5 (Merge and calibrate) on how agents should associate Path 1 engine anomalies (e.g., `unexpected_score_change`) with white-box root cause findings, ensuring unified deduplication keys across both paths.

