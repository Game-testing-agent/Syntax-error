import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC_TELEM = ROOT / "Game_QA_audit" / "telemetry" / "game_events.jsonl"
PRIVATE_DIR = ROOT / "_private" / "telemetry"
PRIVATE_DIR.mkdir(parents=True, exist_ok=True)
ORIG_BACKUP = PRIVATE_DIR / "game_events_original.jsonl"

# Read original
with open(SRC_TELEM, "r", encoding="utf-8") as f:
    orig_lines = f.readlines()

# Backup original
with open(ORIG_BACKUP, "w", encoding="utf-8") as f:
    f.writelines(orig_lines)

filtered_lines = []
removed_events = []

for line in orig_lines:
    if not line.strip():
        continue
    ev = json.loads(line)
    en = ev.get("event_name") or ev.get("event") or ""
    if en == "bug_trigger":
        removed_events.append(ev)
    else:
        filtered_lines.append(line)

# Write sanitized copy back to Game_QA_audit/telemetry/game_events.jsonl
with open(SRC_TELEM, "w", encoding="utf-8") as f:
    f.writelines(filtered_lines)

print(f"Original lines: {len(orig_lines)}")
print(f"Removed events (bug_trigger): {len(removed_events)}")
print(f"Sanitized lines in copy: {len(filtered_lines)}")

# Confirm no remaining bug IDs or payload keys in sanitized telemetry
forbidden_keys = [
    "bug_id", "tile_coords", "stair_coords", "wall_coords", "jump_multiplier",
    "escape_presses_needed", "delay_seconds", "required_touches", "retained_enemies_count"
]

remaining_leaks = []
for idx, line in enumerate(filtered_lines, 1):
    for k in forbidden_keys:
        if f'"{k}"' in line:
            remaining_leaks.append((idx, k))

print(f"Remaining leak hits across sanitized telemetry: {len(remaining_leaks)}")
if remaining_leaks:
    for h in remaining_leaks:
        print(f"  Line {h[0]}: {h[1]}")

