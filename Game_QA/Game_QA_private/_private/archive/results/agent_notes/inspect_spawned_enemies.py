import json

sid = "session_1792857656_89907"
with open(r"..\Syntax-error\game_events.jsonl", "r", encoding="utf-8") as f:
    for line in f:
        if not line.strip():
            continue
        ev = json.loads(line)
        if ev.get("session_id") == sid and ev.get("event_name") == "enemy_spawned":
            print(f"Spawned: {ev.get('data')}")

