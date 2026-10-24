import json

sid = "session_1792857656_89907"
with open(r"..\Syntax-error\game_events.jsonl", "r", encoding="utf-8") as f:
    for line in f:
        if not line.strip():
            continue
        ev = json.loads(line)
        if ev.get("session_id") == sid and 1220 <= ev.get("physics_frame", 0) <= 1785:
            en = ev.get("event_name", "")
            if any(k in en for k in ["enemy", "wall", "reverse", "float", "bug"]):
                print(f"Frame {ev.get('physics_frame')}: {en} -> {ev.get('data')}")

