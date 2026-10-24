import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from loader import resolve_log_path
from eval import run_evaluation

log_path = resolve_log_path()
dmg_log = Path("results/selfcheck/tmp/damage_bypass_session.jsonl")

# Extract window w01 (frames 500-1000) and inject enemy_contact_started at frame 600 without death event
lines = []
injected = False
with open(log_path, "r", encoding="utf-8") as f:
    for line in f:
        l = line.strip()
        if not l:
            continue
        try:
            obj = json.loads(l)
            pf = obj.get("physics_frame") or obj.get("data", {}).get("frame", 0)
            if 200 <= pf <= 450:
                lines.append(l)
                if pf >= 300 and not injected:
                    inj_event = {
                        "category": "combat",
                        "data": {"enemy_name": "Enemy5"},
                        "elapsed_ms": 3000,
                        "event_name": "enemy_contact_started",
                        "physics_frame": 301,
                        "scene": "res://src/Levels/Level01.tscn",
                        "session_id": "session_1792777856_45957",
                        "timestamp_unix_ms": 1792777859000,
                    }
                    lines.append(json.dumps(inj_event))
                    injected = True
        except Exception:
            pass

dmg_log.write_text("\n".join(lines) + "\n", encoding="utf-8")
print(f"Wrote {len(lines)} lines with injected enemy_contact_started to {dmg_log}")

out_path = Path("results/selfcheck/tmp/damage_eval_results.json")
res = run_evaluation(
    log_path=str(dmg_log),
    out_path=str(out_path),
    stride=1,
    ignore_checks=True,
)

results = res["results"]
findings = []
for r in results:
    findings.extend(r.get("findings", []))

flagged = any("survived sideways enemy contact" in f["title"].lower() or "contact" in f["title"].lower() for f in findings)
print(f"Total findings: {len(findings)}")
for f in findings:
    print(f"  Finding: {f['title']} | Frame: {f['evidence_frames']}")

print(f"Injected damage bypass flagged: {flagged}")
print("CP-34 RESULT:", "PASS" if flagged else "FAIL (MISSED)")
