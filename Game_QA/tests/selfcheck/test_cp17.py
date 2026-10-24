import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from loader import resolve_log_path, load_sessions
from checker import check_event, violations_to_findings

log_path = resolve_log_path()
sessions = load_sessions(log_path, stride=1)
sess = list(sessions.values())[0]

anomaly_events = [e for e in sess.events if e.category == "anomaly" or "anomaly" in e.event]
violations = []
for e in anomaly_events:
    v = check_event(e)
    if v:
        violations.append((e, v))

findings = violations_to_findings([v for e, v in violations], {})

print(f"Total anomaly events in telemetry: {len(anomaly_events)}")
print(f"Violations produced from anomaly events: {len(violations)}")
print(f"Aggregated Path 1 findings produced: {len(findings)}")

for f in findings:
    print(f"  Finding: {f.title} | Severity: {f.severity} | Evidence frames count: {len(f.evidence_frames)}")
    print(f"    Sample frames: {f.evidence_frames[:5]}")
