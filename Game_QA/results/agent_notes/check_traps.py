import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from loader import resolve_log_path, load_sessions

log_path = resolve_log_path()
sessions = load_sessions(log_path, stride=1)
sess = sessions["session_1792862072_26412"]

print("=== CHECKING CORNER PIN AND STEP ALIGN ===")
# Corner pin: x in [4360, 4440], y in [600, 680]
# Step align: x in [5420, 5460], y in [540, 580]
for e in sess.events:
    p = e.payload.get("player")
    pos = p.get("position") if isinstance(p, dict) else None
    if not pos:
        pos = e.payload.get("to_position") or e.payload.get("position")
    if isinstance(pos, dict):
        x = pos.get("x", 0)
        y = pos.get("y", 0)
        if 4360 <= x <= 4440 and 600 <= y <= 680:
            print(f"Corner pin range hit: Frame {e.frame} ({e.event}): pos=({x}, {y})")
        if 5420 <= x <= 5460 and 540 <= y <= 580:
            print(f"Step align range hit: Frame {e.frame} ({e.event}): pos=({x}, {y})")

print("\n=== CHECKING ENEMY CONTACT EVENTS ===")
contacts = [e for e in sess.events if "contact" in e.event]
print(f"Contact events ({len(contacts)}):")
for c in contacts:
    print(f"  Frame {c.frame}: {c.event} -> {c.payload}")

print("\n=== CHECKING ENEMY REVERSALS ON ENEMY4 ===")
e4_revs = [e for e in sess.events if e.event == "enemy_reversed_at_wall" and e.payload.get("entity", {}).get("name") == "Enemy4"]
print(f"Enemy4 wall reversals ({len(e4_revs)}):")
for r in e4_revs:
    print(f"  Frame {r.frame}: old={r.payload.get('old_direction')} new={r.payload.get('new_direction')} pos={r.payload.get('position')}")

print("\n=== CHECKING ALL ANOMALIES IN THE SESSION ===")
anomalies = [e for e in sess.events if e.category == "anomaly"]
for a in anomalies:
    print(f"  Frame {a.frame}: {a.event} -> {a.payload}")

