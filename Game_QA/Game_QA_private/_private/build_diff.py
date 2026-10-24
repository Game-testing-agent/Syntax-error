import difflib
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ORIG_DIR = ROOT / "_private" / "archive" / "game_src_before_build"
NEW_DIR = ROOT / "game_src"

patch_lines = []
table_rows = []

DROPPED = ["Utils/BugFlags.gd", "Tests/test_bugs.gd", "Tests/test_fault_injection.gd"]

for dropped in DROPPED:
    table_rows.append({
        "file": dropped,
        "hunk_lines": "All lines",
        "flag_involved": "Entire file / registry / suite",
        "runtime_value": "N/A",
        "transformation": "Dropped file completely"
    })

for root, _, files in os.walk(ORIG_DIR):
    for f in sorted(files):
        if f.endswith(".uid") or f.startswith("."):
            continue
        orig_file = Path(root) / f
        rel = orig_file.relative_to(ORIG_DIR)
        norm_rel = str(rel).replace("\\", "/")
        new_file = NEW_DIR / rel

        if not new_file.exists():
            continue

        orig_text = orig_file.read_text(encoding="utf-8", errors="ignore").splitlines(keepends=True)
        new_text = new_file.read_text(encoding="utf-8", errors="ignore").splitlines(keepends=True)

        diff = list(difflib.unified_diff(
            orig_text, new_text,
            fromfile=f"a/{norm_rel}",
            tofile=f"b/{norm_rel}"
        ))

        if diff:
            patch_lines.extend(diff)
            # Find hunk line info
            for line in diff:
                if line.startswith("@@"):
                    table_rows.append({
                        "file": norm_rel,
                        "hunk_lines": line.strip(),
                        "flag_involved": "See patch",
                        "runtime_value": "true",
                        "transformation": "Guard substitution / comment removal"
                    })

patch_file = ROOT / "_private" / "sanitize_diff.patch"
patch_file.write_text("".join(patch_lines), encoding="utf-8")
print(f"Wrote patch to {patch_file} ({len(patch_lines)} lines)")

# Classify rows with specific details
table_md = [
    "# Sanitization Hunk & Equivalence Review Table",
    "",
    "| File | Hunk / Location | Flag Involved | Runtime Value | Transformation Applied |",
    "| :--- | :--- | :--- | :--- | :--- |",
    "| `Utils/BugFlags.gd` | Full file | Global BugFlags registry | N/A | Dropped file entirely |",
    "| `Tests/test_bugs.gd` | Full file | Benchmark test suite | N/A | Dropped file entirely |",
    "| `Tests/test_fault_injection.gd` | Full file | Fault injection suite | N/A | Dropped file entirely |",
    "| `Autoload/PlayerData.gd` | `L40` (`set_score`) | `bug_milestone_score_tax` | `true` | Removed flag check and `# TRICKY 4` comment; executed condition is unconditional |",
    "| `Actors/Player.gd` | `L82` (`_on_EnemyDetector_body_entered`) | `map1_enemy4_no_kill` | `true` | Unwrapped body condition; Enemy4 collision exemption executes unconditionally |",
    "| `Actors/Player.gd` | `L108` (`trigger_lava_contact`) | `map4_delayed_lava_death` | `true` | Unwrapped body condition; 3-second grace period executes unconditionally |",
    "| `Actors/Player.gd` | `L127` (`_physics_process`) | `map2_wall_stuck` | `true` | Unwrapped body condition; coordinates wedge executes unconditionally |",
    "| `Actors/Player.gd` | `L141` (`_physics_process`) | `map3_stair_stick` | `true` | Unwrapped body condition; stair sticking executes unconditionally |",
    "| `Actors/Player.gd` | `L246` (`_physics_process`) | `map1_floor_hole` | `true` | Unwrapped body trigger call; 1B triggers unconditionally on void fall |",
    "| `Actors/Player.gd` | `L264` (`get_direction`) | `map3_tower_wall_jump` | `true` | Removed flag term; wall jump triggers on wall contact |",
    "| `Actors/Enemy.gd` | `L19` (`_ready`) | `map4_retry_retains_enemies` | `true` | Reads `PlayerData.retained_enemy_transforms` directly |",
    "| `Actors/Enemy.gd` | `L36` (`_physics_process`) | `map2_floating_enemy` | `true` | Removed flag term; checks `@export var is_floating` |",
    "| `Actors/Enemy.gd` | `L77` (`_on_StompArea2D_area_entered`) | `bug_stomp_tunneling` | `true` | Removed flag export and comment; fast descent threshold subtraction is unconditional |",
    "| `Objects/Coin.gd` | `L63` (`_on_body_entered`) | `map1_seventh_coin_no_score` | `true` | Removed flag term; 7th coin zero score is unconditional |",
    "| `Objects/Portal2D.gd` | `L27` (`_on_body_entered`) | `map4_portal_second_touch` | `true` | Removed flag term; checks `is_map4_portal` |",
    "| `UserInterface/RetryButton.gd` | `L12` (`_on_button_up`) | `map4_retry_retains_enemies` | `true` | Saves enemy transforms to `PlayerData.retained_enemy_transforms` |",
    "| `Levels/Map2_UndergroundCaves.tscn` | `L139` | `is_floating_bug` | `true` | Renamed property to clean name `is_floating = true` |",
    "| `Utils/MapRunner.gd` | `L3` | Comment label | N/A | Removed word 'benchmark' from header comment |",
]

table_file = ROOT / "_private" / "sanitize_table.md"
table_file.write_text("\n".join(table_md), encoding="utf-8")
print(f"Wrote sanitize table to {table_file}")

