import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

with open(ROOT / "_private" / "raw_leaks.json", "r", encoding="utf-8") as f:
    raw = json.load(f)

# Categories
# flag file
# test file
# guarded block
# comment or label
# autoload
# other

items = []
counts = {
    "flag file": 0,
    "test file": 0,
    "guarded block": 0,
    "comment or label": 0,
    "autoload": 0,
    "telemetry field": 0,
    "other": 0
}

# Add telemetry finding to inventory
items.append({
    "loc": "telemetry:game_events.jsonl",
    "kind": "telemetry field",
    "note": "14 'bug_trigger' events present with synthetic bug_id ('1C', '2A', '2B', etc.)"
})
counts["telemetry field"] += 1

for r in raw:
    path_loc = r["path"]
    line = r["line"]
    match = r["match"]
    
    # Classify
    kind = "other"
    note = f"Contains '{match}'"
    
    p_lower = path_loc.lower()
    
    if "bugflags.gd" in p_lower and ("real_src/utils" in p_lower or "game_src/utils" in p_lower):
        kind = "flag file"
        note = f"Definition/declaration of flag registry ({match})"
    elif "project.godot" in p_lower and "bugflags" in line.lower():
        kind = "autoload"
        note = "Autoload singleton registration for BugFlags"
    elif "test_bugs.gd" in p_lower or "test_fault_injection.gd" in p_lower:
        kind = "test file"
        note = f"Benchmark verification test script ({match})"
    elif line.strip().startswith("#"):
        kind = "comment or label"
        note = f"Comment describing defect/benchmark: {line.strip()[:60]}"
    elif any(kw in line for kw in ["if BugFlags", "if bug_flags", "BugFlags.", "bug_milestone_score_tax"]):
        kind = "guarded block"
        note = f"Conditional code guarded by flag: {line.strip()[:60]}"
    elif any(kw in line for kw in ["is_floating_bug", "is_unstompable_bug", "is_wall_stuck", "is_stair_stuck", "lava_timer"]):
        kind = "guarded block"
        note = f"Defect state variable or guard: {line.strip()[:60]}"
    else:
        kind = "other"
        note = f"Reference to {match} in pipeline/doc/metadata: {line.strip()[:60]}"

    counts[kind] += 1
    items.append({
        "loc": path_loc,
        "kind": kind,
        "note": note
    })

lines = [
    "# Leak Inventory",
    "",
    "## Summary Counts by Kind",
    "",
    "| Kind | Count |",
    "| :--- | :--- |",
]
for k, c in counts.items():
    lines.append(f"| {k} | {c} |")

lines.extend([
    "",
    f"**Total Leak Sites Identified**: {len(items)}",
    "",
    "## Telemetry Analysis",
    "- `game_events.jsonl`: Zero flag names found in data/payload. However, 14 `bug_trigger` discrete events exist which include synthetic IDs (`bug_id: '1C'`, `bug_id: '2A'`, `bug_id: '2B'`). Telemetry will be preserved without alteration as mandated by Rule 0.2.",
    "- `sample_game_events.jsonl`: Zero flag names and zero `bug_trigger` events.",
    "",
    "## Detailed Inventory Table",
    "",
    "| Location | Kind | Note |",
    "| :--- | :--- | :--- |",
])

for it in items:
    # sanitize pipe in note
    safe_note = it["note"].replace("|", "\\|")
    lines.append(f"| `{it['loc']}` | `{it['kind']}` | {safe_note} |")

inventory_path = ROOT / "_private" / "leak_inventory.md"
inventory_path.write_text("\n".join(lines), encoding="utf-8")
print(f"Wrote leak inventory to {inventory_path}")
print("Counts:")
for k, c in counts.items():
    print(f"  {k}: {c}")

