import sys
import json
import hashlib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from schemas import Finding, Verdict, Severity, ReviewWindow
from code_loader import get_game_codebase_context
from llm import _cache_key, _cache_put

# Let's inspect if any route exists
print("Inspecting eval.py and llm.py for agent finding ingestion hooks...")

# Test the cache route for a dummy review window
dummy_payload = {
    "window_id": "w00",
    "session_id": "session_1792777856_45957",
    "scene": "res://src/Screens/MainScreen.tscn",
    "start_frame": 60,
    "end_frame": 60,
    "events_count": 0,
    "code_hash": hashlib.md5("".encode("utf-8")).hexdigest()[:16],
}
key = _cache_key("audit", json.dumps(dummy_payload, sort_keys=True))
print(f"Computed cache key for w00: {key}")

# But in eval.py, does eval.py have any CLI flag or function hook to receive findings directly from an agent?
with open("eval.py", "r", encoding="utf-8") as f:
    eval_text = f.read()

has_agent_hook = "agent" in eval_text.lower() and ("finding" in eval_text.lower() or "hook" in eval_text.lower())
print(f"eval.py has native agent hook: {has_agent_hook}")

