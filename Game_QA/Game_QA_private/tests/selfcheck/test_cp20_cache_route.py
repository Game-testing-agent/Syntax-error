import sys
import json
import hashlib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from schemas import Finding, Verdict, Severity, ReviewWindow
from code_loader import get_game_codebase_context
from llm import _cache_key, _cache_put, review_window
from loader import resolve_log_path, load_sessions

log_path = resolve_log_path()
sessions = load_sessions(log_path, stride=4)
sess = list(sessions.values())[0]

# Construct review window w00
w_snaps = [s for s in sess.snapshots if 0.0 <= s.session_time < 5.0]
w_events = [e for e in sess.events if 0.0 <= e.session_time < 5.0]

rw = ReviewWindow(
    window_id="w00",
    session_id=sess.session_id,
    scene=w_snaps[0].scene if w_snaps else "",
    start_frame=w_snaps[0].frame if w_snaps else 0,
    end_frame=w_snaps[-1].frame if w_snaps else 0,
    snapshots=w_snaps,
    events=w_events,
    active_checks=[],
)

code_context = get_game_codebase_context(rw.events)
cache_payload = {
    "window_id": rw.window_id,
    "session_id": rw.session_id,
    "scene": rw.scene,
    "start_frame": rw.start_frame,
    "end_frame": rw.end_frame,
    "events_count": len(rw.events),
    "code_hash": hashlib.md5(code_context.encode("utf-8")).hexdigest()[:16],
}
key = _cache_key("audit", json.dumps(cache_payload, sort_keys=True))

dummy_finding = Finding(
    verdict=Verdict.bug,
    severity=Severity.critical,
    confidence=0.99,
    title="CP20 Test Dummy Finding Injected via Cache",
    explanation="Test finding injected into cache key to verify pipeline handoff route.",
    evidence_frames=[12345],
    suspected_code="TestCode.gd:L1",
    path="path2",
    needs_human_review=False,
)

_cache_put(key, dummy_finding.model_dump())
print(f"Placed dummy finding in cache at {key}")

# Now call review_window(rw)
retrieved = review_window(rw)
print(f"Retrieved from review_window: {retrieved.title if retrieved else None}")
matches = retrieved is not None and retrieved.title == dummy_finding.title
print(f"Route functional via cache key: {matches}")

