import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GAME_SRC = ROOT / "game_src"

# 1. Inspect guarded blocks in sanitized scripts:
# Player.gd:
# - Enemy4 exemption: body.name == "Enemy4", "can_kill_player", GameLogger.log_bug_trigger("1A", ...)
# - Delayed lava death: lava_timer, GameLogger.log_bug_trigger("4A", ...)
# - Wall stuck: is_wall_stuck, GameLogger.log_bug_trigger("2A", ...), tile_coords [55, 8]
# - Stair stick: is_stair_stuck, stair_escape_count, GameLogger.log_bug_trigger("3A", ...), stair_coords [68, 7]
# - Floor hole: GameLogger.log_bug_trigger("1B", ...)
# - Tower wall jump: tower_wall_jump_active, GameLogger.log_bug_trigger("3C", ...), wall_coords [195, 8], jump_multiplier 2.0

# Enemy.gd:
# - Stomp threshold modification: attacker.velocity.y > 500.0, stomp_threshold -= 14.0
# - Floating enemy: is_floating, has_triggered_floating, GameLogger.log_bug_trigger("2B", ...)
# - Retained transforms: PlayerData.retained_enemy_transforms

# Coin.gd:
# - 7th coin: total_coins_collected == 7, should_award_score = false, GameLogger.log_bug_trigger("1C", ...)

# Portal2D.gd:
# - 2nd touch: is_map4_portal, portal_touch_count < 2, GameLogger.log_bug_trigger("4B", ...)

# RetryButton.gd:
# - Retained enemies count: GameLogger.log_bug_trigger("4C", ...)

# PlayerData.gd:
# - Milestone score reduction: old_score >= 500 and new_score > old_score -> final_score = old_score - 10

# 2. Inspect scene node names in Level scenes:
levels = list((GAME_SRC / "Levels").glob("*.tscn"))
scene_nodes = {}
for lvl in levels:
    text = lvl.read_text(encoding="utf-8")
    nodes = re.findall(r'\[node name="([^"]+)"', text)
    scene_nodes[lvl.name] = nodes

print("Level Scene Nodes found:")
for lvl_name, nodes in scene_nodes.items():
    print(f"\n{lvl_name} ({len(nodes)} nodes):")
    special = [n for n in nodes if any(k in n.lower() for k in ["enemy", "hole", "lava", "stair", "tower", "gap", "portal", "coin", "bumper"])]
    print(f"  Key entities: {special[:15]}")

