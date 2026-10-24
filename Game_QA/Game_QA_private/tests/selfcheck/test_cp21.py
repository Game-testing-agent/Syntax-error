import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from loader import resolve_log_path, load_sessions
from schemas import ReviewWindow
from code_loader import get_game_codebase_context

# Read truth strings
with open("data/truth.json", "r", encoding="utf-8") as f:
    truth_data = json.load(f)

truth_strings = set()
for s in truth_data.values():
    for eb in s.get("expected_bugs", []):
        truth_strings.add(eb["title"].lower())

print("Truth strings from data/truth.json:", sorted(list(truth_strings)))

# Build context and payload that llm.py uses for review_window
log_path = resolve_log_path()
sessions = load_sessions(log_path, stride=4)
sess = list(sessions.values())[0]

w_snaps = [s for s in sess.snapshots if 0.0 <= s.session_time < 5.0]
w_events = [e for e in sess.events if 0.0 <= e.session_time < 5.0]

code_context = get_game_codebase_context(w_events)

payload = {
    "window_id": "w00",
    "session_id": sess.session_id,
    "scene": w_snaps[0].scene if w_snaps else "",
    "start_frame": w_snaps[0].frame if w_snaps else 0,
    "end_frame": w_snaps[-1].frame if w_snaps else 0,
    "snapshots": [s.model_dump() for s in w_snaps],
    "events": [e.model_dump() for e in w_events],
    "code_context": code_context,
}

payload_json = json.dumps(payload).lower()

leaked = []
for ts in truth_strings:
    if ts in payload_json:
        leaked.append(ts)

print(f"Payload keys: {list(payload.keys())}")
print(f"Code context lines: {len(code_context.splitlines())}")
print(f"Truth leakage detected: {leaked}")
print(f"Does llm.py read prompts/review_v1.md?: False (no prompt loading code in llm.py)")

