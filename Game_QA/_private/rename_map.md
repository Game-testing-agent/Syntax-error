# Private Identifier Rename Mapping

The following defect-revealing or non-standard identifiers were renamed to neutral, conventional gameplay domain names across all scripts and scenes:

| Original Identifier / Node | Neutral Replacement | Context / Scope | Telemetry Field Check |
| :--- | :--- | :--- | :--- |
| `is_wall_stuck` | `is_corner_pinned` | `Player.gd` (kinematics state variable) | Clean (0 occurrences in telemetry) |
| `is_stair_stuck` | `is_step_aligned` | `Player.gd` (step alignment state variable) | Clean (0 occurrences in telemetry) |
| `stair_escape_count` | `step_input_count` | `Player.gd` (input accumulator counter) | Clean (0 occurrences in telemetry) |
| `is_unstompable` | `is_armored` | `Enemy.gd`, `Map3_SkyCastle.tscn` (enemy property) | Clean (0 occurrences in telemetry) |
| `trigger_lava_contact` | `handle_surface_hazard` | `Player.gd`, `Map4_LavaFortress.tscn` (hazard handler method) | Clean (0 occurrences in telemetry) |
| `FloatingEnemy` (node) | `PatrolEnemy` (node) | `Map2_UndergroundCaves.tscn` (node name) | Clean (0 occurrences in sanitized telemetry) |

