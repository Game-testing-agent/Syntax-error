import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from schemas import Finding, Verdict, Severity, Truth, ExpectedBug
from eval import score_session

# Test Case 1: Truth entry with neither frames nor suspected_code must refuse scoring
truth_empty = {
    "session_id": "s1",
    "expected_bugs": [
        {"title": "bug_without_evidence", "should_be_caught_by": "path1"}
    ]
}

# In current unpatched eval.py, this does NOT refuse scoring, it just checks title substring!
try:
    res = score_session([Finding(verdict=Verdict.bug, title="bug_without_evidence", explanation="fake")], Truth(session_id="s1", expected_bugs=[ExpectedBug(title="bug_without_evidence")]))
    refused = False
except ValueError:
    refused = True

print(f"Empty truth entry refused: {refused} (Expected True after fix)")
if not refused:
    print("F5 TEST RESULT: FAIL (unpatched eval.py does not refuse scoring on empty truth)")
    sys.exit(1)

