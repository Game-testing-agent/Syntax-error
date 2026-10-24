import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
import json
from loader import load_sessions, resolve_log_path

sessions = load_sessions(resolve_log_path(None), stride=4)
sess = sessions["session_1792846649_48218"]

all_times = [s.session_time for s in sess.snapshots] + [e.session_time for e in sess.events]
max_t = max(all_times) if all_times else 0.0

cur_t = 0.0
w_idx = 0
window_sec = 5.0

print(f"Max time: {max_t:.2f}s")
while cur_t <= max_t + 0.1:
    next_t = cur_t + window_sec
    w_snaps = [s for s in sess.snapshots if cur_t <= s.session_time < next_t]
    w_events = [e for e in sess.events if cur_t <= e.session_time < next_t]

    curr_id = f"w{w_idx:02d}"
    print(f"Window {curr_id}: t=[{cur_t:.1f}, {next_t:.1f}) snaps={len(w_snaps)} events={len(w_events)}")
    for ev in w_events:
        if ev.event in ["bug_trigger", "unexpected_score_change", "unexpected_player_removal", "quit_pressed"]:
            print(f"   -> Event {ev.event} at t={ev.session_time:.2f} frame={ev.frame} payload={ev.payload}")
    cur_t = next_t
    w_idx += 1
