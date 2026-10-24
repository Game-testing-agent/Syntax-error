import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from schemas import Finding, Verdict, Severity
from eval import score_session

truth_sample = {
    "session_id": "session_test",
    "expected_bugs": [
        {
            "title": "unexpected_score_change",
            "evidence_frames": [578, 861],
            "suspected_code": "PlayerData.gd:set_score",
            "should_be_caught_by": "path1",
        }
    ]
}

# (a) Perfect finding (frame 578 matches, code matches)
f_perfect = Finding(
    verdict=Verdict.bug,
    title="unexpected_score_change",
    explanation="Score decreased unexpectedly",
    evidence_frames=[578],
    suspected_code="PlayerData.gd:set_score",
    path="path1",
)
res_a = score_session([f_perfect], truth_sample)
pass_a = res_a["matched"][0]["found"] is True and len(res_a["false_positives"]) == 0
print(f"(a) Perfect finding matched: {'PASS' if pass_a else 'FAIL'}")

# (b) Correct title, but wrong frames (frame 999999 > 120 tolerance) AND wrong code file
f_wrong_evidence = Finding(
    verdict=Verdict.bug,
    title="unexpected_score_change",
    explanation="Wrong evidence finding",
    evidence_frames=[999999],
    suspected_code="QuitButton.gd:L1",
    path="path1",
)
res_b = score_session([f_wrong_evidence], truth_sample)
pass_b = res_b["matched"][0]["found"] is False and len(res_b["false_positives"]) == 1
print(f"(b) Wrong evidence rejected: {'PASS' if pass_b else 'FAIL'}")

# (c) Nonsense finding
f_nonsense = Finding(
    verdict=Verdict.bug,
    title="Completely unrelated bug",
    explanation="No matching keywords",
    evidence_frames=[578],
    suspected_code="Other.gd:L1",
    path="path1",
)
res_c = score_session([f_nonsense], truth_sample)
pass_c = res_c["matched"][0]["found"] is False and len(res_c["false_positives"]) == 1
print(f"(c) Nonsense counted as false positive: {'PASS' if pass_c else 'FAIL'}")

# (d) Unsure finding with perfect evidence (must NOT be counted as hit)
f_unsure = Finding(
    verdict=Verdict.unsure,
    title="unexpected_score_change",
    explanation="Might be a bug",
    evidence_frames=[578],
    suspected_code="PlayerData.gd:set_score",
    path="path1",
)
res_d = score_session([f_unsure], truth_sample)
pass_d = res_d["matched"][0]["found"] is False and len(res_d["false_positives"]) == 1
print(f"(d) Unsure verdict rejected from match: {'PASS' if pass_d else 'FAIL'}")

# (e) Truth entry lacking both frames and code must raise ValueError
truth_no_evidence = {
    "session_id": "session_test",
    "expected_bugs": [{"title": "ungrounded_bug", "should_be_caught_by": "path1"}]
}
try:
    score_session([f_perfect], truth_no_evidence)
    pass_e = False
except ValueError:
    pass_e = True
print(f"(e) Refuses ungrounded truth entry: {'PASS' if pass_e else 'FAIL'}")

# (f) One-to-one matching: two identical findings against 1 truth entry -> 1 match, 1 false positive
res_f = score_session([f_perfect, f_perfect], truth_sample)
pass_f = res_f["matched"][0]["found"] is True and len(res_f["false_positives"]) == 1
print(f"(f) One-to-one matching enforced: {'PASS' if pass_f else 'FAIL'}")

overall = pass_a and pass_b and pass_c and pass_d and pass_e and pass_f
print(f"\nF5 VERIFICATION OVERALL: {'PASS' if overall else 'FAIL'}")
sys.exit(0 if overall else 1)

