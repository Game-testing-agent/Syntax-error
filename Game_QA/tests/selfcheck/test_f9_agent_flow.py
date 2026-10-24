import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from loader import resolve_log_path, load_sessions
from schemas import Finding, Verdict, Severity
from tools.native_submit import submit_finding
from eval import run_evaluation

# 1. Create mutated soft-lock telemetry
log_path = resolve_log_path()
softlock_log = Path("results/selfcheck/tmp/f9_softlock_session.jsonl")

lines = []
with open(log_path, "r", encoding="utf-8") as f:
    for line in f:
        l = line.strip()
        if not l:
            continue
        try:
            obj = json.loads(l)
            # Remove any portal/scene transitions
            if "portal" not in obj.get("event_name", "") and "scene_change" not in obj.get("event_name", ""):
                lines.append(l)
        except Exception:
            pass

softlock_log.write_text("\n".join(lines) + "\n", encoding="utf-8")
print(f"1. Created mutated softlock telemetry ({len(lines)} lines) at {softlock_log}")

# 2. Agent audits and produces progression softlock finding
progression_finding = Finding(
    verdict=Verdict.bug,
    severity=Severity.critical,
    confidence=0.98,
    title="Level Completion Softlock Due to Missing Portal Trigger / Registration",
    explanation="Player traversed Level01 to its terminus at coordinates (X: 7316.61, Y: 159.96) across snapshots up to physics frame 5818. However, goal.found remained false throughout all snapshots and no portal_entered event fired, causing a progression softlock.",
    evidence_frames=[5700, 5705, 5755, 5760, 5817, 5818],
    suspected_code="Portal2D.gd:11",
    path="path2",
    needs_human_review=False,
)

finding_file = Path("results/selfcheck/tmp/f9_progression_finding.json")
finding_file.write_text(json.dumps([progression_finding.model_dump()], indent=2), encoding="utf-8")

# 3. Submit via native_submit tool for window w19
cache_path = submit_finding(
    session_id="session_1792777856_45957",
    window_id="w19",
    findings_path=finding_file,
    log_path=str(softlock_log),
    stride=4,
)
print(f"2. Submitted finding via native_submit to {cache_path}")

# 4. Run pipeline
out_results = Path("results/selfcheck/tmp/f9_eval_results.json")
res = run_evaluation(
    log_path=str(softlock_log),
    out_path=str(out_results),
    stride=4,
    ignore_checks=True,
)

eval_findings = res["results"][0]["findings"]
progression_hits = [f for f in eval_findings if "softlock" in f["title"].lower() or "portal" in f["title"].lower()]

print(f"\n3. Total findings in eval_results.json: {len(eval_findings)}")
for f in eval_findings:
    print(f"   - {f['title']} | Code: {f['suspected_code']} | Frames: {f['evidence_frames']}")

success = len(progression_hits) > 0 and progression_hits[0]["suspected_code"] == "Portal2D.gd:11"
print(f"\nF9 TEST RESULT: {'PASS' if success else 'FAIL'}")
sys.exit(0 if success else 1)

