import sys
from pathlib import Path
import json

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from loader import resolve_log_path, load_sessions
from schemas import Check
from checker import check_snapshot, check_event, violations_to_findings

log_path = resolve_log_path()
sessions = load_sessions(log_path, stride=1)
sess = list(sessions.values())[0]

with open("data/checks.json", "r", encoding="utf-8") as f:
    checks_data = json.load(f)["checks"]
checks = [Check(**c) for c in checks_data]
checks_by_id = {c.id: c for c in checks}

# Window w00 / frames 200 to 500 is early clean traversal (before first anomaly at frame 578)
clean_events = [e for e in sess.events if 100 <= e.frame <= 500]
clean_snapshots = [s for s in sess.snapshots if 100 <= s.frame <= 500]

violations = []
for e in clean_events:
    v = check_event(e)
    if v:
        violations.append(v)

for s in clean_snapshots:
    vs = check_snapshot(s, checks, [])
    violations.extend(vs)

findings = violations_to_findings(violations, checks_by_id)
print(f"Clean slice events count: {len(clean_events)}")
print(f"Clean slice snapshots count: {len(clean_snapshots)}")
print(f"Violations count: {len(violations)}")
print(f"Findings count: {len(findings)}")
print("CP-18 RESULT:", "PASS" if len(findings) == 0 else "FAIL")

