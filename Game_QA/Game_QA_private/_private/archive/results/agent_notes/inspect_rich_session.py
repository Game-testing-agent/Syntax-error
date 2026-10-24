import json

with open(r"..\Syntax-error\game_events.jsonl", "r", encoding="utf-8") as f:
    events = [json.loads(line) for line in f if line.strip() and json.loads(line).get("session_id") == "session_1792845878_84836"]

print(f"Total events in session: {len(events)}")

for e in events:
    en = e.get("event_name") or ""
    cat = e.get("category") or ""
    fr = e.get("physics_frame")
    if en in ["bug_trigger", "missing_expected_object", "player_out_of_bounds", "unexpected_player_removal", "portal_entered", "portal_target_missing"]:
        print(f"Frame {fr}: {en} -> {e.get('data')}")

