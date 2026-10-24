import json

with open("../Syntax-error/game_events.jsonl", "r", encoding="utf-8") as f:
    events = [json.loads(line) for line in f if line.strip()]

overlaps = []
for e in events:
    frame = e.get("physics_frame")
    p = e.get("player") or {}
    data = e.get("data") or {}
    pos = None
    if isinstance(p, dict):
        pos = p.get("position")
    if not pos and isinstance(data, dict):
        pos = data.get("player_position") or data.get("position")
    
    if pos and isinstance(pos, dict) and "x" in pos and "y" in pos:
        px, py = pos["x"], pos["y"]
        p_x1, p_x2 = px - 40, px + 40
        p_y1, p_y2 = py - 82, py
        
        # Check AABB overlap with portal bounds: x in [7343, 7477], y in [-71, 131]
        if not (p_x2 < 7343 or p_x1 > 7477 or p_y2 < -71 or p_y1 > 131):
            overlaps.append((frame, px, py, e.get("event_name")))

print(f"Total overlapping frames: {len(overlaps)}")
for o in overlaps[:20]:
    print(f"  Frame {o[0]}: player=({o[1]:.1f}, {o[2]:.1f}) | event={o[3]}")

