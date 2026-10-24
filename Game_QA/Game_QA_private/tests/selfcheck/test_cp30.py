import sys
import json
import re
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from report import generate_report

# Run report generator
report_path = generate_report()

with open("results/eval_results.json", "r", encoding="utf-8") as f:
    json_data = json.load(f)

with open("report.md", "r", encoding="utf-8") as f:
    report_text = f.read()

# Compare counts
json_sessions = len(json_data)
json_findings = sum(len(r.get("findings", [])) for r in json_data)

# Count severities in JSON
json_sev = {"critical": 0, "high": 0, "medium": 0, "low": 0}
for r in json_data:
    for f in r.get("findings", []):
        sev = (f.get("severity") or "medium").lower()
        json_sev[sev] = json_sev.get(sev, 0) + 1

# Extract from report.md
md_sessions = int(re.search(r"Sessions Analyzed\*\*:\s*`(\d+)`", report_text).group(1))
md_findings = int(re.search(r"Total Findings\*\*:\s*`(\d+)`", report_text).group(1))

md_sev = {}
for s in ["critical", "high", "medium", "low"]:
    m = re.search(rf"\*\*{s.capitalize()}\*\*\s*\|\s*(\d+)", report_text)
    if m:
        md_sev[s] = int(m.group(1))

print("Count comparisons:")
print(f"  Sessions: JSON={json_sessions} | Report={md_sessions} | Match={json_sessions == md_sessions}")
print(f"  Findings: JSON={json_findings} | Report={md_findings} | Match={json_findings == md_findings}")
for s in ["critical", "high", "medium", "low"]:
    print(f"  Severity {s:<8}: JSON={json_sev[s]} | Report={md_sev.get(s, 0)} | Match={json_sev[s] == md_sev.get(s, 0)}")

# Check finding titles in report
all_titles_in_md = True
for r in json_data:
    for f in r.get("findings", []):
        title = f.get("title", "")
        if title not in report_text:
            print(f"Missing title in report: {title}")
            all_titles_in_md = False

print(f"All JSON finding titles present in report: {all_titles_in_md}")
print("CP-30 RESULT:", "PASS" if (json_findings == md_findings and all_titles_in_md) else "FAIL")

