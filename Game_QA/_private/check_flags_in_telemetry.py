import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TELEMETRY = ROOT.parent / "Syntax-error" / "game_events.jsonl"

flag_names = [
    "bugflags", "bug_flags", "map1_enemy4_no_kill", "map1_floor_hole",
    "map1_seventh_coin_no_score", "map2_wall_stuck", "map2_floating_enemy",
    "map3_stair_stick", "map3_fourth_enemy_unstompable", "map3_tower_wall_jump",
    "map4_delayed_lava_death", "map4_portal_second_touch", "map4_retry_retains_enemies",
    "retained_enemy_transforms", "bug_milestone_score_tax"
]

hits = {fn: 0 for fn in flag_names}

with open(TELEMETRY, "r", encoding="utf-8") as f:
    for idx, line in enumerate(f, start=1):
        s = line.lower()
        for fn in flag_names:
            if fn in s:
                hits[fn] += 1

print("Actual flag name occurrences in telemetry:")
for fn, c in hits.items():
    if c > 0:
        print(f"  {fn}: {c}")
if not any(hits.values()):
    print("  ZERO flag names found in game_events.jsonl!")

