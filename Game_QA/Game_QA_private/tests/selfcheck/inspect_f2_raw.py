import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from loader import resolve_log_path

log_path = resolve_log_path()
snaps = []
events = []

with open(log_path, "r", encoding="utf-8") as f:
    for line in f:
        l = line.strip()
        if not l:
            continue
        try:
            obj = json.loads(l)
            cat = obj.get("category")
            ev = obj.get("event_name") or obj.get("event")
            if cat == "state_snapshot" or ev == "state_snapshot":
                if len(snaps) < 5:
                    snaps.append(obj)
            else:
                if len(events) < 5:
                    events.append(obj)
            if len(snaps) == 5 and len(events) == 5:
                break
        except Exception:
            pass

print("--- 5 RAW SNAPSHOTS ---")
for i, s in enumerate(snaps, 1):
    print(f"Snapshot {i}: category={repr(s.get('category'))}, event_name={repr(s.get('event_name'))}")
    print(f"  data.event={repr(s.get('data', {}).get('event'))}")
    print(f"  data keys={list(s.get('data', {}).keys())[:6]}")

print("\n--- 5 RAW EVENTS ---")
for i, e in enumerate(events, 1):
    print(f"Event {i}: category={repr(e.get('category'))}, event_name={repr(e.get('event_name'))}")
    print(f"  keys={list(e.keys())[:6]}")

