import sys
import re
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from schemas import Event
from code_loader import get_game_codebase_context

# Test 1: coin_picked window must include PlayerData.gd (via autoload reference in Coin.gd)
ev_coin = [Event(frame=100, session_time=1.0, timestamp=1.0, event="coin_picked", category="collectible", payload={})]
ctx_coin = get_game_codebase_context(ev_coin)
coin_scripts = re.findall(r"### (\w+\.gd)", ctx_coin)
pass_coin = "PlayerData.gd" in coin_scripts
print(f"1. coin_picked includes PlayerData.gd: {'PASS' if pass_coin else 'FAIL'} ({coin_scripts})")

# Test 2: Player.gd window must include Actor.gd (via extends Actor)
ev_player = [Event(frame=200, session_time=2.0, timestamp=2.0, event="player_moved", category="player_movement", payload={})]
ctx_player = get_game_codebase_context(ev_player)
player_scripts = re.findall(r"### (\w+\.gd)", ctx_player)
pass_player = "Actor.gd" in player_scripts
print(f"2. Player window includes Actor.gd: {'PASS' if pass_player else 'FAIL'} ({player_scripts})")

# Test 3: Empty window works and does not crash
ctx_empty = get_game_codebase_context([])
pass_empty = bool(ctx_empty)
print(f"3. Empty window works without crashing: {'PASS' if pass_empty else 'FAIL'}")

# Test 4: Always includes GameLogger.gd
pass_logger = "GameLogger.gd" in player_scripts and "GameLogger.gd" in coin_scripts
print(f"4. Always includes GameLogger.gd: {'PASS' if pass_logger else 'FAIL'}")

overall = pass_coin and pass_player and pass_empty and pass_logger
print(f"\nF8 TEST RESULT: {'PASS' if overall else 'FAIL'}")
sys.exit(0 if overall else 1)

