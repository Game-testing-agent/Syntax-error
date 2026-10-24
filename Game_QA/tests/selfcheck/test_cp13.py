import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from loader import resolve_log_path, load_sessions
from schemas import ReviewWindow

log_path = resolve_log_path()
# test with stride=1 to check all events
sessions = load_sessions(log_path, stride=1)
sess = list(sessions.values())[0]

window_sec = 5.0
all_times = [s.session_time for s in sess.snapshots] + [e.session_time for e in sess.events]
max_t = max(all_times) if all_times else 0.0

cur_t = 0.0
w_idx = 0
windows = []

while cur_t <= max_t + 0.1:
    next_t = cur_t + window_sec
    w_snaps = [s for s in sess.snapshots if cur_t <= s.session_time < next_t]
    w_events = [e for e in sess.events if cur_t <= e.session_time < next_t]
    if w_snaps or w_events:
        windows.append((f"w{w_idx:02d}", cur_t, next_t, w_events, w_snaps))
    cur_t = next_t
    w_idx += 1

total_events_in_session = len(sess.events)
total_events_across_windows = sum(len(w[3]) for w in windows)

# Check each event membership
event_window_counts = {}
for w in windows:
    for e in w[3]:
        event_window_counts[id(e)] = event_window_counts.get(id(e), 0) + 1

multi_window = [eid for eid, count in event_window_counts.items() if count > 1]
zero_window = [e for e in sess.events if id(e) not in event_window_counts]

print(f"Total events in session: {total_events_in_session}")
print(f"Total events across windows: {total_events_across_windows}")
print(f"Events in >1 window: {len(multi_window)}")
print(f"Events in 0 windows: {len(zero_window)}")
print(f"Window count: {len(windows)}")
if windows:
    print(f"First window: {windows[0][0]} [{windows[0][1]}s - {windows[0][2]}s], events={len(windows[0][3])}")
    print(f"Last window: {windows[-1][0]} [{windows[-1][1]}s - {windows[-1][2]}s], events={len(windows[-1][3])}")
