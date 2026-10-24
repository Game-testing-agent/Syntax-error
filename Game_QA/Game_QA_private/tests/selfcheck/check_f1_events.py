import sys
import json
import re
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from loader import resolve_log_path

log_path = resolve_log_path()
real_src = Path("../Syntax-error/godot-4game/src").resolve()

# 1. Collect all distinct event names
event_names = set()
with open(log_path, "r", encoding="utf-8") as f:
    for line in f:
        l = line.strip()
        if not l:
            continue
        try:
            obj = json.loads(l)
            ev = obj.get("event_name") or obj.get("event") or obj.get("category")
            if ev:
                event_names.add(ev)
        except Exception:
            pass

print(f"Total distinct event names in telemetry: {len(event_names)}")

# 2. Collect all GDScript content in real_src
all_code = {}
for p in real_src.rglob("*.gd"):
    try:
        all_code[p.name] = p.read_text(encoding="utf-8")
    except Exception as e:
        print(f"Error reading {p}: {e}")

missing_events = []
found_events = {}

for ev in sorted(event_names):
    hits = [fname for fname, code in all_code.items() if ev in code]
    if hits:
        found_events[ev] = hits
    else:
        missing_events.append(ev)

print(f"Found events in source: {len(found_events)}")
print(f"Missing events in source: {len(missing_events)}")
if missing_events:
    print("MISSING EVENTS:")
    for m in missing_events:
        print(f"  - {m}")
else:
    print("ALL telemetry events verified emitted in real source!")

