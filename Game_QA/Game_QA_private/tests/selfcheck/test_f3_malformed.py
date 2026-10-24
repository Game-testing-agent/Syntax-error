import sys
import shutil
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from loader import resolve_log_path, load_sessions

log_path = Path(resolve_log_path())
bad_path = Path("results/selfcheck/tmp/bad_f3.jsonl")

# Copy real telemetry
shutil.copy2(log_path, bad_path)

# Append malformed lines: broken JSON and missing session_id/event_name
with open(bad_path, "a", encoding="utf-8") as f:
    f.write("\n{bad json}\n")
    f.write('{"category": "test", "foo": "bar"}\n')  # missing session_id and event_name
    f.write('{"event_name": "test_no_session", "physics_frame": 10}\n')  # missing session_id

sessions = load_sessions(str(bad_path), stride=1)
fake_sessions = [sid for sid in sessions.keys() if sid == "default_session"]

# Verify real telemetry still parses cleanly
real_sessions = load_sessions(log_path, stride=1)
real_sid = list(real_sessions.keys())[0]
total_events = len(real_sessions[real_sid].events)
total_snaps = len(real_sessions[real_sid].snapshots)

print(f"Fake sessions created in bad file: {fake_sessions}")
print(f"Real session events: {total_events} (expected 1680)")
print(f"Real session snapshots: {total_snaps} (expected 96)")

success = (len(fake_sessions) == 0 and total_events == 1680 and total_snaps == 96)
print("F3 TEST RESULT:", "PASS" if success else "FAIL")
sys.exit(0 if success else 1)

