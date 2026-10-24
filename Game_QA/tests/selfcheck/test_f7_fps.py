import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from loader import resolve_log_path, load_sessions
from schemas import Check, Snapshot
from checker import check_snapshot

with open("data/checks.json", "r", encoding="utf-8") as f:
    checks_data = json.load(f)["checks"]
checks = [Check(**c) for c in checks_data]
fps_check = [c for c in checks if c.id == "c_fps_healthy"]

# 1. Clean slice test: Frame 92 scene-load snapshot (2.0 FPS, game_state='main_menu')
snap_startup = Snapshot(
    frame=92,
    session_time=0.96,
    timestamp=1792777857.044,
    scene="MainScreen",
    game_state="main_menu",
    fps=2.0,
    player={"alive": False},
    enemies={},
    coins={},
    goal={},
    inputs={},
    stats={},
)
v_startup = check_snapshot(snap_startup, fps_check, [])
pass_startup = (len(v_startup) == 0)
print(f"1. Startup snapshot (2.0 FPS, main_menu) silent: {'PASS' if pass_startup else 'FAIL'} (violations: {len(v_startup)})")

# 2. Injected sustained low-fps during active gameplay (5.0 FPS, game_state='playing')
snap_gameplay_bad = Snapshot(
    frame=500,
    session_time=5.0,
    timestamp=1792777860.0,
    scene="Level01",
    game_state="playing",
    fps=5.0,
    player={"alive": True},
    enemies={},
    coins={},
    goal={},
    inputs={},
    stats={},
)
v_gameplay = check_snapshot(snap_gameplay_bad, fps_check, [])
pass_gameplay = (len(v_gameplay) == 1)
print(f"2. Active gameplay low FPS (5.0 FPS, playing) flagged: {'PASS' if pass_gameplay else 'FAIL'} (violations: {len(v_gameplay)})")

success = pass_startup and pass_gameplay
print(f"\nF7 TEST RESULT: {'PASS' if success else 'FAIL'}")
sys.exit(0 if success else 1)

