import json

sid = "session_1792857656_89907"
with open(r"..\Syntax-error\game_events.jsonl", "r", encoding="utf-8") as f:
    events = [json.loads(line) for line in f if line.strip() and json.loads(line).get("session_id") == sid]

print(f"Total events: {len(events)}")
for e in events:
    en = e.get("event_name") or ""
    if any(k in en for k in ["scene", "map", "loaded", "portal", "teleport", "died", "stomp", "contact", "kill", "hazard", "fall", "quit", "end"]):
        print(f"Frame {e.get('physics_frame')}: {en} -> {e.get('data')}")

