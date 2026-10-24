import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from loader import resolve_log_path, load_sessions
from schemas import ReviewWindow
import json

log_path = resolve_log_path()
sessions = load_sessions(log_path, stride=1)
sess = sessions["session_1792862072_26412"]

window_sec = 5.0
all_times = [s.session_time for s in sess.snapshots] + [e.session_time for e in sess.events]
max_t = max(all_times) if all_times else 0.0
cur_t = 0.0
w_idx = 0

print("=== DEEP AUDIT OF ALL 9 WINDOWS ===")

while cur_t <= max_t + 0.1:
    next_t = cur_t + window_sec
    w_snaps = [s for s in sess.snapshots if cur_t <= s.session_time < next_t]
    w_events = [e for e in sess.events if cur_t <= e.session_time < next_t]
    
    if w_snaps or w_events:
        wid = f"w{w_idx:02d}"
        print(f"\n==========================================")
        print(f"WINDOW {wid} (t={cur_t:.1f}s to {next_t:.1f}s, {len(w_events)} events, {len(w_snaps)} snaps)")
        print(f"==========================================")
        
        # Check non-player_moved events
        significant_events = [e for e in w_events if e.event != "player_moved"]
        print(f"Significant events ({len(significant_events)}):")
        for e in significant_events:
            print(f"  Frame {e.frame:5d} ({e.session_time:5.2f}s) | {e.category:12s} | {e.event:30s} | {e.payload}")
            
        # Snapshot player y range
        if w_snaps:
            ys = [s.player.get("y", 0.0) for s in w_snaps if s.player]
            scores = [s.stats.get("score", 0) for s in w_snaps if s.stats]
            deaths = [s.stats.get("deaths", 0) for s in w_snaps if s.stats]
            print(f"Snapshots stats: Y range: [{min(ys) if ys else 0:.1f}, {max(ys) if ys else 0:.1f}], Scores: {scores}, Deaths: {deaths}")
            
    cur_t = next_t
    w_idx += 1

