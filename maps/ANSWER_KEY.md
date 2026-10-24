# Syntax-Error QA Benchmark — Master Answer Key

This document provides a consolidated reference of all 11 intentional, documented benchmark bugs implemented across Maps 1 through 4.

| Bug ID | Map | Coordinates (Tile / Global) | Description | Expected Behavior | Actual Observed Behavior | Log Identifier |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **1A** | Map 1: Green Hills | Tile `(38, 7)`<br>`(3040, 560)` | Enemy4 collision does not kill player | Player dies upon collision with enemy body | `Enemy4` has `can_kill_player=false`; player collides safely without dying | `[BUGTRIGGER] 1A` |
| **1B** | Map 1: Green Hills | Tile `x=29..32, y=10..13`<br>`(2320..2560, 800..1040)` | Gap in level floor causing endless void fall | Solid platform or bottom boundary death zone | Floor collision omitted; player falls infinitely through void past `y > 1000` | `[BUGTRIGGER] 1B` |
| **1C** | Map 1: Green Hills | Tile `(42, 6)`<br>`(3360, 480)` | Collecting 7th coin gives 0 points | Coin pickup grants +100 score | Coin plays collection effect and increments pickup counter, but awards +0 score | `[BUGTRIGGER] 1C` |
| **2A** | Map 2: Underground Caves | Tile `(55, 8)`<br>`(4400, 640)` | Player wedged in narrow ceiling block gap | Collision allows smooth sliding or completely blocks entry | Player becomes permanently stuck inside narrow ceiling slot; only retry frees player | `[BUGTRIGGER] 2A` |
| **2B** | Map 2: Underground Caves | Tile `(94, 4)`<br>`(7520, 320)` | Enemy patrols off platform and floats in air | Enemy turns around at ledge or falls with gravity | Enemy walks off platform ledge and continues floating horizontally across the chasm | `[BUGTRIGGER] 2B` |
| **3A** | Map 3: Sky Castle | Tile `(68, 7)`<br>`(5440, 560)` | Player stuck on staircase edge until 3 left taps | Smooth stair climbing and movement | Player freezes on stair step edge; cannot jump or walk until pressing left 3 times | `[BUGTRIGGER] 3A` |
| **3B** | Map 3: Sky Castle | Tile `(88, 7)`<br>`(7040, 560)` | 4th enemy cannot be squashed by stomping | Stomping enemy squashes and eliminates it | Stomp detection logs and bounces player, but enemy remains alive and active | `[BUGTRIGGER] 3B` |
| **3C** | Map 3: Sky Castle | Tile `(195, 7)`<br>`(15600, 560)` | Wall jump on final tower gives 2x height | Standard vertical jump impulse (-1000 px/s) | Touching tower left wall doubles jump vertical launch velocity (-2000 px/s) | `[BUGTRIGGER] 3C` |
| **4A** | Map 4: Lava Fortress | Tile `x=43..53, y=10..12`<br>`(3480..4280, 800..960)` | Delayed lava death with 3-second grace period | Instant death upon touching lava surface | Death is delayed by 3 seconds; player can still jump out and pick up coins | `[BUGTRIGGER] 4A` |
| **4B** | Map 4: Lava Fortress | Tile `(215, 6)`<br>`(17200, 480)` | Goal portal requires two distinct touches | First touch triggers level transition | First touch is ignored; player must touch portal a second time to activate level transition | `[BUGTRIGGER] 4B` |
| **4C** | Map 4: Lava Fortress | Global Level Scope | Level Retry fails to reset enemy positions | Restart reinitializes all enemy spawn transforms | Player resets to spawn, but enemies retain their pre-retry world coordinates | `[BUGTRIGGER] 4C` |

---

## Log Verification Format
When an agent or automated tester triggers any of these benchmark bugs, two log entries are emitted:
1. **Human-Readable Log (`run_YYYYMMDD_HHMMSS.log`)**:
   ```text
   [BUGTRIGGER] <BUG_ID>: <JSON_DETAILS>
   ```
2. **Schema 1.0 Event Log (`game_events.jsonl`)**:
   ```json
   {
     "schema_version": "1.0",
     "session_id": "<uuid>",
     "event_id": 123,
     "timestamp_unix_ms": 1729770000000,
     "category": "bug",
     "event_type": "bug_trigger",
     "action_context": "physics_process",
     "elapsed_ms": 5000,
     "physics_frame": 300,
     "details": {
       "bug_id": "<BUG_ID>",
       ...
     }
   }
   ```

