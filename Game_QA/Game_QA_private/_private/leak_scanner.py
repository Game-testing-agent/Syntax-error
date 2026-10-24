import os
import re
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REAL_SRC = ROOT.parent / "Syntax-error" / "godot-4game" / "src"
REAL_PROJ = ROOT.parent / "Syntax-error" / "godot-4game" / "project.godot"
TELEMETRY = ROOT.parent / "Syntax-error" / "game_events.jsonl"
SAMPLE_TELEMETRY = ROOT.parent / "Syntax-error" / "sample_game_events.jsonl"

SEARCH_DIRS = [
    ROOT / "game_src",
    ROOT / "data",
    ROOT / "prompts",
    ROOT / ".agents",
    ROOT / "tools",
]

PIPELINE_FILES = [
    ROOT / "loader.py",
    ROOT / "code_loader.py",
    ROOT / "checker.py",
    ROOT / "llm.py",
    ROOT / "eval.py",
    ROOT / "report.py",
    ROOT / "schemas.py",
]

# Patterns to search
KEYWORDS = [
    r"\bBugFlags\b",
    r"\bbug_flags\b",
    r"\btest_bugs\b",
    r"\btest_fault_injection\b",
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
    r"\bhas_triggered_floating\b",
    r"\bis_unstompable_bug\b",
    r"\bis_wall_stuck\b",
    r"\bis_stair_stuck\b",
    r"\bstair_escape_count\b",
    r"\blava_timer\b",
    r"TRICKY\s+\d+",
    r"\bbenchmark\b",
    r"\bsynthetic\b",
    r"\binjection\b",
    r"\btoggle\b",
    r"\bknown defect\b",
    r"\bknown bug\b",
    r"\bplanted\b",
    r"\bseeded\b",
]

regex = re.compile("|".join(KEYWORDS), re.IGNORECASE)

findings = []

def scan_file(fpath: Path, rel_label: str):
    if not fpath.exists() or fpath.is_dir():
        return
    # Skip binaries or private archive
    if "_private" in fpath.parts or ".git" in fpath.parts:
        return
    try:
        content = fpath.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return
    lines = content.splitlines()
    for idx, line in enumerate(lines, start=1):
        m = regex.search(line)
        if m:
            matched_text = m.group(0)
            findings.append({
                "path": f"{rel_label}:{idx}",
                "line": line.strip(),
                "match": matched_text
            })

# Scan real source
if REAL_SRC.exists():
    for root, _, files in os.walk(REAL_SRC):
        for f in files:
            p = Path(root) / f
            rel = f"real_src/{p.relative_to(REAL_SRC)}"
            scan_file(p, rel)

if REAL_PROJ.exists():
    scan_file(REAL_PROJ, "real_src/project.godot")

# Scan game_src
for root, _, files in os.walk(ROOT / "game_src"):
    for f in files:
        p = Path(root) / f
        rel = f"game_src/{p.relative_to(ROOT / 'game_src')}"
        scan_file(p, rel)

# Scan pipeline files
for p in PIPELINE_FILES:
    if p.exists():
        scan_file(p, p.name)

# Scan other dirs
for d in SEARCH_DIRS:
    if d.exists():
        for root, _, files in os.walk(d):
            for f in files:
                p = Path(root) / f
                if p not in PIPELINE_FILES:
                    rel = str(p.relative_to(ROOT)).replace("\\", "/")
                    scan_file(p, rel)

print(f"Total leak items found across codebases and pipeline: {len(findings)}")

# Save raw scan
with open(ROOT / "_private" / "raw_leaks.json", "w", encoding="utf-8") as f:
    json.dump(findings, f, indent=2)

