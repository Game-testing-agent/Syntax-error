import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from schemas import Finding, Verdict, Severity

# Dedupe logic extracted from eval.py lines 92-99
def dedupe_findings(incoming_findings: list[Finding]) -> list[Finding]:
    findings = []
    for f in incoming_findings:
        existing = next((ex for ex in findings if ex.title.lower() == f.title.lower()), None)
        if existing is None:
            findings.append(f)
        else:
            for fr in f.evidence_frames:
                if fr not in existing.evidence_frames:
                    existing.evidence_frames.append(fr)
    return findings

# Case 1: Two distinct bugs with the same title string but different frames and code
f_distinct1 = Finding(
    verdict=Verdict.bug,
    title="Enemy Frozen",
    explanation="Enemy 1 stuck at frame 500",
    evidence_frames=[500],
    suspected_code="Enemy.gd:L20",
)
f_distinct2 = Finding(
    verdict=Verdict.bug,
    title="Enemy Frozen",
    explanation="Enemy 4 stuck at frame 3241 due to velocity 0",
    evidence_frames=[3241],
    suspected_code="Enemy.gd:L31",
)

res1 = dedupe_findings([f_distinct1, f_distinct2])
print(f"Distinct bugs test: {len(res1)} finding(s) returned (expected 2)")
print(f"  Result titles: {[f.title for f in res1]} | Evidence frames: {[f.evidence_frames for f in res1]}")

# Case 2: Same root cause bugs but differing title prefix
f_same1 = Finding(
    verdict=Verdict.bug,
    title="Engine Anomaly: unexpected_score_change",
    explanation="Score decreased by 10",
    evidence_frames=[578],
    suspected_code="PlayerData.gd:L36",
)
f_same2 = Finding(
    verdict=Verdict.bug,
    title="Semantic Anomaly: unexpected_score_change",
    explanation="Score decreased by 10",
    evidence_frames=[861],
    suspected_code="PlayerData.gd:L36",
)

res2 = dedupe_findings([f_same1, f_same2])
print(f"Same root cause test: {len(res2)} finding(s) returned (expected 1 merged)")
print(f"  Result titles: {[f.title for f in res2]}")

