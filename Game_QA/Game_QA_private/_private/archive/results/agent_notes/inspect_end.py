import json

with open("../Syntax-error/game_events.jsonl", "r", encoding="utf-8") as f:
    events = [json.loads(line) for line in f if line.strip()]

for e in events:
    frame = e.get("physics_frame")
    if frame is not None and frame >= 1350:
        print(f"Frame {frame}: {e.get('event_name')} | player: {e.get('data', {}).get('player_position') or e.get('player', {}).get('position')}")

