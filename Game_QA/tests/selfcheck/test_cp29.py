import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from loader import resolve_log_path, load_sessions

with open("data/truth.json", "r", encoding="utf-8") as f:
    truth = json.load(f)

log_path = resolve_log_path()
sessions = load_sessions(log_path, stride=1)
active_sessions = set(sessions.keys())

print("Active telemetry sessions in pipeline:", active_sessions)
print(f"{'Session in truth.json':<30} | {'Expected Bug':<28} | {'Telemetry Found?'}")
print("-" * 75)

all_reachable = True
for sid, t_data in truth.items():
    bugs = t_data.get("expected_bugs", [])
    in_active = sid in active_sessions
    if not in_active:
        all_reachable = False
    if not bugs:
        print(f"{sid:<30} | {'[None / Empty List]':<28} | {in_active}")
    for b in bugs:
        print(f"{sid:<30} | {b.get('title', ''):<28} | {in_active}")

print("CP-29 ALL TRUTH BUGS REACHABLE:", all_reachable)

