import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from schemas import Check, Snapshot, Event
from checker import check_snapshot, check_event, violations_to_findings

with open("data/checks.json", "r", encoding="utf-8") as f:
    checks_data = json.load(f)["checks"]
checks = [Check(**c) for c in checks_data]
checks_by_id = {c.id: c for c in checks}

# Mutant 1: Snapshot with player.y beyond kill boundary (Y=1450.0 > 1400.0) at frame 9999
m1_snap = Snapshot(
    frame=9999,
    session_time=99.0,
    timestamp=99999.0,
    scene="Level01",
    game_state="playing",
    fps=60.0,
    player={"y": 1450.0, "vel_x": 0.0, "vel_y": 0.0},
    enemies={},
    coins={"coins_remaining": 10},
    goal={},
    inputs={},
    stats={"score": 100, "deaths": 0},
)
v1 = check_snapshot(m1_snap, checks, [])
f1 = violations_to_findings(v1, checks_by_id)

m1_detected = any(9999 in f.evidence_frames for f in f1)
print(f"Mutant 1 (OOB Y=1450.0 at frame 9999): {'PASS' if m1_detected else 'MISSED'}")
if f1:
    print(f"  Finding: {f1[0].title} | Frames: {f1[0].evidence_frames}")

# Mutant 2: Score that decreases without reset event (stats.score drops to negative or unexpected_score_change anomaly)
# Note: In checks.json, predicate is stats.score >= 0. Let's test negative score at frame 9998:
m2_snap = Snapshot(
    frame=9998,
    session_time=98.0,
    timestamp=99998.0,
    scene="Level01",
    game_state="playing",
    fps=60.0,
    player={"y": 500.0, "vel_x": 0.0, "vel_y": 0.0},
    enemies={},
    coins={"coins_remaining": 10},
    goal={},
    inputs={},
    stats={"score": -50, "deaths": 0},
)
v2 = check_snapshot(m2_snap, checks, [])
f2 = violations_to_findings(v2, checks_by_id)
m2_detected = any(9998 in f.evidence_frames for f in f2)
print(f"Mutant 2 (Negative score=-50 at frame 9998): {'PASS' if m2_detected else 'MISSED'}")
if f2:
    print(f"  Finding: {f2[0].title} | Frames: {f2[0].evidence_frames}")

# Also test Mutant 2 as unexpected_score_change anomaly event:
m2_ev = Event(
    frame=9997,
    session_time=97.0,
    timestamp=99997.0,
    scene="Level01",
    category="anomaly",
    event="unexpected_score_change",
    payload={"severity": "warning", "expected": "Score should only increase", "observed": "Score decreased by 10"},
)
v2_ev = check_event(m2_ev)
f2_ev = violations_to_findings([v2_ev] if v2_ev else [], checks_by_id)
m2_ev_detected = any(9997 in f.evidence_frames for f in f2_ev)
print(f"Mutant 2 (Anomaly event at frame 9997): {'PASS' if m2_ev_detected else 'MISSED'}")

# Mutant 3: Same coin pickup event duplicated (duplicate_pickup_attempt anomaly event at frame 9996)
m3_ev = Event(
    frame=9996,
    session_time=96.0,
    timestamp=99996.0,
    scene="Level01",
    category="anomaly",
    event="duplicate_pickup_attempt",
    payload={"severity": "warning", "expected": "Coin body_entered should not trigger after collection", "observed": "Duplicate body_entered on collected coin"},
)
v3_ev = check_event(m3_ev)
f3_ev = violations_to_findings([v3_ev] if v3_ev else [], checks_by_id)
m3_detected = any(9996 in f.evidence_frames for f in f3_ev)
print(f"Mutant 3 (Duplicate coin pickup anomaly at frame 9996): {'PASS' if m3_detected else 'MISSED'}")
if f3_ev:
    print(f"  Finding: {f3_ev[0].title} | Frames: {f3_ev[0].evidence_frames}")

all_detected = m1_detected and (m2_detected or m2_ev_detected) and m3_detected
print("CP-19 ALL MUTANTS DETECTED:", all_detected)

