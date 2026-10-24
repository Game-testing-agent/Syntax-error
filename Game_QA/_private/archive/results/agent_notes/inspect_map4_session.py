import json
from pathlib import Path

log_path = Path(r"..\Syntax-error\game_events.jsonl")

events = []
with open(log_path, "r", encoding="utf-8") as f:
    for line in f:
        if not line.strip(): continue
        events.append(json.loads(line))

print(f"Total events in session: {len(events)}")

print("\n--- All distinct event types and counts ---")
counts = {}
for e in events:
    en = e.get("event_name")
    if en:
        counts[en] = counts.get(en, 0) + 1

for en, c in sorted(counts.items()):
    print(f"  {en}: {c}")

print("\n--- Key events (anomalies, bug triggers, portal, lava, deaths) ---")
for e in events:
    en = e.get("event_name") or ""
    cat = e.get("category") or ""
    if any(k in en for k in ["anomaly", "bug", "portal", "lava", "died", "stomp", "hazard", "teleport"]):
        print(f"Frame {e.get('physics_frame')}: {en} -> {e.get('data')}")

