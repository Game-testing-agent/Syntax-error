import sys
sys.stdout.reconfigure(encoding='utf-8')
from pathlib import Path

targets = [
    ('Game_QA_audit/report.py', 70),
    ('Game_QA_audit/.agents/skills/game-qa/references/gdscript_mechanics.md', 1),
    ('Game_QA_audit/game_src/Actors/Enemy.gd', 17),
    ('Game_QA_audit/game_src/Actors/Player.gd', 302),
    ('Game_QA_audit/game_src/Objects/Coin.gd', 38),
    ('Game_QA_audit/game_src/Objects/Portal2D.gd', 81),
]

for p, l in targets:
    fpath = Path(p)
    if fpath.exists():
        lines = fpath.read_text(encoding='utf-8').splitlines()
        print(f"{p}:{l} -> {repr(lines[l-1])}")
