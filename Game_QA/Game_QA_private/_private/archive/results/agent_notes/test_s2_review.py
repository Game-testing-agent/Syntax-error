import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from loader import load_sessions, resolve_log_path
from llm import review_window
from schemas import ReviewWindow

sessions = load_sessions(resolve_log_path(None), stride=4)
sess = sessions["session_1792857656_89907"]

all_times = [s.session_time for s in sess.snapshots] + [e.session_time for e in sess.events]
max_t = max(all_times) if all_times else 0.0

cur_t = 0.0
w_idx = 0
window_sec = 5.0

while cur_t <= max_t + 0.1:
    next_t = cur_t + window_sec
    w_snaps = [s for s in sess.snapshots if cur_t <= s.session_time < next_t]
    w_events = [e for e in sess.events if cur_t <= e.session_time < next_t]

    if w_snaps or w_events:
        curr_id = f"w{w_idx:02d}"
        rw = ReviewWindow(
            window_id=curr_id,
            session_id=sess.session_id,
            scene=w_snaps[0].scene if w_snaps else (w_events[0].scene or ""),
            start_frame=w_snaps[0].frame if w_snaps else (w_events[0].frame if w_events else 0),
            end_frame=w_snaps[-1].frame if w_snaps else (w_events[-1].frame if w_events else 0),
            snapshots=w_snaps,
            events=w_events,
            active_checks=[],
        )
        f = review_window(rw)
        if f:
            print(f"Window {curr_id} returned finding: [{f.severity}] {f.title} (code: {f.suspected_code})")
        else:
            print(f"Window {curr_id}: None")

    cur_t = next_t
    w_idx += 1

