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

for sid, records in sessions.items():
    print(f"\n=======================================================")
    print(f"SESSION: {sid} (total {len(records)} records)")
    
    # Event breakdown
    events_count = {}
    for r in records:
        en = r.get("event_name")
        if en:
            events_count[en] = events_count.get(en, 0) + 1
            
    print("Events count:")
    for en, cnt in sorted(events_count.items()):
        if any(k in en for k in ["anomaly", "bug", "died", "stomp", "portal", "retry", "contact", "fall", "player_stuck", "pick"]):
            print(f"  {en}: {cnt}")
            
    # Print all anomalies and bug triggers with details
    triggers = [r for r in records if r.get("event_name") in ["bug_trigger", "anomaly"] or r.get("category") == "anomaly"]
    print(f"\nSpecial triggers/anomalies ({len(triggers)}):")
    for t in triggers:
        print(f"  Frame {t.get('physics_frame')}: {t.get('event_name')} -> {t.get('data')}")

