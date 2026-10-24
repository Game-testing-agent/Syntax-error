import json

with open(r"..\Syntax-error\game_events.jsonl", "r", encoding="utf-8") as f:
    events = [json.loads(line) for line in f if line.strip()]

for e in events:
    en = e.get("event_name") or ""
    if any(k in en for k in ["enemy", "stomp", "hurt", "die", "death", "damage", "hole", "fall", "hazard"]):
        print(f"Frame {e.get('physics_frame')}: {en} -> {e.get('data')}")

