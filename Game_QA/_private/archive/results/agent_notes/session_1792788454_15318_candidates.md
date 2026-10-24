# Candidate Adjudication Log: session_1792788454_15318

## Lead 1: Unregistered Exit Portal Progression Soft-Lock
1. **Contract**: Lifecycle Progression Invariant (`Portal2D.gd:L11-L16`) — Reaching the level finish coordinates must trigger `portal_entered` and transition scenes.
2. **Code Path**: `Portal2D.gd:L11-L16` (`_ready` / `_on_body_entered`).
3. **Window Check**: Across all 27 snapshots, `goal.found` is `false`. The player reaches terminus coordinates $(7486.56, 159.97)$ at frames 3594 and 3739, resting directly at the portal without any scene transition.
4. **Steelman**: Player reached portal coordinates ($X \approx 7486.56, Y \approx 160.0$) and stayed grounded; `goal.found` was `false` throughout the entire level.
5. **Decision**: **Confirmed Bug** (`critical`, confidence 0.95).

## Lead 2: Milestone Score Deductions on Collectibles
1. **Contract**: State Monotonicity Invariant (`PlayerData.gd:L32`) — Score must only increase during gameplay.
2. **Code Path**: `PlayerData.gd:L36-L43` (`set_score`).
3. **Window Check**: At frames 810, 908, 1039, 1050, 1056, 1364, 1377, picking up collectibles decrements score by 10 points.
4. **Steelman**: Confirmed bug toggle `# TRICKY BUG 4: Milestone Score Regression` in `PlayerData.gd:L40-L41`.
5. **Decision**: **Confirmed Bug** (`high`, confidence 0.95).

## Lead 3: Duplicate Pickup Attempt on Coin14
1. **Contract**: Collectible Idempotency Invariant (`Coin.gd:L27-L35`) — Coin collision must not trigger `body_entered` queries after initial collection.
2. **Code Path**: `Coin.gd:L27-L35` (`_on_body_entered`) & `Coin.tscn`.
3. **Window Check**: `Coin14` collected at frame 1039. At frame 1061 (during 0.4s picked animation before `queue_free`), upward bounce through coin location triggered `duplicate_pickup_attempt`.
4. **Steelman**: Collision shape was left enabled on the area during the picked animation sequence instead of being disabled immediately.
5. **Decision**: **Confirmed Bug** (`medium`, confidence 0.90).

