import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from loader import resolve_log_path, load_sessions

log_path = resolve_log_path()
s1 = load_sessions(log_path, stride=1)
s4 = load_sessions(log_path, stride=4)

sid = list(s1.keys())[0]
ev1 = s1[sid].events
ev4 = s4[sid].events
snaps1 = s1[sid].snapshots
snaps4 = s4[sid].snapshots

c1 = Counter(e.event for e in ev1 if e.event != "state_snapshot")
c4 = Counter(e.event for e in ev4 if e.event != "state_snapshot")

all_types = sorted(set(c1.keys()) | set(c4.keys()))

mismatches = []
for t in all_types:
    if c1[t] != c4[t]:
        mismatches.append((t, c1[t], c4[t]))

print(f"Total event types compared: {len(all_types)}")
print(f"Mismatched event types between stride 1 and stride 4: {len(mismatches)}")
for m in mismatches[:10]:
    print(f"  {m[0]}: count@1={m[1]} vs count@4={m[2]}")

print(f"Snapshots: stride 1 = {len(snaps1)} | stride 4 = {len(snaps4)}")
target_quarter = len(snaps1) / 4.0
print(f"Target ~quarter of snapshots: {target_quarter:.1f}")

critical_events = ["player_died", "enemy_stomped", "scene_change_pressed"]
critical_present = all(c4[e] > 0 for e in critical_events)
for ce in critical_events:
    print(f"Critical event '{ce}': count@4 = {c4[ce]}")

success = (len(mismatches) == 0 and critical_present and (0.2 * len(snaps1) <= len(snaps4) <= 0.3 * len(snaps1)))
print("F2 TEST RESULT:", "PASS" if success else "FAIL")
sys.exit(0 if success else 1)

