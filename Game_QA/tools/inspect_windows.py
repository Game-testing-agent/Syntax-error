import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from loader import resolve_log_path, load_sessions
from schemas import ReviewWindow

sessions = load_sessions(resolve_log_path(), stride=4)
sess = sessions['session_1792777856_45957']

all_times = [s.session_time for s in sess.snapshots] + [e.session_time for e in sess.events]
max_t = max(all_times) if all_times else 0.0
cur_t = 0.0
w_idx = 0

print("Exact ReviewWindows for session_1792777856_45957:")
while cur_t <= max_t + 0.1:
    next_t = cur_t + 5.0
    w_snaps = [s for s in sess.snapshots if cur_t <= s.session_time < next_t]
    w_events = [e for e in sess.events if cur_t <= e.session_time < next_t]

    if w_snaps or w_events:
        rw = ReviewWindow(
            window_id=f"w{w_idx:02d}",
            session_id=sess.session_id,
            scene=w_snaps[0].scene if w_snaps else (w_events[0].scene or ""),
            start_frame=w_snaps[0].frame if w_snaps else (w_events[0].frame if w_events else 0),
            end_frame=w_snaps[-1].frame if w_snaps else (w_events[-1].frame if w_events else 0),
            snapshots=w_snaps,
            events=w_events,
        )
        all_frames = [e.frame for e in w_events] + [s.frame for s in w_snaps]
        print(f"{rw.window_id}: t=[{cur_t:.1f}, {next_t:.1f}] rw.start_frame={rw.start_frame}, rw.end_frame={rw.end_frame}, actual_frames=[{min(all_frames)}, {max(all_frames)}]")

    cur_t = next_t
    w_idx += 1

