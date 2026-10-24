import json
from pathlib import Path

with open("../Syntax-error/game_events.jsonl", "r", encoding="utf-8") as f:
    events = [json.loads(line) for line in f if line.strip()]

print(f"Total records: {len(events)}")

# 1. Inspect enemy interactions
print("\n--- ENEMY INTERACTIONS ---")
for e in events:
    ename = e.get("event_name") or ""
    if any(k in ename for k in ["enemy", "stomp", "kill", "contact"]):
        print(f"Frame {e.get('physics_frame')}: {ename} | data: {e.get('data')}")

# 2. Inspect portal / level completion
print("\n--- PORTAL / LEVEL TRANSITIONS ---")
for e in events:
    ename = e.get("event_name") or ""
    if any(k in ename for k in ["portal", "teleport", "level", "scene", "transition"]):
        print(f"Frame {e.get('physics_frame')}: {ename} | data: {e.get('data')}")

# 3. Inspect wall jumps
print("\n--- WALL JUMP / FRICTION ---")
for e in events:
    ename = e.get("event_name") or ""
    if any(k in ename for k in ["wall", "friction"]):
        print(f"Frame {e.get('physics_frame')}: {ename} | data: {e.get('data')}")

