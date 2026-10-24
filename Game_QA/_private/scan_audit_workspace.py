import os
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
AUDIT_DIR = ROOT / "Game_QA_audit"

# Comprehensive private tokens & generic forbidden patterns
PRIVATE_PATTERNS = [
    # Answer key & flag files
    r"bugflags?\.gd",
    r"\bbugflag\w*",
    r"\btest_bugs\b",
    r"\btest_fault_injection\b",
    
    # Specific defect flags & variables
    r"\bbug_milestone_score_tax\b",
    r"\bmap1_enemy4_no_kill\b",
    r"\bmap1_floor_hole\b",
    r"\bmap1_seventh_coin_no_score\b",
    r"\bmap2_wall_stuck\b",
    r"\bmap2_floating_enemy\b",
    r"\bmap3_stair_stick\b",
    r"\bmap3_fourth_enemy_unstompable\b",
    r"\bmap3_tower_wall_jump\b",
    r"\bmap4_delayed_lava_death\b",
    r"\bmap4_portal_second_touch\b",
    r"\bmap4_retry_retains_enemies\b",
    r"\bretained_enemy_transforms\b",
    r"\bis_floating_bug\b",
    r"\bis_unstompable_bug\b",
    r"\bbug_stomp_tunneling\b",
    r"\bbug_wall_friction_jump\b",
    r"\bbug_deferred_pickup_race\b",
    
    # Bug logging functions & telemetry events
    r"\bbug_trigger\b",
    r"\blog_bug\w*",
    
    # Defect-hinting identifiers per rename_map
    r"\bis_wall_stuck\b",
    r"\bis_stair_stuck\b",
    r"\bstair_escape_count\b",
    r"\bis_unstompable\b",
    r"\btrigger_lava_contact\b",
    r"\bFloatingEnemy\b",
    
    # Benchmark / synthetic annotations
    r"TRICKY\s+\d+",
    r"\binject\w*",
    r"\bsynthetic\w*",
    r"\bbenchmark\w*",
    r"\bseeded\w*",
    r"\bplanted\w*",
    r"\bknown[_\s]+bug\b",
    r"\bknown[_\s]+defect\b",
]

regex = re.compile("|".join(PRIVATE_PATTERNS), re.IGNORECASE)

hits = []

for root, dirs, files in os.walk(AUDIT_DIR):
    for f in files:
        fpath = Path(root) / f
        rel = str(fpath.relative_to(AUDIT_DIR)).replace("\\", "/")
        try:
            lines = fpath.read_text(encoding="utf-8", errors="ignore").splitlines()
        except Exception:
            continue
        for idx, line in enumerate(lines, start=1):
            if regex.search(line):
                hits.append(f"{rel}:{idx}")

print(f"Total scan hits in Game_QA_audit: {len(hits)}")
if hits:
    print("Hits found at (file:line):")
    for h in hits[:25]:
        print(f"  {h}")
    if len(hits) > 25:
        print(f"  ... and {len(hits) - 25} more")
else:
    print("Zero forbidden token hits across Game_QA_audit!")
