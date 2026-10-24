import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import json
from loader import resolve_log_path, load_sessions

sessions = load_sessions(resolve_log_path(), stride=4)

for sid in ['session_1792777856_45957', 'session_1792785118_99684']:
    sess = sessions[sid]
    findings = json.load(open(f'results/agent_notes/{sid}_findings.json'))
    
    all_times = [s.session_time for s in sess.snapshots] + [e.session_time for e in sess.events]
    max_t = max(all_times) if all_times else 0.0
    cur_t = 0.0
    w_idx = 0
    windows = []
    while cur_t <= max_t + 0.1:
        next_t = cur_t + 5.0
        w_snaps = [s for s in sess.snapshots if cur_t <= s.session_time < next_t]
        w_events = [e for e in sess.events if cur_t <= e.session_time < next_t]
        if w_snaps or w_events:
            w_id = f'w{w_idx:02d}'
            min_f = min([e.frame for e in w_events] + [s.frame for s in w_snaps])
            max_f = max([e.frame for e in w_events] + [s.frame for s in w_snaps])
            windows.append({
                'w_id': w_id,
                'start_t': cur_t,
                'end_t': next_t,
                'min_f': min_f,
                'max_f': max_f,
                'n_events': len(w_events),
                'n_snaps': len(w_snaps)
            })
        cur_t = next_t
        w_idx += 1
        
    print(f'=== Session: {sid} ===')
    for f in findings:
        target_f = f['evidence_frames'][0]
        matched_w = None
        for w in windows:
            if w['min_f'] <= target_f <= w['max_f']:
                matched_w = w
                break
        if not matched_w:
            matched_w = min(windows, key=lambda w: min(abs(w['min_f'] - target_f), abs(w['max_f'] - target_f)))
        print(f'Finding: "{f["title"][:45]}" | frame: {target_f} -> window: {matched_w["w_id"]} [frames {matched_w["min_f"]}..{matched_w["max_f"]}]')

