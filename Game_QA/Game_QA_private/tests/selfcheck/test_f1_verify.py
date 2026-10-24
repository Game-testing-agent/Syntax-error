import sys
import filecmp
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from code_loader import load_script_with_line_numbers

local_src = Path("game_src").resolve()
real_src = Path("../Syntax-error/godot-4game/src").resolve()

# 1. Recursive file diff
differing = []
for r_file in real_src.rglob("*"):
    if r_file.is_file() and r_file.suffix in (".gd", ".tscn"):
        rel = r_file.relative_to(real_src)
        l_file = local_src / rel
        if not l_file.exists() or not filecmp.cmp(r_file, l_file, shallow=False):
            differing.append(str(rel))

print(f"1. Recursive diff of .gd and .tscn files: {len(differing)} differences")
if differing:
    print(f"   Differing: {differing}")

# 2. CP-10 line-number spot check on Player.gd
player_file = local_src / "Actors" / "Player.gd"
loaded = load_script_with_line_numbers(player_file).splitlines()
with open(player_file, "r", encoding="utf-8") as f:
    disk = [l.rstrip("\r\n") for l in f.readlines()]

check_indices = [1, 6, 120, 180, len(disk)]
cp10_matches = all(loaded[idx - 1] == f"L{idx}: {disk[idx - 1]}" for idx in check_indices)
print(f"2. CP-10 spot check on Player.gd: {'PASS' if cp10_matches else 'FAIL'}")

# 3. GameLogger.gd resolution check (CP-35 invalid citation)
logger_file = local_src / "Autoload" / "GameLogger.gd"
logger_exists = logger_file.exists()
print(f"3. GameLogger.gd resolves in game_src: {'PASS' if logger_exists else 'FAIL'} ({logger_file})")

overall_f1 = (len(differing) == 0 and cp10_matches and logger_exists)
print(f"F1 VERIFICATION OVERALL: {'PASS' if overall_f1 else 'FAIL'}")

