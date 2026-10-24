import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from loader import resolve_log_path, load_sessions

log_path = resolve_log_path()
sessions = load_sessions(log_path, stride=1)
sess = sessions["session_1792862072_26412"]

events_to_check = [424, 690, 834, 880, 934, 1003, 1124, 1206, 1706, 1820]
for target in events_to_check:
    evs = [e for e in sess.events if e.frame == target]
    for e in evs:
        w_idx = int(e.session_time // 5.0)
        print(f"Frame {e.frame:5d} ({e.event:25s}): t={e.session_time:5.2f}s -> Window w{w_idx:02d}")

