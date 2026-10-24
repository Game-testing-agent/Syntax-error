extends Node

# Central toggle registry for intentional QA benchmark bugs
# All bugs are deterministic and isolated.

# Map 1: Green Hills
var map1_enemy4_no_kill: bool = true
var map1_floor_hole: bool = true
var map1_seventh_coin_no_score: bool = true

# Map 2: Underground Caves
var map2_wall_stuck: bool = true
var map2_floating_enemy: bool = true

# Map 3: Sky Castle
var map3_stair_stick: bool = true
var map3_fourth_enemy_unstompable: bool = true
var map3_tower_wall_jump: bool = true

# Map 4: Lava Fortress
var map4_delayed_lava_death: bool = true
var map4_portal_second_touch: bool = true
var map4_retry_retains_enemies: bool = true

# Runtime state tracking across retries
var retained_enemy_transforms: Dictionary = {}

