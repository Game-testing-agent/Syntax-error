import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
import json
from collections import Counter
from loader import resolve_log_path, load_sessions

log_path = resolve_log_path()
sessions = load_sessions(log_path, stride=1)
sess = sessions["session_1792862072_26412"]

ev_counter = Counter(e.event for e in sess.events)
print(f"Total events: {len(sess.events)}, Distinct event names: {len(ev_counter)}")
print("Event counts:")
for ev, cnt in ev_counter.most_common():
    print(f"  {ev:35s}: {cnt}")

print("\nField schema per event:")
event_fields = {}
for e in sess.events:
    if e.event not in event_fields:
        event_fields[e.event] = {
            "categories": set(),
            "payload_keys": set(),
            "sample_frame": e.frame,
        }
    if e.category:
        event_fields[e.event]["categories"].add(e.category)
    if isinstance(e.payload, dict):
        event_fields[e.event]["payload_keys"].update(e.payload.keys())

for ev, data in sorted(event_fields.items()):
    cat_str = ", ".join(data["categories"])
    keys_str = ", ".join(sorted(data["payload_keys"]))
    print(f"- **`{ev}`** (count: {ev_counter[ev]}, category: `{cat_str}`): fields: `{keys_str}`")

# Also print session time range and frames
print(f"\nTime range: {sess.events[0].session_time:.2f}s (frame {sess.events[0].frame}) to {sess.events[-1].session_time:.2f}s (frame {sess.events[-1].frame})")
print(f"Snapshots count: {len(sess.snapshots)}")
if sess.snapshots:
    print(f"Snapshot frame range: {sess.snapshots[0].frame} to {sess.snapshots[-1].frame}")

