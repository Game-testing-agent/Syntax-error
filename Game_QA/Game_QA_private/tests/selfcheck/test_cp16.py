import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from schemas import Check, Snapshot
from checker import check_snapshot

with open("data/checks.json", "r", encoding="utf-8") as f:
    checks_data = json.load(f)["checks"]

checks = [Check(**c) for c in checks_data]

def make_snap(**kwargs):
    d = {
        "frame": 100,
        "session_time": 1.0,
        "timestamp": 1000.0,
        "scene": "Level01",
        "game_state": "playing",
        "fps": 60.0,
        "player": {"y": 500.0, "vel_x": 100.0, "vel_y": 100.0},
        "enemies": {},
        "coins": {"coins_remaining": 10},
        "goal": {},
        "inputs": {},
        "stats": {"score": 100, "deaths": 0},
    }
    # Deep update
    for k, v in kwargs.items():
        if isinstance(v, dict) and k in d and isinstance(d[k], dict):
            d[k].update(v)
        else:
            d[k] = v
    return Snapshot(**d)

results = []
all_passed = True

test_cases = [
    (
        "c_player_out_of_bounds",
        "player.y <= 1400.0",
        make_snap(player={"y": 1400.0, "vel_x": 0, "vel_y": 0}),  # Boundary pass
        make_snap(player={"y": 1400.1, "vel_x": 0, "vel_y": 0}),  # Fail
    ),
    (
        "c_score_non_negative",
        "stats.score >= 0",
        make_snap(stats={"score": 0, "deaths": 0}),  # Boundary pass
        make_snap(stats={"score": -1, "deaths": 0}),  # Fail
    ),
    (
        "c_deaths_nonnegative",
        "stats.deaths >= 0",
        make_snap(stats={"score": 0, "deaths": 0}),  # Boundary pass
        make_snap(stats={"score": 0, "deaths": -1}),  # Fail
    ),
    (
        "c_player_velocity_limit",
        "abs(player.vel_x) <= 2500 and abs(player.vel_y) <= 3000",
        make_snap(player={"y": 0, "vel_x": 2500.0, "vel_y": 3000.0}),  # Boundary pass
        make_snap(player={"y": 0, "vel_x": 2500.1, "vel_y": 3000.0}),  # Fail
    ),
    (
        "c_fps_healthy",
        "fps >= 15.0",
        make_snap(fps=15.0),  # Boundary pass
        make_snap(fps=14.9),  # Fail
    ),
    (
        "c_coins_remaining_nonnegative",
        "coins.coins_remaining >= 0",
        make_snap(coins={"coins_remaining": 0}),  # Boundary pass
        make_snap(coins={"coins_remaining": -1}),  # Fail
    ),
]

for check_id, pred, snap_pass, snap_fail in test_cases:
    chk = [c for c in checks if c.id == check_id]
    v_pass = check_snapshot(snap_pass, chk, [])
    v_fail = check_snapshot(snap_fail, chk, [])
    pass_ok = (len(v_pass) == 0)
    fail_ok = (len(v_fail) == 1 and v_fail[0].check_id == check_id)
    overall = pass_ok and fail_ok
    if not overall:
        all_passed = False
    results.append((check_id, pred, pass_ok, fail_ok, overall))
    print(f"Check {check_id:<30}: pass_case_ok={pass_ok:<5} | fail_case_ok={fail_ok:<5} | OVERALL={'PASS' if overall else 'FAIL'}")

print("CP-16 ALL PREDICATES EVALUATED CORRECTLY:", all_passed)

