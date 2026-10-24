import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from loader import resolve_log_path, load_sessions

log_path = resolve_log_path()
sessions = load_sessions(log_path, stride=1)
sess = list(sessions.values())[0]

all_times = [s.session_time for s in sess.snapshots] + [e.session_time for e in sess.events]
max_t = max(all_times) if all_times else 0.0

window_sec = 5.0
cur_t = 0.0
w_idx = 0

window_durations = []
while cur_t <= max_t + 0.1:
    next_t = cur_t + window_sec
    w_snaps = [s for s in sess.snapshots if cur_t <= s.session_time < next_t]
    if w_snaps:
        actual_start = w_snaps[0].session_time
        actual_end = w_snaps[-1].session_time
        span = actual_end - actual_start
        fps_vals = [s.fps for s in w_snaps if s.fps > 0]
        avg_fps = sum(fps_vals) / len(fps_vals) if fps_vals else 60.0
        frame_span = w_snaps[-1].frame - w_snaps[0].frame
        window_durations.append((f"w{w_idx:02d}", cur_t, next_t, len(w_snaps), actual_start, actual_end, span, avg_fps, frame_span))
    cur_t = next_t
    w_idx += 1

print(f"Total evaluated windows with snapshots: {len(window_durations)}")
for w in window_durations[:5]:
    wid, t0, t1, n_snaps, act_t0, act_t1, span, fps, f_span = w
    print(f"{wid}: target={t0:.1f}s-{t1:.1f}s | snaps={n_snaps} | actual={act_t0:.2f}s-{act_t1:.2f}s (span={span:.2f}s) | avg_fps={fps:.1f} | frames={f_span}")

