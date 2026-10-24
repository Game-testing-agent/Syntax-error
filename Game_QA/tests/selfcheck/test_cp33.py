import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from loader import resolve_log_path
from eval import run_evaluation

log_path = resolve_log_path()
softlock_log = Path("results/selfcheck/tmp/softlock_session.jsonl")

# Copy the tail of session (frames 5600-5818) where player reaches end-zone X=7316
lines = []
with open(log_path, "r", encoding="utf-8") as f:
    for line in f:
        l = line.strip()
        if not l:
            continue
        try:
            obj = json.loads(l)
            pf = obj.get("physics_frame") or obj.get("data", {}).get("frame", 0)
            if pf >= 5600:
                # Ensure no scene change or portal entered exists
                if "portal" not in obj.get("event_name", "") and "scene" not in obj.get("event_name", ""):
                    lines.append(l)
        except Exception:
            pass

softlock_log.write_text("\n".join(lines) + "\n", encoding="utf-8")
print(f"Wrote {len(lines)} lines to {softlock_log}")

out_path = Path("results/selfcheck/tmp/softlock_eval_results.json")
res = run_evaluation(
    log_path=str(softlock_log),
    out_path=str(out_path),
    stride=1,
    ignore_checks=False,
)

results = res["results"]
findings = []
for r in results:
    findings.extend(r.get("findings", []))

progression_findings = [
    f for f in findings
    if "portal" in f["title"].lower() or "soft" in f["title"].lower() or "progress" in f["title"].lower() or "stuck" in f["title"].lower()
]

print(f"Total findings: {len(findings)}")
for f in findings:
    print(f"  Finding: {f['title']} | Code: {f['suspected_code']}")

print(f"Progression soft-lock flagged: {len(progression_findings) > 0}")
print("CP-33 RESULT:", "PASS" if len(progression_findings) > 0 else "FAIL (MISSED)")

