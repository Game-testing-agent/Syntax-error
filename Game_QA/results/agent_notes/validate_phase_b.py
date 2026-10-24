import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
import json
from schemas import Finding
from loader import resolve_log_path, load_sessions

log_path = resolve_log_path()
sessions = load_sessions(log_path, stride=1)
sess = sessions["session_1792862072_26412"]

# 1. Pydantic validation
findings_file = Path(__file__).parent / "session_1792862072_26412_findings.json"
data = json.loads(findings_file.read_text(encoding="utf-8"))
findings = [Finding.model_validate(item) for item in data]
print(f"Pydantic validation: PASS ({len(findings)} findings parsed)")

# 2. Frame & event existence check
all_event_frames = {e.frame: e.event for e in sess.events}
all_events_by_frame = {}
for e in sess.events:
    all_events_by_frame.setdefault(e.frame, []).append(e.event)
for s in sess.snapshots:
    all_events_by_frame.setdefault(s.frame, []).append("snapshot")

all_valid = True
for f in findings:
    print(f"\nValidating finding: '{f.title}'")
    for frame in f.evidence_frames:
        if frame not in all_events_by_frame:
            print(f"  FAIL: Frame {frame} not found in telemetry!")
            all_valid = False
        else:
            evs = all_events_by_frame[frame]
            print(f"  OK: Frame {frame} present in telemetry (events: {evs[:3]})")

# 3. Suspected code check
print("\nValidating suspected_code citations:")
for f in findings:
    print(f"Finding: {f.title}")
    print(f"  suspected_code: {f.suspected_code}")
    # Verify file exists
    parts = f.suspected_code.split(":")
    fname = parts[0]
    # Check in game_src
    src_file = next(Path("game_src").rglob(fname), None)
    if not src_file or not src_file.exists():
        print(f"  FAIL: Source file {fname} not found!")
        all_valid = False
    else:
        print(f"  OK: Source file {src_file} exists.")

print(f"\nOverall B4 validation status: {'PASS' if all_valid else 'FAIL'}")

