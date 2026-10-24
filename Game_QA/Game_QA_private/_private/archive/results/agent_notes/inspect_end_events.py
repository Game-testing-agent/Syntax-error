import json

with open(r"..\Syntax-error\game_events.jsonl", "r", encoding="utf-8") as f:
    events = [json.loads(line) for line in f if line.strip()]

for e in events:
    if e.get("physics_frame", 0) >= 1200:
        print(f"Frame {e.get('physics_frame')}: {e.get('event_name')} -> {e.get('data')}")

