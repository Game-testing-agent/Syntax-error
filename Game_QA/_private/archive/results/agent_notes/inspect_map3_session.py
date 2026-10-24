import json

with open(r"..\Syntax-error\game_events.jsonl", "r", encoding="utf-8") as f:
    events = [json.loads(line) for line in f if line.strip()]

print(f"Total events: {len(events)}")

# Find all bug_triggers and anomalies
special = [e for e in events if e.get("event_name") in ["bug_trigger", "anomaly"] or e.get("category") == "anomaly"]
print(f"Total anomalies & bug triggers: {len(special)}")
for s in special:
    print(f"Frame {s.get('physics_frame')}: {s.get('event_name')} -> {s.get('data')}")

# Check key transitions and lifecycle
print("\nKey transitions & lifecycle:")
for e in events:
    en = e.get("event_name") or ""
    if any(k in en for k in ["portal", "teleport", "died", "stomp", "unexpected_player_removal", "level", "scene"]):
        print(f"Frame {e.get('physics_frame')}: {en} -> {e.get('data')}")

