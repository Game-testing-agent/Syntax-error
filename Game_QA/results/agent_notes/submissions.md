# Pipeline Submissions Log (Phase C)

## Submissions Summary
- **Session ID**: `session_1792862072_26412`
- **Total Findings Submitted**: 4
- **Windows with Submissions**: 4 (`w01`, `w02`, `w03`, `w06`)
- **Submission Stride**: `--stride 1` (matching `eval.py --stride 1`)

---

## Submission Details

### 1. Window `w01`
- **Session ID**: `session_1792862072_26412`
- **Window ID**: `w01` (t = 5.0s to 10.0s)
- **Title**: `Score Decrements When Earning Points Above 500 Threshold`
- **Attachment Rationale**: Attached to `w01` because frame 424 is the earliest frame where score reached >= 500 and the decrement defect first manifested upon collecting Coin8.
- **Source**: `agent` (independent invariant sweep and code audit of `PlayerData.set_score`)
- **Tool Success Output**:
  ```
  [native_submit] Successfully submitted finding for session_1792862072_26412 / w01
    Title: Score Decrements When Earning Points Above 500 Threshold
    Cache key: C:\Users\hunne\Documents\Game_QA\.cache\audit_c9ff9c6b654f819f196a53fe047f0899.json
  ```

### 2. Window `w02`
- **Session ID**: `session_1792862072_26412`
- **Window ID**: `w02` (t = 10.0s to 15.0s)
- **Title**: `Phantom Enemy Wall Reversal Freezes Patrol at Zero Velocity`
- **Attachment Rationale**: Attached to `w02` because frame 690 is the exact frame where Enemy4 triggered wall reversal with old_direction: 0.0 and new_direction: 0.0, permanently halting patrol.
- **Source**: `agent` (invariant sweep across all `enemy_reversed_at_wall` payloads cross-referenced with `Enemy.gd`)
- **Tool Success Output**:
  ```
  [native_submit] Successfully submitted finding for session_1792862072_26412 / w02
    Title: Phantom Enemy Wall Reversal Freezes Patrol at Zero Velocity
    Cache key: C:\Users\hunne\Documents\Game_QA\.cache\audit_4b0f27e2d8401da1ff46403ce550ad88.json
  ```

### 3. Window `w03`
- **Session ID**: `session_1792862072_26412`
- **Window ID**: `w03` (t = 15.0s to 20.0s)
- **Title**: `Seventh Coin Collection Suppresses Score Award`
- **Attachment Rationale**: Attached to `w03` because frame 934 is the collection frame of the 7th coin (Coin11) where score failed to increment.
- **Source**: `agent` (reconciliation of pickups against score delta and source analysis of `Coin.gd:picked()`)
- **Tool Success Output**:
  ```
  [native_submit] Successfully submitted finding for session_1792862072_26412 / w03
    Title: Seventh Coin Collection Suppresses Score Award
    Cache key: C:\Users\hunne\Documents\Game_QA\.cache\audit_e4f15b516ebb0e3d9ca29f92d053e876.json
  ```

### 4. Window `w06`
- **Session ID**: `session_1792862072_26412`
- **Window ID**: `w06` (t = 30.0s to 35.0s)
- **Title**: `Player Out of Bounds Void Fall Without Death`
- **Attachment Rationale**: Attached to `w06` because frame 1820 is the boundary breach frame where player Y exceeded OUT_OF_BOUNDS_Y (1400.0) without `die()` being called.
- **Source**: `agent` (bounds audit and negative space verification of missing `player_died` consequence)
- **Tool Success Output**:
  ```
  [native_submit] Successfully submitted finding for session_1792862072_26412 / w06
    Title: Player Out of Bounds Void Fall Without Death
    Cache key: C:\Users\hunne\Documents\Game_QA\.cache\audit_6924b67d5bfb674fa2d8b5be93af29b6.json
  ```

