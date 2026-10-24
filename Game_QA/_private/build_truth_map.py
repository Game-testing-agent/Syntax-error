import difflib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ORIG_DIR = ROOT / "_private" / "archive" / "game_src_before_build"
NEW_DIR = ROOT / "game_src"

targets = [
    ("Autoload/PlayerData.gd", "set_score", "milestone score tax deduction"),
    ("Actors/Player.gd", "_on_EnemyDetector_body_entered", "Enemy4 non-lethal collision"),
    ("Actors/Player.gd", "trigger_lava_contact", "delayed lava death timer"),
    ("Actors/Player.gd", "_physics_process", "wall stuck ceiling gap wedge"),
    ("Actors/Player.gd", "_physics_process", "stair sticking"),
    ("Actors/Player.gd", "_physics_process", "floor hole void fall"),
    ("Actors/Player.gd", "get_direction", "tower wall jump boost"),
    ("Actors/Enemy.gd", "_ready", "retained enemy transforms on retry"),
    ("Actors/Enemy.gd", "_physics_process", "floating enemy platform edge float"),
    ("Actors/Enemy.gd", "_on_StompArea2D_area_entered", "stomp tunneling miss"),
    ("Objects/Coin.gd", "_on_body_entered", "7th coin zero score pickup"),
    ("Objects/Portal2D.gd", "_on_body_entered", "portal second touch requirement"),
    ("UserInterface/RetryButton.gd", "_on_button_up", "retry retaining enemy positions"),
]

lines = [
    "# Truth Line Map & Function Mapping Proposal",
    "",
    "| Component / Function | Defect Mechanism | Original Line | Sanitized Line | Match Strategy |",
    "| :--- | :--- | :--- | :--- | :--- |",
]

for file_rel, func_name, desc in targets:
    orig_file = ORIG_DIR / file_rel
    new_file = NEW_DIR / file_rel

    orig_lines = orig_file.read_text(encoding="utf-8").splitlines() if orig_file.exists() else []
    new_lines = new_file.read_text(encoding="utf-8").splitlines() if new_file.exists() else []

    # Find line in orig
    orig_ln = "N/A"
    for idx, l in enumerate(orig_lines, 1):
        if func_name in l:
            orig_ln = f"L{idx}"
            break

    # Find line in new
    new_ln = "N/A"
    for idx, l in enumerate(new_lines, 1):
        if func_name in l:
            new_ln = f"L{idx}"
            break

    lines.append(f"| `{file_rel}` (`{func_name}`) | {desc} | `{orig_ln}` | `{new_ln}` | Match by file & function |")

line_map_file = ROOT / "_private" / "truth_line_map.md"
line_map_file.write_text("\n".join(lines), encoding="utf-8")
print(f"Wrote truth line map to {line_map_file}")

