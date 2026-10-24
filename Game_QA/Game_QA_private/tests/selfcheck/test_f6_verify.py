import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from schemas import Finding, Verdict, Severity
from eval import dedupe_finding_key, merge_findings

def dedupe_list(incoming: list[Finding]) -> list[Finding]:
    findings = []
    for f in incoming:
        key = dedupe_finding_key(f)
        existing = next((ex for ex in findings if dedupe_finding_key(ex) == key), None)
        if existing is None:
            # Shallow copy to avoid mutating test inputs
            findings.append(Finding.model_validate(f.model_dump()))
        else:
            merge_findings(existing, f)
    return findings

# (a) Same line, different titles: MUST merge
f_a1 = Finding(
    verdict=Verdict.bug,
    severity=Severity.medium,
    confidence=0.8,
    title="Engine Anomaly: unexpected_score_change",
    explanation="Short explanation 1",
    evidence_frames=[578],
    suspected_code="PlayerData.gd:L36",
)
f_a2 = Finding(
    verdict=Verdict.bug,
    severity=Severity.high,
    confidence=0.95,
    title="Semantic Anomaly: unexpected_score_change",
    explanation="Much longer detailed explanation 2 from semantic pass",
    evidence_frames=[861],
    suspected_code="PlayerData.gd:36",
)
res_a = dedupe_list([f_a1, f_a2])
pass_a = len(res_a) == 1
print(f"(a) Same line different titles merged: {'PASS' if pass_a else 'FAIL'} (Count: {len(res_a)})")

# (b) Same title, different code: MUST stay separate
f_b1 = Finding(
    verdict=Verdict.bug,
    severity=Severity.medium,
    title="Enemy Frozen",
    explanation="Enemy 1 stuck at wall",
    evidence_frames=[500],
    suspected_code="Enemy.gd:L20",
)
f_b2 = Finding(
    verdict=Verdict.bug,
    severity=Severity.medium,
    title="Enemy Frozen",
    explanation="Enemy 4 stuck at wall due to zero velocity",
    evidence_frames=[3241],
    suspected_code="Enemy.gd:L31",
)
res_b = dedupe_list([f_b1, f_b2])
pass_b = len(res_b) == 2
print(f"(b) Same title different code kept separate: {'PASS' if pass_b else 'FAIL'} (Count: {len(res_b)})")

# (c) Null code: falls back to title
f_c1 = Finding(
    verdict=Verdict.bug,
    severity=Severity.low,
    title="General Timing Jitter",
    explanation="Frame rate drop",
    evidence_frames=[100],
    suspected_code=None,
)
f_c2 = Finding(
    verdict=Verdict.bug,
    severity=Severity.low,
    title="General Timing Jitter",
    explanation="Another frame rate drop",
    evidence_frames=[200],
    suspected_code=None,
)
res_c = dedupe_list([f_c1, f_c2])
pass_c = len(res_c) == 1
print(f"(c) Null code falls back to title: {'PASS' if pass_c else 'FAIL'} (Count: {len(res_c)})")

# (d) Merged evidence frames are the union, highest severity and confidence kept, longest explanation kept
merged = res_a[0]
pass_d = (
    merged.evidence_frames == [578, 861]
    and merged.severity == Severity.high
    and merged.confidence == 0.95
    and "Much longer detailed explanation 2" in merged.explanation
)
print(f"(d) Merged properties union and max verified: {'PASS' if pass_d else 'FAIL'}")
print(f"  Frames: {merged.evidence_frames}")
print(f"  Severity: {merged.severity}")
print(f"  Confidence: {merged.confidence}")

overall = pass_a and pass_b and pass_c and pass_d
print(f"\nF6 VERIFICATION OVERALL: {'PASS' if overall else 'FAIL'}")
sys.exit(0 if overall else 1)

