import json

with open(r"..\Syntax-error\game_events.jsonl", "r", encoding="utf-8") as f:
    events = [json.loads(line) for line in f if line.strip()]

print(f"Total events in session: {len(events)}")

# Print anomalies and bug triggers
special = [e for e in events if e.get("event_name") in ["bug_trigger", "anomaly"] or e.get("category") == "anomaly"]
print(f"\nAnomalies & bug triggers ({len(special)}):")
for s in special:
    print(f"Frame {s.get('physics_frame')}: {s.get('event_name')} -> {s.get('data')}")

# Print key transitions and lifecycle
print("\nKey transitions & lifecycle:")
for e in events:
    en = e.get("event_name") or ""
    if any(k in en for k in ["portal", "teleport", "died", "stomp", "unexpected", "level", "scene", "enemy"]):
        if en in ["portal_entered", "enemy_stomped", "enemy_contact_death", "enemy_contact_started", "player_died", "level_loaded", "scene_loaded", "session_end"]:
            print(f"Frame {e.get('physics_frame')}: {en} -> {e.get('data')}")

