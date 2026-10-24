import json
from pathlib import Path

log_path = Path(r"..\Syntax-error\game_events.jsonl")

sessions = {}
with open(log_path, "r", encoding="utf-8") as f:
    for line in f:
        if not line.strip(): continue
        rec = json.loads(line)
        sid = rec.get("session_id")
        if sid:
            sessions.setdefault(sid, []).append(rec)

print(f"Total sessions: {len(sessions)}")

for sid, records in sessions.items():
    print(f"\n=======================================================")
    print(f"Session: {sid} (Records: {len(records)})")
    
    events = [r for r in records if r.get("event_name") or r.get("event")]
    snapshots = [r for r in records if r.get("category") == "state_snapshot" or r.get("event_name") == "state_snapshot"]
    anomalies = [r for r in records if r.get("category") == "anomaly" or "anomaly" in str(r.get("event_name"))]
    
    first = records[0]
    last = records[-1]
    
    print(f"  First: frame {first.get('physics_frame')}, t={first.get('session_time')}, event={first.get('event_name')}")
    print(f"  Last:  frame {last.get('physics_frame')}, t={last.get('session_time')}, event={last.get('event_name')}")
    print(f"  Snapshots: {len(snapshots)}, Anomalies: {len(anomalies)}")
    
    for a in anomalies:
        print(f"    [ANOMALY] Frame {a.get('physics_frame')}: {a.get('event_name')} -> {a.get('data')}")
        
    # Check deaths / kills / pickups / portal / game state
    deaths = [r for r in records if "death" in str(r.get("event_name")) or "died" in str(r.get("event_name"))]
    stomps = [r for r in records if "stomp" in str(r.get("event_name"))]
    portals = [r for r in records if "portal" in str(r.get("event_name")) or "teleport" in str(r.get("event_name")) or "goal" in str(r.get("event_name"))]
    
    print(f"  Deaths: {len(deaths)}, Stomps: {len(stomps)}, Portal events: {len(portals)}")
    for d in deaths:
        print(f"    - Death: Frame {d.get('physics_frame')}: {d.get('event_name')} -> {d.get('data')}")
    for p in portals:
        print(f"    - Portal: Frame {p.get('physics_frame')}: {p.get('event_name')} -> {p.get('data')}")

