#!/usr/bin/env python3
"""Source sanitization tool for Game_QA (Private Builder).

Transforms real source into sanitized game_src, generating .manifest.json.
- Removes all BugFlags, test suites, and benchmark comments.
- Removes GameLogger.log_bug_trigger function and all call sites.
- Renames defect-hinting identifiers to neutral domain names per _private/rename_map.md.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent

MAX_RULE_ITERATIONS = 5
BUILD_TIMEOUT_SECONDS = 60.0

ALLOWED_EXTENSIONS = {".gd", ".tscn", ".tres"}
IGNORED_DIRS = {".godot", ".import", ".git", "__pycache__"}


def compute_sha256(filepath: Path) -> str:
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def apply_replacement(text: str, target: str, replacement: str, rule_name: str, filename: str) -> str:
    """Applies target replacement with hard iteration cap."""
    iterations = 0
    while target in text:
        iterations += 1
        if iterations > MAX_RULE_ITERATIONS:
            raise RuntimeError(f"Iteration cap exceeded ({MAX_RULE_ITERATIONS}) in {filename} for rule: {rule_name}")
        text = text.replace(target, replacement, 1)
    return text


def strip_tricky_comments(text: str) -> str:
    """Strips all benchmark '# TRICKY <N>' comment annotations."""
    return re.sub(r'([ \t]*# TRICKY\s+\d+:[^\n]*\n(?:[ \t]*#[^\n]*\n)*)', '', text)


def sanitize_text(content: str, filename: str) -> str:
    """Applies behavior-preserving sanitization rules."""
    text = strip_tricky_comments(content)

    if filename == "project.godot":
        lines = [line for line in text.splitlines() if not re.search(r'BugFlags\s*=\s*"\*res://', line)]
        return "\n".join(lines) + ("\n" if lines else "")

    if filename == "GameLogger.gd":
        # Remove func log_bug_trigger entirely
        pattern = r'func log_bug_trigger\(bug_id:[^\n]+\n(?:\t[^\n]+\n)*'
        text = re.sub(pattern, '', text)
        return text

    if filename == "PlayerData.gd":
        # Add saved_enemy_positions
        text = re.sub(
            r'# Milestone score regression\s*\n\s*var bug_milestone_score_tax:\s*bool\s*=\s*true\s*\n',
            'var saved_enemy_positions: Dictionary = {}\n',
            text
        )
        text = apply_replacement(
            text,
            "if bug_milestone_score_tax and not is_resetting and old_score >= 500 and new_score > old_score:",
            "if not is_resetting and old_score >= 500 and new_score > old_score:",
            "milestone_tax_guard",
            filename
        )
        return text

    if filename == "Player.gd":
        # Rename state variables
        text = text.replace("var is_wall_stuck: bool = false", "var is_corner_pinned: bool = false")
        text = text.replace("var is_stair_stuck: bool = false", "var is_step_aligned: bool = false")
        text = text.replace("var stair_escape_count: int = 0", "var step_input_count: int = 0")
        text = text.replace("func trigger_lava_contact() -> void:", "func handle_surface_hazard() -> void:")

        # 1. Enemy4 collision exemption (unwrapped, call removed)
        old_1a = """\tif BugFlags and BugFlags.map1_enemy4_no_kill:
\t\tif body.name == "Enemy4" or body.get_index() == 3 or ("can_kill_player" in body and not body.can_kill_player):
\t\t\tif GameLogger:
\t\t\t\tGameLogger.log_bug_trigger("1A", {
\t\t\t\t\t"enemy_name": body.name,
\t\t\t\t\t"player_position": GameLogger.vec2_to_dict(global_position),
\t\t\t\t\t"enemy_position": GameLogger.vec2_to_dict(body.global_position) if "global_position" in body else null
\t\t\t\t})
\t\t\treturn"""
        new_1a = """\tif body.name == "Enemy4" or body.get_index() == 3 or ("can_kill_player" in body and not body.can_kill_player):
\t\treturn"""
        text = apply_replacement(text, old_1a, new_1a, "enemy4_no_kill", filename)

        # 2. Delayed lava death (unwrapped, call removed)
        old_4a = """\tif BugFlags and BugFlags.map4_delayed_lava_death:
\t\tif lava_timer < 0.0:
\t\t\tlava_timer = 3.0
\t\t\tif GameLogger:
\t\t\t\tGameLogger.log_bug_trigger("4A", {
\t\t\t\t\t"delay_seconds": 3.0,
\t\t\t\t\t"position": GameLogger.vec2_to_dict(global_position)
\t\t\t\t})
\t\treturn"""
        new_4a = """\tif lava_timer < 0.0:
\t\tlava_timer = 3.0
\treturn"""
        text = apply_replacement(text, old_4a, new_4a, "delayed_lava_death", filename)

        # 3. Wall stuck -> corner pinned (unwrapped, call removed)
        old_2a = """\tif BugFlags and BugFlags.map2_wall_stuck:
\t\tif not is_wall_stuck and global_position.x >= 4360.0 and global_position.x <= 4440.0 and global_position.y >= 600.0 and global_position.y <= 680.0:
\t\t\tis_wall_stuck = true
\t\t\tif GameLogger:
\t\t\t\tGameLogger.log_bug_trigger("2A", {
\t\t\t\t\t"tile_coords": [55, 8],
\t\t\t\t\t"position": GameLogger.vec2_to_dict(global_position),
\t\t\t\t\t"stuck": true
\t\t\t\t})
\t\tif is_wall_stuck:
\t\t\tvelocity = Vector2.ZERO
\t\t\tmove_and_slide()
\t\t\treturn"""
        new_2a = """\tif not is_corner_pinned and global_position.x >= 4360.0 and global_position.x <= 4440.0 and global_position.y >= 600.0 and global_position.y <= 680.0:
\t\tis_corner_pinned = true
\tif is_corner_pinned:
\t\tvelocity = Vector2.ZERO
\t\tmove_and_slide()
\t\treturn"""
        text = apply_replacement(text, old_2a, new_2a, "wall_stuck", filename)

        # 4. Stair stick -> step aligned (unwrapped, call removed)
        old_3a = """\tif BugFlags and BugFlags.map3_stair_stick:
\t\tif not is_stair_stuck and is_on_floor() and global_position.x >= 5420.0 and global_position.x <= 5460.0 and global_position.y >= 540.0 and global_position.y <= 580.0:
\t\t\tis_stair_stuck = true
\t\t\tstair_escape_count = 0
\t\t\tif GameLogger:
\t\t\t\tGameLogger.log_bug_trigger("3A", {
\t\t\t\t\t"stair_coords": [68, 7],
\t\t\t\t\t"escape_presses_needed": 3,
\t\t\t\t\t"position": GameLogger.vec2_to_dict(global_position)
\t\t\t\t})
\t\tif is_stair_stuck:
\t\t\tif Input.is_action_just_pressed("move_left"):
\t\t\t\tstair_escape_count += 1
\t\t\t\tif stair_escape_count >= 3:
\t\t\t\t\tis_stair_stuck = false
\t\t\tif is_stair_stuck:
\t\t\t\tvelocity = Vector2.ZERO
\t\t\t\tmove_and_slide()
\t\t\t\treturn"""
        new_3a = """\tif not is_step_aligned and is_on_floor() and global_position.x >= 5420.0 and global_position.x <= 5460.0 and global_position.y >= 540.0 and global_position.y <= 580.0:
\t\tis_step_aligned = true
\t\tstep_input_count = 0
\tif is_step_aligned:
\t\tif Input.is_action_just_pressed("move_left"):
\t\t\tstep_input_count += 1
\t\t\tif step_input_count >= 3:
\t\t\t\tis_step_aligned = false
\t\tif is_step_aligned:
\t\t\tvelocity = Vector2.ZERO
\t\t\tmove_and_slide()
\t\t\treturn"""
        text = apply_replacement(text, old_3a, new_3a, "stair_stick", filename)

        # 5. Floor hole (call removed)
        old_1b = """\t\tif BugFlags and BugFlags.map1_floor_hole:
\t\t\tGameLogger.log_bug_trigger("1B", {
\t\t\t\t"position": GameLogger.vec2_to_dict(global_position),
\t\t\t\t"threshold_y": OUT_OF_BOUNDS_Y
\t\t\t})"""
        text = apply_replacement(text, old_1b, "", "floor_hole", filename)

        # 6. Tower wall jump (unwrapped, call removed)
        old_3c = """\tif BugFlags and BugFlags.map3_tower_wall_jump and is_on_wall() and Input.is_action_just_pressed("jump"):
\t\tif global_position.x >= 15550.0 and global_position.x <= 15650.0:
\t\t\tjump_pressed = true
\t\t\ttower_wall_jump_active = true
\t\t\tif GameLogger:
\t\t\t\tGameLogger.log_bug_trigger("3C", {
\t\t\t\t\t"wall_coords": [195, 8],
\t\t\t\t\t"jump_multiplier": 2.0,
\t\t\t\t\t"position": GameLogger.vec2_to_dict(global_position)
\t\t\t\t})"""
        new_3c = """\tif is_on_wall() and Input.is_action_just_pressed("jump"):
\t\tif global_position.x >= 15550.0 and global_position.x <= 15650.0:
\t\t\tjump_pressed = true
\t\t\ttower_wall_jump_active = true"""
        text = apply_replacement(text, old_3c, new_3c, "tower_wall_jump", filename)

        # 7. Wall friction jump dampening
        text = re.sub(r'# Wall-friction jump dampening\s*\n\s*@export var bug_wall_friction_jump:\s*bool\s*=\s*true\s*\n', '', text)
        text = re.sub(r'@export var bug_wall_friction_jump:\s*bool\s*=\s*true\s*\n', '', text)
        text = text.replace(
            "elif bug_wall_friction_jump and is_on_wall() and _velocity.y < -50.0 and direction.x != 0.0:",
            "elif is_on_wall() and _velocity.y < -50.0 and direction.x != 0.0:"
        )
        return text

    if filename == "Enemy.gd":
        text = text.replace("var is_unstompable: bool = false", "var is_armored: bool = false")
        text = text.replace("PlayerData.retained_enemy_transforms", "PlayerData.saved_enemy_positions")
        # Stomp tunneling export and threshold
        text = re.sub(r'@export var bug_stomp_tunneling:\s*bool\s*=\s*true\s*\n', '', text)
        old_tunnel = """\tvar stomp_threshold = stomp_area.global_position.y
\tif bug_stomp_tunneling:
\t\tvar attacker = area.get_parent()
\t\tif attacker and "velocity" in attacker and attacker.velocity.y > 500.0:
\t\t\tstomp_threshold -= 14.0"""
        new_tunnel = """\tvar stomp_threshold = stomp_area.global_position.y
\tvar attacker = area.get_parent()
\tif attacker and "velocity" in attacker and attacker.velocity.y > 500.0:
\t\tstomp_threshold -= 14.0"""
        text = apply_replacement(text, old_tunnel, new_tunnel, "stomp_tunneling", filename)

        # Retained enemy transforms -> saved_enemy_positions in PlayerData
        old_retained = """\tif BugFlags and BugFlags.map4_retry_retains_enemies:
\t\tif BugFlags.retained_enemy_transforms.has(name):
\t\t\tglobal_position = BugFlags.retained_enemy_transforms[name]"""
        new_retained = """\tif PlayerData and PlayerData.saved_enemy_positions.has(name):
\t\tglobal_position = PlayerData.saved_enemy_positions[name]"""
        text = apply_replacement(text, old_retained, new_retained, "retained_enemy_transforms", filename)

        # Floating enemy (unwrapped, call removed)
        old_float = """\tif is_floating_bug:
\t\tif not is_on_floor():
\t\t\tvelocity.y = 0.0
\t\t\tif not has_triggered_floating:
\t\t\t\thas_triggered_floating = true
\t\t\t\tif GameLogger:
\t\t\t\t\tGameLogger.log_bug_trigger("2B", {
\t\t\t\t\t\t"enemy_name": name,
\t\t\t\t\t\t"position": GameLogger.vec2_to_dict(global_position)
\t\t\t\t\t})"""
        new_float = """\tif is_floating:
\t\tif not is_on_floor():
\t\t\tvelocity.y = 0.0
\t\t\tif not has_triggered_floating:
\t\t\t\thas_triggered_floating = true"""
        text = apply_replacement(text, old_float, new_float, "floating_enemy_guard", filename)
        text = apply_replacement(text, "var is_floating_bug: bool = false", "var is_floating: bool = false", "floating_enemy_var", filename)
        return text

    if filename == "Map2_UndergroundCaves.tscn":
        text = apply_replacement(text, 'name="FloatingEnemy"', 'name="PatrolEnemy"', "floating_node_name", filename)
        text = apply_replacement(text, "is_floating_bug = true", "is_floating = true", "floating_scene_override", filename)
        return text

    if filename == "Map3_SkyCastle.tscn":
        text = apply_replacement(text, "is_unstompable = true", "is_armored = true", "unstompable_scene_override", filename)
        return text

    if filename == "Map4_LavaFortress.tscn":
        text = text.replace('trigger_lava_contact', 'handle_surface_hazard')
        return text

    if filename == "Coin.gd":
        text = re.sub(r'# Sub-frame multi-pickup collision race\s*\n\s*@export var bug_deferred_pickup_race:\s*bool\s*=\s*true\s*\n', '', text)
        text = re.sub(r'@export var bug_deferred_pickup_race:\s*bool\s*=\s*true\s*\n', '', text)
        text = text.replace(
            'if bug_deferred_pickup_race and body and "velocity" in body and abs(body.velocity.x) > 300.0:',
            'if body and "velocity" in body and abs(body.velocity.x) > 300.0:'
        )
        old_coin = """\tvar should_award_score = true
\tif total_coins_collected == 7 and BugFlags and BugFlags.map1_seventh_coin_no_score:
\t\tshould_award_score = false
\t\tif GameLogger:
\t\t\tGameLogger.log_bug_trigger("1C", {
\t\t\t\t"coin_number": 7,
\t\t\t\t"coin_id": int(get_instance_id()),
\t\t\t\t"position": GameLogger.vec2_to_dict(global_position),
\t\t\t\t"score_awarded": 0
\t\t\t})"""
        new_coin = """\tvar should_award_score = true
\tif total_coins_collected == 7:
\t\tshould_award_score = false"""
        text = apply_replacement(text, old_coin, new_coin, "seventh_coin_guard", filename)
        return text

    if filename == "Portal2D.gd":
        text = re.sub(r'# Unpaused physics fall during airborne portal transition\s*\n\s*@export var bug_airborne_portal_unpause:\s*bool\s*=\s*true\s*\n', '', text)
        text = re.sub(r'@export var bug_airborne_portal_unpause:\s*bool\s*=\s*true\s*\n', '', text)
        portal_unpause_old = """\tif bug_airborne_portal_unpause:

\t\tvar player_nodes = get_tree().get_nodes_in_group("player")

\t\tif player_nodes.size() > 0 and not player_nodes[0].is_on_floor() and player_nodes[0].velocity.y > 0:

\t\t\tshould_pause = false"""
        portal_unpause_new = """\tvar player_nodes = get_tree().get_nodes_in_group("player")
\tif player_nodes.size() > 0 and not player_nodes[0].is_on_floor() and player_nodes[0].velocity.y > 0:
\t\tshould_pause = false"""
        text = apply_replacement(text, portal_unpause_old, portal_unpause_new, "portal_airborne_unpause", filename)

        old_portal = """\tif BugFlags and BugFlags.map4_portal_second_touch and is_map4_portal:
\t\tportal_touch_count += 1
\t\tif portal_touch_count < 2:
\t\t\tif GameLogger:
\t\t\t\tGameLogger.log_bug_trigger("4B", {
\t\t\t\t\t"touch_count": portal_touch_count,
\t\t\t\t\t"teleport_triggered": false,
\t\t\t\t\t"required_touches": 2
\t\t\t\t})
\t\t\treturn
\t\telse:
\t\t\tif GameLogger:
\t\t\t\tGameLogger.log_bug_trigger("4B", {
\t\t\t\t\t"touch_count": portal_touch_count,
\t\t\t\t\t"teleport_triggered": true
\t\t\t\t})"""
        new_portal = """\tif is_map4_portal:
\t\tportal_touch_count += 1
\t\tif portal_touch_count < 2:
\t\t\treturn"""
        text = apply_replacement(text, old_portal, new_portal, "portal_guard", filename)
        return text

    if filename == "RetryButton.gd":
        old_retry = """\tif BugFlags and BugFlags.map4_retry_retains_enemies:
\t\tvar enemies = get_tree().get_nodes_in_group("enemies")
\t\tBugFlags.retained_enemy_transforms.clear()
\t\tfor e in enemies:
\t\t\tif is_instance_valid(e) and "global_position" in e:
\t\t\t\tBugFlags.retained_enemy_transforms[e.name] = e.global_position
\t\tif GameLogger and enemies.size() > 0:
\t\t\tGameLogger.log_bug_trigger("4C", {
\t\t\t\t"retained_enemies_count": enemies.size()
\t\t\t})"""
        new_retry = """\tvar enemies = get_tree().get_nodes_in_group("enemies")
\tif PlayerData:
\t\tPlayerData.saved_enemy_positions.clear()
\t\tfor e in enemies:
\t\t\tif is_instance_valid(e) and "global_position" in e:
\t\t\t\tPlayerData.saved_enemy_positions[e.name] = e.global_position"""
        text = apply_replacement(text, old_retry, new_retry, "retry_saved_enemies", filename)
        return text

    if filename == "MapRunner.gd":
        text = text.replace(
            "# MapRunner.gd — Headless & CLI dispatcher for QA benchmark maps",
            "# MapRunner.gd — Headless & CLI dispatcher for game levels"
        )
        return text

    return text


def build_sanitized_source(src_dir: Path, proj_path: Path | None, out_dir: Path) -> dict[str, str]:
    """Atomic build: transforms source into staging dir game_src.new, then swaps cleanly."""
    start_time = time.monotonic()

    if not src_dir.exists():
        raise FileNotFoundError(f"Source directory not found: {src_dir}")

    staging_dir = out_dir.parent / (out_dir.name + ".new")
    if staging_dir.exists():
        shutil.rmtree(staging_dir)
    staging_dir.mkdir(parents=True, exist_ok=True)

    manifest: dict[str, str] = {}
    DROP_FILES = {
        "BugFlags.gd",
        "BugFlags.gd.uid",
        "test_bugs.gd",
        "test_bugs.gd.uid",
        "test_fault_injection.gd",
        "test_fault_injection.gd.uid",
        "test_gameplay_flow.gd",
        "test_gameplay_flow.gd.uid",
        "test_logger_suite.gd",
        "test_logger_suite.gd.uid",
    }

    try:
        for root, dirs, files in os.walk(src_dir):
            dirs[:] = [d for d in dirs if d not in IGNORED_DIRS and d != "Tests"]

            for f in sorted(files):
                if time.monotonic() - start_time > BUILD_TIMEOUT_SECONDS:
                    raise TimeoutError(f"Build exceeded timeout of {BUILD_TIMEOUT_SECONDS}s")

                if f in DROP_FILES:
                    print(f"[build] Dropping {f}... OK")
                    continue

                src_file = Path(root) / f
                rel_path = src_file.relative_to(src_dir)

                if src_file.suffix not in ALLOWED_EXTENSIONS and src_file.name != "project.godot":
                    continue

                dest_file = staging_dir / rel_path
                dest_file.parent.mkdir(parents=True, exist_ok=True)

                raw_text = src_file.read_text(encoding="utf-8", errors="ignore")
                sanitized = sanitize_text(raw_text, src_file.name)
                dest_file.write_text(sanitized, encoding="utf-8")

                norm_rel = str(rel_path).replace("\\", "/")
                manifest[norm_rel] = compute_sha256(dest_file)
                print(f"[build] Processing {norm_rel}... OK")

        if proj_path and proj_path.exists():
            dest_proj = staging_dir / "project.godot"
            raw_text = proj_path.read_text(encoding="utf-8", errors="ignore")
            sanitized = sanitize_text(raw_text, "project.godot")
            dest_proj.write_text(sanitized, encoding="utf-8")
            manifest["project.godot"] = compute_sha256(dest_proj)
            print("[build] Processing project.godot... OK")

        manifest_path = staging_dir / ".manifest.json"
        manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
        print(f"[build] Manifest written ({len(manifest)} files)... OK")

        old_backup = out_dir.parent / (out_dir.name + ".old")
        if old_backup.exists():
            shutil.rmtree(old_backup)

        if out_dir.exists():
            out_dir.rename(old_backup)

        staging_dir.rename(out_dir)

        if old_backup.exists():
            shutil.rmtree(old_backup)

        elapsed = time.monotonic() - start_time
        print(f"[build] SUCCESS: Sanitized {len(manifest)} files in {elapsed:.2f}s")
        return manifest

    except Exception as exc:
        print(f"[build] ERROR: Build failed: {exc}", file=sys.stderr)
        if staging_dir.exists():
            shutil.rmtree(staging_dir, ignore_errors=True)
        raise


def main() -> None:
    parser = argparse.ArgumentParser(description="Build Sanitized Godot Source")
    parser.add_argument("--build", action="store_true", default=True, help="Build sanitized source")
    parser.add_argument("--src", type=str, default=str(ROOT / "_private" / "real_src_mirror"), help="Source dir")
    parser.add_argument("--proj", type=str, default=None, help="project.godot path")
    parser.add_argument("--out", type=str, default=str(ROOT / "game_src"), help="Output sanitized game_src")

    args = parser.parse_args()
    build_sanitized_source(Path(args.src), Path(args.proj) if args.proj else None, Path(args.out))


if __name__ == "__main__":
    main()
