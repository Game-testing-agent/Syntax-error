import json

session_ids = []
with open(r"..\Syntax-error\game_events.jsonl", "r", encoding="utf-8") as f:
    for line in f:
        line = line.strip()
        if not line:
            continue
        try:
            ev = json.loads(line)
            sid = ev.get("session_id")
            if sid and sid not in session_ids:
                session_ids.append(sid)
        except Exception:
            pass

print("Session IDs in log:", session_ids)
new_sid = session_ids[-1]
print(f"Auditing new session: {new_sid}")

new_events = []
with open(r"..\Syntax-error\game_events.jsonl", "r", encoding="utf-8") as f:
    for line in f:
        if not line.strip():
            continue
        ev = json.loads(line)
        if ev.get("session_id") == new_sid:
            new_events.append(ev)

print(f"Total events in {new_sid}: {len(new_events)}")

# Filter bugs and anomalies
anomalies = [e for e in new_events if e.get("event_name") in ["bug_trigger", "anomaly"] or e.get("category") == "anomaly"]
print(f"Total anomalies & bug triggers in {new_sid}: {len(anomalies)}")
for a in anomalies:
    print(f"  Frame {a.get('physics_frame')}: {a.get('event_name')} -> {a.get('data')}")

