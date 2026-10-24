import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from schemas import ReviewWindow, Event, Snapshot, Finding, Verdict, Severity
from llm import window_cache_key, review_window
from tools.native_submit import submit_finding

# Base window
ev1 = Event(frame=100, session_time=1.0, timestamp=1000.0, event="coin_picked", payload={"score": 100})
snap1 = Snapshot(frame=100, session_time=1.0, timestamp=1000.0, scene="Level01", game_state="playing", fps=60.0, player={"x": 10.0, "y": 20.0})

w_base = ReviewWindow(
    window_id="w00",
    session_id="session_test",
    scene="Level01",
    start_frame=100,
    end_frame=100,
    snapshots=[snap1],
    events=[ev1],
    active_checks=[],
)

code_base = "extends Player\nfunc _ready(): pass"
key_base = window_cache_key(w_base, code_base)

# Test 1: Change one event field (same count)
ev_mutated = Event(frame=100, session_time=1.0, timestamp=1000.0, event="coin_picked", payload={"score": 90})  # 90 instead of 100
w_mutated = ReviewWindow(
    window_id="w00",
    session_id="session_test",
    scene="Level01",
    start_frame=100,
    end_frame=100,
    snapshots=[snap1],
    events=[ev_mutated],
    active_checks=[],
)
key_mutated = window_cache_key(w_mutated, code_base)
test1_pass = (key_base != key_mutated)
print(f"Test 1: Mutated event field changes key: {'PASS' if test1_pass else 'FAIL'}")
print(f"  Key base:    {key_base.name}")
print(f"  Key mutated: {key_mutated.name}")

# Test 2: Change source code text
code_changed = "extends Player\nfunc _ready(): print('modified')"
key_code_changed = window_cache_key(w_base, code_changed)
test2_pass = (key_base != key_code_changed)
print(f"Test 2: Changed code text changes key: {'PASS' if test2_pass else 'FAIL'}")
print(f"  Key code changed: {key_code_changed.name}")

# Test 3: Submit via native_submit tool and retrieve via review_window
dummy_finding = Finding(
    verdict=Verdict.bug,
    severity=Severity.high,
    confidence=0.98,
    title="Tool Submission Integrity Test",
    explanation="Verified tool-based handoff through content-addressed cache.",
    evidence_frames=[100],
    suspected_code="Test.gd:L10",
    path="path2",
    needs_human_review=False,
)
tmp_finding_file = Path("results/selfcheck/tmp/submit_test_finding.json")
tmp_finding_file.write_text(json.dumps([dummy_finding.model_dump()], indent=2), encoding="utf-8")

from loader import resolve_log_path, load_sessions
from code_loader import get_game_codebase_context

resolved_log = resolve_log_path()
sessions = load_sessions(resolved_log, stride=4)
first_session_id = next(iter(sessions.keys()))

cache_dest = submit_finding(
    session_id=first_session_id,
    window_id="w00",
    findings_path=tmp_finding_file,
    stride=4,
)

sess = sessions[first_session_id]
w00_snaps = [s for s in sess.snapshots if 0.0 <= s.session_time < 5.0]
w00_events = [e for e in sess.events if 0.0 <= e.session_time < 5.0]
w00 = ReviewWindow(
    window_id="w00",
    session_id=sess.session_id,
    scene=w00_snaps[0].scene if w00_snaps else "",
    start_frame=w00_snaps[0].frame if w00_snaps else 0,
    end_frame=w00_snaps[-1].frame if w00_snaps else 0,
    snapshots=w00_snaps,
    events=w00_events,
    active_checks=[],
)
retrieved = review_window(w00)
test3_pass = (retrieved is not None and retrieved.title == dummy_finding.title and retrieved.evidence_frames == [100])
print(f"Test 3: Tool submission retrieves cleanly: {'PASS' if test3_pass else 'FAIL'}")
if retrieved:
    print(f"  Retrieved title: {retrieved.title} | Code: {retrieved.suspected_code}")

# Clean up test cache file
if cache_dest.exists():
    cache_dest.unlink()

overall = test1_pass and test2_pass and test3_pass
print(f"F4 VERIFICATION OVERALL: {'PASS' if overall else 'FAIL'}")
sys.exit(0 if overall else 1)

