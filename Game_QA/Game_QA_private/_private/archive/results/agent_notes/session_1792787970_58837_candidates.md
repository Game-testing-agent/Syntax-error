# Candidate Adjudication Log: session_1792787970_58837

## Lead 1: Milestone Score Deductions on Collectibles
1. **Contract**: State Monotonicity Invariant (`PlayerData.gd:L32`) — Score must only increase during gameplay or reset to 0 upon death.
2. **Code Path**: `PlayerData.gd:L36-L43` (`set_score`).
3. **Window Check**: Across 9 distinct collectible pickups (frames 681, 1294, 1316, 1460, 1461, 1469, 1731, 1839, 2419), picking up coins after reaching 500 points triggered `unexpected_score_change` where score was decremented by 10 points.
4. **Steelman**: Confirmed bug toggle `# TRICKY BUG 4: Milestone Score Regression` in `PlayerData.gd:L40-L41`.
5. **Reproducibility**: Reproduces reliably 9 times whenever score $\ge 500$.
6. **Decision**: **Confirmed Bug** (`high`, confidence 0.95).

## Lead 2: Score Resets to 0 upon Level Retry
- **Lead**: Frame 902 score dropped 590 to 0, frame 2032 score dropped 530 to 0.
- **Steelman**: Accompanied by `retry_pressed` and `retry_started`. Intentional game restart resets player data per `PlayerData.gd:reset_data()`.
- **Decision**: **Dismissed** (benign intentional reset).

