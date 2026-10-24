import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from code_loader import load_script_with_line_numbers

code_file = Path("game_src/Actors/Player.gd")
loaded = load_script_with_line_numbers(code_file)
loaded_lines = loaded.splitlines()

with open(code_file, "r", encoding="utf-8") as f:
    disk_lines = [l.rstrip("\r\n") for l in f.readlines()]

check_indices = [1, 6, 120, 180, len(disk_lines)]

all_passed = True
for idx in check_indices:
    d = disk_lines[idx - 1]
    l = loaded_lines[idx - 1]
    expected = f"L{idx}: {d}"
    matches = (l == expected)
    if not matches:
        all_passed = False
    print(f"Index {idx}:")
    print(f"  Disk:     {repr(d)}")
    print(f"  Loaded:   {repr(l)}")
    print(f"  Matches:  {matches}")

print("CP-10 ALL MATCHED:", all_passed)

