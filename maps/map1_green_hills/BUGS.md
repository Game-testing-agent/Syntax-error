# Map 1: Green Hills — Documented Bugs

This document details all intentional benchmark bugs planted in **Map 1: Green Hills** (`godot-4game/src/Levels/Map1_GreenHills.tscn`).

---

### Bug 1A: Enemy4 Immunity to Player Collision (Non-Lethal Contact)
- **Bug ID**: `1A`
- **Tile Coordinates**: `(38, 7)` — Global Position: `(3040, 560)`
- **Steps to Reproduce**:
  1. Launch Map 1: `python run_map.py --map 1`.
  2. Walk right across the first two platforms past the void gap to `x ≈ 3000`.
  3. Walk directly into `Enemy4` without jumping or stomping.
- **Expected Behavior**:
  Player dies immediately upon touching the enemy body and triggers death animation/reset.
- **Actual Behavior**:
  `Enemy4` has `can_kill_player = false`. The player collides with and passes through or walks against the enemy without dying or taking damage.
- **Exact BUGTRIGGER Log Line**:
  ```text
  [BUGTRIGGER] 1A: {"description":"Enemy4 collided without causing death","enemy":"Enemy4"}
  ```

---

### Bug 1B: Floor Void Hole
- **Bug ID**: `1B`
- **Tile Coordinates**: `x=29..32, y=10..13` — Global Position: `x=2320..2560, y=800..1040`
- **Steps to Reproduce**:
  1. Launch Map 1: `python run_map.py --map 1`.
  2. Run right from spawn point past the first platform section.
  3. Step into the gap at `x=29..32` instead of jumping across.
- **Expected Behavior**:
  A solid floor tile should catch the player, or the pit boundary should trigger a respawn/death screen.
- **Actual Behavior**:
  Missing floor collision tiles allow the player to fall continuously into the infinite void past `y > 1000`.
- **Exact BUGTRIGGER Log Line**:
  ```text
  [BUGTRIGGER] 1B: {"description":"Fell through floor hole at x=29..32, y=10..13","position":[2400.0,1050.0]}
  ```

---

### Bug 1C: 7th Coin Pickup Awards No Score
- **Bug ID**: `1C`
- **Tile Coordinates**: `(42, 6)` (or whichever 7th coin is collected) — Global Position: `(3360, 480)`
- **Steps to Reproduce**:
  1. Launch Map 1: `python run_map.py --map 1`.
  2. Collect any 6 coins along the path.
  3. Pick up the 7th coin.
- **Expected Behavior**:
  Player score increases by +100 upon collecting the coin (displaying +100 animation).
- **Actual Behavior**:
  The 7th coin plays the pickup sound and animation and increments total coin count, but `PlayerData.score` is not increased (+0 score awarded).
- **Exact BUGTRIGGER Log Line**:
  ```text
  [BUGTRIGGER] 1C: {"coin_id":12345,"coin_number":7,"position":{"x":3360.0,"y":480.0},"score_awarded":0}
  ```

