import sys
from pathlib import Path
import re

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from schemas import Event
from code_loader import get_game_codebase_context

ev_coins = [
    Event(frame=100, session_time=1.0, timestamp=1.0, event="coin_picked", category="collectible", payload={})
]

ev_enemies = [
    Event(frame=200, session_time=2.0, timestamp=2.0, event="enemy_stomped", category="combat", payload={})
]

ev_portals = [
    Event(frame=300, session_time=3.0, timestamp=3.0, event="portal_entered", category="portal", payload={})
]

ev_empty = []

cases = [
    ("Coins only", ev_coins),
    ("Enemies only", ev_enemies),
    ("Portals only", ev_portals),
    ("Empty window", ev_empty),
]

for label, evs in cases:
    ctx = get_game_codebase_context(evs)
    # Header format is: ### <name>.gd (<path>)
    matches = re.findall(r"### (\w+\.gd)", ctx)
    print(f"{label}:")
    print(f"  Selected scripts ({len(matches)}): {matches}")

