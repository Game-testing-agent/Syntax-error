import sys
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

import code_loader
from schemas import Event

src_dir = code_loader.find_source_dir()
all_gd_files = [p.name for p in src_dir.rglob("*.gd")]
total_gd_lines = sum(len(p.read_text(encoding="utf-8", errors="ignore").splitlines()) for p in src_dir.rglob("*.gd"))

print(f"Total GDScript lines in game_src: {total_gd_lines} (Cap: {code_loader.ALL_GD_LINE_CAP})")

# 1. Under cap: verify all .gd files are included in every window
ctx = code_loader.get_game_codebase_context([])
included_gd = re.findall(r"### (\w+\.gd)", ctx)
included_tscn = re.findall(r"### (\w+\.tscn)", ctx)

print(f"Included GDScript files count: {len(included_gd)} / {len(all_gd_files)}")
print(f"Included TSCN files count: {len(included_tscn)}")

assert len(included_gd) == len(all_gd_files), f"Expected all {len(all_gd_files)} .gd files, got {len(included_gd)}"
assert "Player.tscn" in included_tscn, "Player.tscn should be included"
assert "Portal2D.tscn" in included_tscn, "Portal2D.tscn should be included"
assert "Coin.tscn" in included_tscn, "Coin.tscn should be included"
assert "Level01.tscn" in included_tscn, "Level01.tscn should be included"

# Verify lines in .tscn are annotated with L1, L2, etc.
assert "L1: [gd_scene" in ctx or "L1: [" in ctx, "TSCN lines must be annotated with line numbers"

# 2. Over cap test: artificially set cap lower than total lines
old_cap = code_loader.ALL_GD_LINE_CAP
try:
    code_loader.ALL_GD_LINE_CAP = 100
    ev_coin = [Event(frame=10, session_time=0.1, timestamp=0.1, event="coin_picked", category="collectible", payload={})]
    ctx_fallback = code_loader.get_game_codebase_context(ev_coin)
    fallback_gd = re.findall(r"### (\w+\.gd)", ctx_fallback)
    print(f"Fallback mode GDScript count: {len(fallback_gd)} (subset via dependency resolution)")
    assert "Coin.gd" in fallback_gd, "Fallback mode must include Coin.gd"
    assert "PlayerData.gd" in fallback_gd, "Fallback mode must include PlayerData.gd"
finally:
    code_loader.ALL_GD_LINE_CAP = old_cap

print("\nALL code_loader tests PASSED successfully!")

