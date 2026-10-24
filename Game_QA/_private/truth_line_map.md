# Truth Line Map & Function Mapping

This mapping correlates ground truth defects with the sanitized `game_src` code locations, accounting for all identifier renames per `_private/rename_map.md`.

## Identifier Renaming Reference
| Original Identifier / Node | Neutral Sanitized Name | File / Scene Scope |
| :--- | :--- | :--- |
| `trigger_lava_contact` | `handle_surface_hazard` | `Actors/Player.gd`, `Levels/Map4_LavaFortress.tscn` |
| `is_wall_stuck` | `is_corner_pinned` | `Actors/Player.gd` |
| `is_stair_stuck` | `is_step_aligned` | `Actors/Player.gd` |
| `stair_escape_count` | `step_input_count` | `Actors/Player.gd` |
| `is_unstompable` | `is_armored` | `Actors/Enemy.gd`, `Levels/Map3_SkyCastle.tscn` |
| `FloatingEnemy` (node) | `PatrolEnemy` (node) | `Levels/Map2_UndergroundCaves.tscn` |

## Truth Component Mapping Table
| Defect Mechanism | Component / File | Original Function / Line | Sanitized Function / Line | Matching Strategy |
| :--- | :--- | :--- | :--- | :--- |
| Milestone score deduction | `Autoload/PlayerData.gd` | `set_score` (L7) | `set_score` (L29, check L33) | File + function (`PlayerData.gd:set_score`) |
| Enemy4 non-lethal collision | `Actors/Player.gd` | `_on_EnemyDetector_body_entered` (L79) | `_on_EnemyDetector_body_entered` (L79) | File + function (`Player.gd:_on_EnemyDetector_body_entered`) |
| Delayed lava death timer | `Actors/Player.gd` | `trigger_lava_contact` (L105) | `handle_surface_hazard` (L98) | File + function / alias mapping |
| Wall pin wedge softlock | `Actors/Player.gd` | `_physics_process` (L120) | `_physics_process` (L107, check L115 `is_corner_pinned`) | File + function (`Player.gd:_physics_process`) |
| Stair sticking step arrest | `Actors/Player.gd` | `_physics_process` (L120) | `_physics_process` (L107, check L122 `is_step_aligned`) | File + function (`Player.gd:_physics_process`) |
| Floor hole void fall | `Actors/Player.gd` | `_physics_process` (L120) | `_physics_process` (L107, out of bounds check L218) | File + function (`Player.gd:_physics_process`) |
| Tower wall jump impulse boost | `Actors/Player.gd` | `get_direction` (L170) | `get_direction` (L231, check L235) | File + function (`Player.gd:get_direction`) |
| Retained enemy positions on retry | `Actors/Enemy.gd` | `_ready` (L13) | `_ready` (L13) | File + function (`Enemy.gd:_ready`) |
| Floating enemy platform hover | `Actors/Enemy.gd` | `_physics_process` (L32) | `_physics_process` (L32, `is_floating`) | File + function (`Enemy.gd:_physics_process`) |
| Stomp tunneling height miss | `Actors/Enemy.gd` | `_on_StompArea2D_area_entered` (L61) | `_on_StompArea2D_area_entered` (L61) | File + function (`Enemy.gd:_on_StompArea2D_area_entered`) |
| 7th coin zero score pickup | `Objects/Coin.gd` | `_on_body_entered` (L21) | `_on_body_entered` (L21, check L60) | File + function (`Coin.gd:_on_body_entered`) |
| Portal second touch requirement | `Objects/Portal2D.gd` | `_on_body_entered` (L18) | `_on_body_entered` (L18, check L27) | File + function (`Portal2D.gd:_on_body_entered`) |
| Retry retaining enemy transforms | `UserInterface/RetryButton.gd` | `_on_button_up` (L4) | `_on_button_up` (L4, check L14) | File + function (`RetryButton.gd:_on_button_up`) |
