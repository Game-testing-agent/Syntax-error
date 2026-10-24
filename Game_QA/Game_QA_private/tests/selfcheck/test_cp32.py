import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from loader import resolve_log_path
from eval import run_evaluation

log_path = resolve_log_path()
clean_log_path = Path("results/selfcheck/tmp/clean_session.jsonl")

# Extract only lines from session_start to frame 500
clean_lines = []
with open(log_path, "r", encoding="utf-8") as f:
    for line in f:
        line_str = line.strip()
        if not line_str:
            continue
        try:
            obj = json.loads(line_str)
            pf = obj.get("physics_frame") or obj.get("data", {}).get("frame", 0)
            cat = obj.get("category", "")
            # Keep clean startup and early gameplay, skip all anomalies
            if pf <= 500 and cat != "anomaly" and "anomaly" not in obj.get("event_name", ""):
                clean_lines.append(line_str)
        except Exception:
            pass

clean_log_path.write_text("\n".join(clean_lines) + "\n", encoding="utf-8")
print(f"Wrote {len(clean_lines)} clean lines to {clean_log_path}")

out_path = Path("results/selfcheck/tmp/clean_eval_results.json")
res = run_evaluation(
    log_path=str(clean_log_path),
    out_path=str(out_path),
    stride=1,
    ignore_checks=False,  # Run full Path 1 + Path 2
)

results = res["results"]
total_findings = sum(len(r["findings"]) for r in results)
print(f"Clean session total findings: {total_findings}")
for r in results:
    for f in r["findings"]:
        print(f"  False positive: {f['title']} | Frame: {f['evidence_frames']}")

print("CP-32 RESULT:", "PASS" if total_findings == 0 else "FAIL")

