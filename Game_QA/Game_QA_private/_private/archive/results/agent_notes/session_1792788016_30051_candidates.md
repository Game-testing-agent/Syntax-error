# Candidate Adjudication Log: session_1792788016_30051

## Lead 1: Milestone Score Deductions on Collectibles
1. **Contract**: State Monotonicity Invariant (`PlayerData.gd:L32`) — Score must only increase during gameplay or reset to 0 upon death.
2. **Code Path**: `PlayerData.gd:L36-L43` (`set_score`).
3. **Window Check**: Across 11 collectible pickups and enemy stomps (frames 394, 539, 554, 578, 595, 607, 617, 736, 745, 1074), adding score after reaching 500 points triggered `unexpected_score_change` deducting 10 points.
4. **Steelman**: Confirmed bug toggle `# TRICKY BUG 4: Milestone Score Regression` in `PlayerData.gd:L40-L41`.
5. **Reproducibility**: Reproduces reliably 11 times.
6. **Decision**: **Confirmed Bug** (`high`, confidence 0.95).

## Lead 2: Player Demise upon Contact with Enemy5
- **Lead**: At frame 1223, `player_died` after `enemy_contact_started`.
- **Steelman**: Normal combat hazard consequence defined in `Player.gd:_on_EnemyDetector_body_entered`.
- **Decision**: **Dismissed** (intended combat damage resolution).

