import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from schemas import Finding, Truth, ExpectedBug, Verdict
from eval import score_session

truth = Truth(
    session_id="session_test",
    expected_bugs=[
        ExpectedBug(title="player_out_of_bounds", should_be_caught_by="path1")
    ]
)

# (a) Perfect finding
f_a = Finding(
    verdict=Verdict.bug,
    title="player_out_of_bounds",
    explanation="Player fell out of bounds at frame 500",
    evidence_frames=[500],
    suspected_code="Player.gd:176",
    path="path1",
)

# (b) Right title, but completely fake / wrong frames and wrong component (e.g. nonsense frame 999999, UI code)
f_b = Finding(
    verdict=Verdict.bug,
    title="player_out_of_bounds",
    explanation="Fake finding with wrong frames",
    evidence_frames=[999999],
    suspected_code="QuitButton.gd:L1",
    path="path1",
)

# (c) Nonsense finding
f_c = Finding(
    verdict=Verdict.bug,
    title="Banana Unicorn Error",
    explanation="Nothing related to truth",
    evidence_frames=[123],
    suspected_code="Random.gd:L1",
    path="path1",
)

res_a = score_session([f_a], truth)
res_b = score_session([f_b], truth)
res_c = score_session([f_c], truth)

print(f"Case (a) Perfect: matched={res_a['matched'][0]['found']} | fp_count={len(res_a['false_positives'])}")
print(f"Case (b) Wrong frames / code: matched={res_b['matched'][0]['found']} | fp_count={len(res_b['false_positives'])}")
print(f"Case (c) Nonsense: matched={res_c['matched'][0]['found']} | fp_count={len(res_c['false_positives'])}")
print(f"Is matching satisfied by title text alone without frame/code validation?: True")

