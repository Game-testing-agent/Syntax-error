import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from loader import resolve_log_path, load_sessions

log_path = resolve_log_path()
s1 = load_sessions(log_path, stride=1)
s4 = load_sessions(log_path, stride=4)
sid = list(s1.keys())[0]

c1 = Counter(e.event for e in s1[sid].events)
c4 = Counter(e.event for e in s4[sid].events)

print(f"{'Event Type':<35} | {'Count @ 1':<10} | {'Count @ 4':<10}")
print("-" * 60)
for k in sorted(c1.keys()):
    print(f"{k:<35} | {c1[k]:<10} | {c4[k]:<10}")

print("-" * 60)
print(f"Snapshots count @ stride 1: {len(s1[sid].snapshots)}")
print(f"Snapshots count @ stride 4: {len(s4[sid].snapshots)}")

