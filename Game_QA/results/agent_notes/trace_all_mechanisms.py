import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from loader import resolve_log_path, load_sessions

log_path = resolve_log_path()
sessions = load_sessions(log_path, stride=1)
sess = sessions["session_1792862072_26412"]

print("=== 1. COLLECTIBLE & SCORE TRACE ===")
coins_picked = [e for e in sess.events if e.event == "coin_picked"]
score_awarded = [e for e in sess.events if e.event == "coin_score_awarded"]
score_anomalies = [e for e in sess.events if e.event == "unexpected_score_change"]
enemy_kills = [e for e in sess.events if e.event == "enemy_killed"]

print(f"Total coins picked: {len(coins_picked)}")
for idx, (cp, sa) in enumerate(zip(coins_picked, score_awarded), start=1):
    c_name = cp.payload.get("entity", {}).get("name") if cp.payload.get("entity") else "Unknown"
    s_gain = sa.payload.get("score_gain")
    s_before = sa.payload.get("score_before")
    s_after = sa.payload.get("score_after")
    print(f"Coin #{idx} ({c_name}) at frame {cp.frame}: gain={s_gain}, before={s_before}, after={s_after}")

print(f"\nTotal enemy kills: {len(enemy_kills)}")
for ek in enemy_kills:
    e_name = ek.payload.get("entity", {}).get("name") if ek.payload.get("entity") else "Unknown"
    s_gain = ek.payload.get("score_gain")
    s_before = ek.payload.get("score_before")
    s_after = ek.payload.get("score_after")
    print(f"Kill ({e_name}) at frame {ek.frame}: gain={s_gain}, before={s_before}, after={s_after}")

print(f"\nScore anomalies ({len(score_anomalies)}):")
for a in score_anomalies:
    print(f"  Frame {a.frame}: old={a.payload['details']['old_score']}, new={a.payload['details']['new_score']}, delta={a.payload['details']['delta']}")

print("\n=== 2. ENEMY INTERACTIONS TRACE ===")
stomps = [e for e in sess.events if e.event == "stomp_attempted"]
stomp_success = [e for e in sess.events if e.event == "enemy_stomped"]
wall_revs = [e for e in sess.events if e.event == "enemy_reversed_at_wall"]
enemy_spawns = [e for e in sess.events if e.event == "enemy_spawned"]

print(f"Total enemies spawned: {len(enemy_spawns)}")
print(f"Stomp attempts: {len(stomps)}, Stomp successes: {len(stomp_success)}, Kills: {len(enemy_kills)}")
for s, ss in zip(stomps, stomp_success):
    ename = s.payload.get("entity", {}).get("name") if s.payload.get("entity") else "Unknown"
    print(f"Stomp at frame {s.frame} on {ename}: player_vel_y={s.payload.get('player_velocity_y')}, bounce_vel={ss.payload.get('bounce_velocity')}")

print(f"\nWall reversals ({len(wall_revs)}):")
for wr in wall_revs:
    ename = wr.payload.get("entity", {}).get("name") if wr.payload.get("entity") else "Unknown"
    print(f"  Frame {wr.frame} on {ename}: old_dir={wr.payload.get('old_direction')}, new_dir={wr.payload.get('new_direction')}, pos={wr.payload.get('position')}")

print("\n=== 3. MOVEMENT & POSITION ANOMALIES ===")
oob = [e for e in sess.events if e.event == "player_out_of_bounds"]
print(f"OOB anomalies: {len(oob)}")
for o in oob:
    print(f"  Frame {o.frame}: {o.payload}")

# Check frames where player x is near 4360-4440 (corner pin) and 5420-5460 (step align)
p_moves = [e for e in sess.events if e.event == "player_moved"]
print(f"Total player_moved events: {len(p_moves)}")

# Check for stuck or stopped horizontal velocity while input pressed
inputs = [e for e in sess.events if "pressed" in e.event]
print(f"Input events count: {len(inputs)}")

