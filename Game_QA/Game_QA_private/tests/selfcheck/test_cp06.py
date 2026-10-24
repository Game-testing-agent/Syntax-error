import sys
from pathlib import Path

# Add repo root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import shutil
from loader import resolve_log_path, load_sessions

log_path = Path(resolve_log_path())
bad_path = Path("results/selfcheck/tmp/bad.jsonl")

# Copy telemetry
shutil.copy2(log_path, bad_path)

# Append one broken JSON line and one missing required field line
with open(bad_path, "a", encoding="utf-8") as f:
    f.write("\n{this is broken json: definitely not valid}\n")
    f.write('{"category": "test", "foo": "bar"}\n')  # missing required fields (session_id, etc.)

print("Appended malformed lines to results/selfcheck/tmp/bad.jsonl")

try:
    sessions = load_sessions(str(bad_path), stride=1)
    print("SUCCESS: load_sessions did not crash.")
    total_events = sum(len(s.events) for s in sessions.values())
    total_snaps = sum(len(s.snapshots) for s in sessions.values())
    print(f"Parsed {total_events} events, {total_snaps} snapshots.")
    # Check if broken lines produced fake sessions or events
    session_ids = list(sessions.keys())
    print(f"Session IDs: {session_ids}")
except Exception as e:
    print(f"CRASH: {type(e).__name__}: {e}")
