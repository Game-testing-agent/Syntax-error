import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
import json
from loader import resolve_log_path, load_sessions

log_path = resolve_log_path()
print("Resolved log path:", log_path)

total_lines = 0
non_empty_lines = 0
malformed = 0
snapshots = 0
events = 0
sessions_counts = {}

with open(log_path, "r", encoding="utf-8") as f:
    for line in f:
        total_lines += 1
        line_s = line.strip()
        if not line_s:
            continue
        non_empty_lines += 1
        try:
            record = json.loads(line_s)
        except Exception:
            malformed += 1
            continue
        session_id = record.get("session_id")
        if not session_id or not isinstance(session_id, str):
            malformed += 1
            continue
        if session_id not in sessions_counts:
            sessions_counts[session_id] = {"events": 0, "snapshots": 0, "skipped": 0}
        cat = record.get("category")
        ev_name = record.get("event_name") or record.get("event")
        data = record.get("data", {})
        data_ev = data.get("event") if isinstance(data, dict) else None
        is_snap = (cat == "state_snapshot" or ev_name == "state_snapshot" or data_ev == "state_snapshot")
        if is_snap:
            snapshots += 1
            sessions_counts[session_id]["snapshots"] += 1
        else:
            if not ev_name or not isinstance(ev_name, str):
                malformed += 1
                sessions_counts[session_id]["skipped"] += 1
            else:
                events += 1
                sessions_counts[session_id]["events"] += 1

print(f"Total lines in file: {total_lines}")
print(f"Non-empty lines: {non_empty_lines}")
print(f"Events: {events}")
print(f"Snapshots: {snapshots}")
print(f"Malformed / skipped records: {malformed}")
print(f"Sum (events + snapshots + malformed): {events + snapshots + malformed}")
print(f"Reconciliation check (Sum == Non-empty lines): {events + snapshots + malformed == non_empty_lines}")
for sid, c in sessions_counts.items():
    s_total = c["events"] + c["snapshots"] + c["skipped"]
    print(f"Session {sid}: total_lines={s_total}, events={c['events']}, snapshots={c['snapshots']}, skipped={c['skipped']}")

# Verify against loader.py load_sessions with stride=1
sessions = load_sessions(log_path, stride=1)
for sid, sess in sessions.items():
    print(f"loader.py loaded: Session {sid} with {len(sess.events)} events and {len(sess.snapshots)} snapshots.")
