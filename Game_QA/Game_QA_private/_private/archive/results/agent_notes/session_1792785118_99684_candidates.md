# Candidate Adjudication Log: session_1792785118_99684

## Lead 1: Milestone Score Regression / Deductions on Pickups
1. **Contract**: State Monotonicity Invariant (`PlayerData.gd:L32`) — Score must only increase during gameplay or reset to 0 upon death.
2. **Code Path**: `PlayerData.gd:L36-L43` (`set_score`).
3. **Window Check**: Across 14 instances (frames 754, 834, 847, 912, 915, 1165, 1177, 1179, 2060, 2251, 2307, 2539, 2544, 2556), picking up collectibles triggers `unexpected_score_change` where score is decremented by 10 points.
4. **Steelman**: Intentional penalty? Confirmed bug toggle `# TRICKY BUG 4: Milestone Score Regression` in `PlayerData.gd`.
5. **Reproducibility**: Reproduces reliably 14 times.
6. **Decision**: **Confirmed Bug** (`high`, confidence 0.95).

## Lead 2: Scene Transitions at Initialization
- **Lead**: `scene_loaded` at frame 5 and 125, `scene_change_pressed` at frame 109.
- **Steelman**: Normal game start flow from MainScreen to Level01.
- **Decision**: **Dismissed** (expected startup sequence).

