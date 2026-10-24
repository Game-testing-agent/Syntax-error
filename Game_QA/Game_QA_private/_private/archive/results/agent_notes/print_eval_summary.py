import json

with open("results/eval_results.json", "r", encoding="utf-8") as f:
    data = json.load(f)

for sess in data:
    sid = sess.get("session_id")
    findings = sess.get("findings", [])
    print(f"\n=== Session: {sid} (Findings: {len(findings)}) ===")
    for idx, f in enumerate(findings, 1):
        print(f"  {idx}. [{f.get('severity')}] {f.get('title')}")
        print(f"     Code: {f.get('suspected_code')} | Path: {f.get('path')} | Conf: {f.get('confidence')}")
        print(f"     Frames: {f.get('evidence_frames')}")

