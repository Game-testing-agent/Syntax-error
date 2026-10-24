#!/usr/bin/env python3
"""Source sanitization tool for Game_QA.

Modes:
  --build: Transforms real source into sanitized game_src, generating .manifest.json. (Private side)
  --check: Verifies manifest integrity and scans for generic forbidden defect tokens. (Audit side)
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

ROOT = Path(__file__).resolve().parent.parent

# Generic forbidden tokens (case-insensitive)
FORBIDDEN_PATTERNS = [
    r"bugflags?\.gd",
    r"\bbugflag\w*",
    r"\btest_bugs\.gd\b",
    r"\btest_fault_injection\.gd\b",
    r"\binject\w*",
    r"\bsynthetic\w*",
    r"\bbenchmark\w*",
    r"\bseeded\w*",
    r"\bplanted\w*",
    r"\bknown[_\s]+bug\b",
    r"\bknown[_\s]+defect\b",
]
FORBIDDEN_REGEX = re.compile("|".join(FORBIDDEN_PATTERNS), re.IGNORECASE)

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


def sanitize_text(content: str, filename: str) -> str:
    """Applies behavior-preserving sanitization rules."""
    text = content

    if filename == "project.godot":
        lines = [line for line in text.splitlines() if not re.search(r'BugFlags\s*=\s*"\*res://', line)]
        return "\n".join(lines) + ("\n" if lines else "")

    if filename == "PlayerData.gd":
        # Add retained_enemy_transforms
        text = re.sub(
            r'# Milestone score regression\s*\n\s*var bug_milestone_score_tax:\s*bool\s*=\s*true\s*\n',
            'var retained_enemy_transforms: Dictionary = {}\n',
            text
        )
        # Strip tricky comments
        text = re.sub(
            r'# TRICKY\s+4: Milestone Score Regression[^\n]*\n(?:[ \t]*#[^\n]*\n)*',
            '',
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
        # 1. Enemy4 collision exemption
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
\t\tif GameLogger:
\t\t\tGameLogger.log_bug_trigger("1A", {
\t\t\t\t"enemy_name": body.name,
\t\t\t\t"player_position": GameLogger.vec2_to_dict(global_position),
\t\t\t\t"enemy_position": GameLogger.vec2_to_dict(body.global_position) if "global_position" in body else null
\t\t\t})
\t\treturn"""
        text = apply_replacement(text, old_1a, new_1a, "enemy4_no_kill", filename)

        # 2. Delayed lava death
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
\t\tif GameLogger:
\t\t\tGameLogger.log_bug_trigger("4A", {
\t\t\t\t"delay_seconds": 3.0,
\t\t\t\t"position": GameLogger.vec2_to_dict(global_position)
\t\t\t})
\treturn"""
        text = apply_replacement(text, old_4a, new_4a, "delayed_lava_death", filename)

        # 3. Wall stuck
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
        new_2a = """\tif not is_wall_stuck and global_position.x >= 4360.0 and global_position.x <= 4440.0 and global_position.y >= 600.0 and global_position.y <= 680.0:
\t\tis_wall_stuck = true
\t\tif GameLogger:
\t\t\tGameLogger.log_bug_trigger("2A", {
\t\t\t\t"tile_coords": [55, 8],
\t\t\t\t"position": GameLogger.vec2_to_dict(global_position),
\t\t\t\t"stuck": true
\t\t\t})
\tif is_wall_stuck:
\t\tvelocity = Vector2.ZERO
\t\tmove_and_slide()
\t\treturn"""
        text = apply_replacement(text, old_2a, new_2a, "wall_stuck", filename)

        # 4. Stair stick
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
        new_3a = """\tif not is_stair_stuck and is_on_floor() and global_position.x >= 5420.0 and global_position.x <= 5460.0 and global_position.y >= 540.0 and global_position.y <= 580.0:
\t\tis_stair_stuck = true
\t\tstair_escape_count = 0
\t\tif GameLogger:
\t\t\tGameLogger.log_bug_trigger("3A", {
\t\t\t\t"stair_coords": [68, 7],
\t\t\t\t"escape_presses_needed": 3,
\t\t\t\t"position": GameLogger.vec2_to_dict(global_position)
\t\t\t})
\tif is_stair_stuck:
\t\tif Input.is_action_just_pressed("move_left"):
\t\t\tstair_escape_count += 1
\t\t\tif stair_escape_count >= 3:
\t\t\t\tis_stair_stuck = false
\t\tif is_stair_stuck:
\t\t\tvelocity = Vector2.ZERO
\t\t\tmove_and_slide()
\t\t\treturn"""
        text = apply_replacement(text, old_3a, new_3a, "stair_stick", filename)

        # 5. Floor hole
        old_1b = """\t\tif BugFlags and BugFlags.map1_floor_hole:
\t\t\tGameLogger.log_bug_trigger("1B", {
\t\t\t\t"position": GameLogger.vec2_to_dict(global_position),
\t\t\t\t"threshold_y": OUT_OF_BOUNDS_Y
\t\t\t})"""
        new_1b = """\t\tGameLogger.log_bug_trigger("1B", {
\t\t\t"position": GameLogger.vec2_to_dict(global_position),
\t\t\t"threshold_y": OUT_OF_BOUNDS_Y
\t\t})"""
        text = apply_replacement(text, old_1b, new_1b, "floor_hole", filename)

        # 6. Tower wall jump
        text = apply_replacement(
            text,
            'if BugFlags and BugFlags.map3_tower_wall_jump and is_on_wall() and Input.is_action_just_pressed("jump"):',
            'if is_on_wall() and Input.is_action_just_pressed("jump"):',
            "tower_wall_jump",
            filename
        )
        return text

    if filename == "Enemy.gd":
        # Stomp tunneling comment and export
        text = re.sub(
            r'# TRICKY\s+1: Stomp Tunneling Miss on Fast Descent[^\n]*\n(?:[ \t]*#[^\n]*\n)*',
            '',
            text
        )
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

        # Retained enemy transforms
        old_retained = """\tif BugFlags and BugFlags.map4_retry_retains_enemies:
\t\tif BugFlags.retained_enemy_transforms.has(name):
\t\t\tglobal_position = BugFlags.retained_enemy_transforms[name]"""
        new_retained = """\tif PlayerData and PlayerData.retained_enemy_transforms.has(name):
\t\tglobal_position = PlayerData.retained_enemy_transforms[name]"""
        text = apply_replacement(text, old_retained, new_retained, "retained_enemy_transforms", filename)

        # Floating enemy
        text = apply_replacement(
            text,
            "if BugFlags and BugFlags.map2_floating_enemy and is_floating_bug:",
            "if is_floating:",
            "floating_enemy_guard",
            filename
        )
        text = apply_replacement(
            text,
            "var is_floating_bug: bool = false",
            "var is_floating: bool = false",
            "floating_enemy_var",
            filename
        )
        return text

    if filename == "Map2_UndergroundCaves.tscn":
        text = apply_replacement(text, "is_floating_bug = true", "is_floating = true", "floating_scene_override", filename)
        return text

    if filename == "MapRunner.gd":
        text = text.replace(
            "# MapRunner.gd — Headless & CLI dispatcher for QA benchmark maps",
            "# MapRunner.gd — Headless & CLI dispatcher for game levels"
        )
        return text

    if filename == "Coin.gd":
        text = apply_replacement(
            text,
            "if total_coins_collected == 7 and BugFlags and BugFlags.map1_seventh_coin_no_score:",
            "if total_coins_collected == 7:",
            "seventh_coin_guard",
            filename
        )
        return text

    if filename == "Portal2D.gd":
        text = apply_replacement(
            text,
            "if BugFlags and BugFlags.map4_portal_second_touch and is_map4_portal:",
            "if is_map4_portal:",
            "portal_guard",
            filename
        )
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
\t\tPlayerData.retained_enemy_transforms.clear()
\t\tfor e in enemies:
\t\t\tif is_instance_valid(e) and "global_position" in e:
\t\t\t\tPlayerData.retained_enemy_transforms[e.name] = e.global_position
\tif GameLogger and enemies.size() > 0:
\t\tGameLogger.log_bug_trigger("4C", {
\t\t\t"retained_enemies_count": enemies.size()
\t\t})"""
        text = apply_replacement(text, old_retry, new_retry, "retry_retained_enemies", filename)
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
    # Files/folders to drop completely
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
        # Walk only source directory, handling only allowed text files
        for root, dirs, files in os.walk(src_dir):
            # Prune ignored directories
            dirs[:] = [d for d in dirs if d not in IGNORED_DIRS]

            for f in sorted(files):
                if time.monotonic() - start_time > BUILD_TIMEOUT_SECONDS:
                    raise TimeoutError(f"Build exceeded timeout of {BUILD_TIMEOUT_SECONDS}s")

                if f in DROP_FILES:
                    print(f"[build] Dropping {f}... OK")
                    continue

                src_file = Path(root) / f
                rel_path = src_file.relative_to(src_dir)

                # Skip files not in allowed extensions unless project.godot
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

        # Project file if present
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

        # Atomic replacement: swap staging into out_dir
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


def check_sanitized_source(
    target_dir: Path,
    manifest_path: Path | None = None,
    telemetry_path: Path | None = None,
) -> bool:
    """Verifies manifest integrity and scans for forbidden tokens."""
    m_path = manifest_path or (target_dir / ".manifest.json")
    if not m_path.exists():
        print(f"[check] FAIL: Manifest file not found at {m_path}")
        return False

    manifest: dict[str, str] = json.loads(m_path.read_text(encoding="utf-8"))
    drift_detected = False

    # Check all files in manifest exist and match hash
    for rel_path, expected_hash in sorted(manifest.items()):
        actual_file = target_dir / rel_path
        if not actual_file.exists():
            print(f"[check] FAIL: Missing file from manifest: {rel_path}")
            drift_detected = True
            continue
        actual_hash = compute_sha256(actual_file)
        if actual_hash != expected_hash:
            print(f"[check] FAIL: Hash mismatch for file: {rel_path}")
            drift_detected = True

    # Check no extra files exist
    for root, dirs, files in os.walk(target_dir):
        dirs[:] = [d for d in dirs if d not in IGNORED_DIRS]
        for f in files:
            if f == ".manifest.json":
                continue
            curr = Path(root) / f
            if curr.suffix not in ALLOWED_EXTENSIONS and curr.name != "project.godot":
                continue
            rel = str(curr.relative_to(target_dir)).replace("\\", "/")
            if rel not in manifest:
                print(f"[check] FAIL: Unregistered file found in target: {rel}")
                drift_detected = True

    manifest_status = "FAIL" if drift_detected else "PASS"
    print(f"[check] Manifest Integrity Check: {manifest_status}")

    # Scan for forbidden tokens
    forbidden_hits: list[str] = []

    for root, dirs, files in os.walk(target_dir):
        dirs[:] = [d for d in dirs if d not in IGNORED_DIRS]
        for f in files:
            if f == ".manifest.json":
                continue
            fpath = Path(root) / f
            try:
                lines = fpath.read_text(encoding="utf-8", errors="ignore").splitlines()
            except Exception:
                continue
            for idx, line in enumerate(lines, start=1):
                if FORBIDDEN_REGEX.search(line):
                    rel = str(fpath.relative_to(target_dir)).replace("\\", "/")
                    forbidden_hits.append(f"{rel}:{idx}")

    # Telemetry check if provided
    if telemetry_path and telemetry_path.exists():
        try:
            with open(telemetry_path, "r", encoding="utf-8", errors="ignore") as tf:
                for idx, line in enumerate(tf, start=1):
                    if re.search(r"\bBugFlags\b|\bbug_flags\b", line, re.IGNORECASE):
                        forbidden_hits.append(f"{telemetry_path.name}:{idx}")
        except Exception:
            pass

    token_status = "PASS" if not forbidden_hits else "FAIL"
    print(f"[check] Forbidden Tokens Scan: {token_status} (hits: {len(forbidden_hits)})")

    if forbidden_hits:
        print("[check] Forbidden token location hits (file:line):")
        for hit in forbidden_hits[:20]:
            print(f"  {hit}")
        if len(forbidden_hits) > 20:
            print(f"  ... and {len(forbidden_hits) - 20} more hits")

    return not drift_detected and len(forbidden_hits) == 0


def main() -> None:
    parser = argparse.ArgumentParser(description="Sanitize Godot Game Source & Verify Integrity")
    parser.add_argument("--build", action="store_true", help="Build sanitized source from real source")
    parser.add_argument("--check", action="store_true", help="Verify manifest and scan for forbidden tokens")
    parser.add_argument("--src", type=str, default=str(ROOT / "_private" / "real_src_mirror"), help="Source dir")
    parser.add_argument("--proj", type=str, default=None, help="project.godot path")
    parser.add_argument("--out", type=str, default=str(ROOT / "game_src"), help="Output sanitized game_src")
    parser.add_argument("--target", type=str, default=str(ROOT / "game_src"), help="Target dir for check")
    parser.add_argument("--manifest", type=str, default=None, help="Manifest path for check")
    parser.add_argument("--telemetry", type=str, default=None, help="Telemetry path to scan")

    args = parser.parse_args()

    if args.build:
        build_sanitized_source(Path(args.src), Path(args.proj) if args.proj else None, Path(args.out))
    elif args.check:
        ok = check_sanitized_source(Path(args.target), Path(args.manifest) if args.manifest else None, Path(args.telemetry) if args.telemetry else None)
        sys.exit(0 if ok else 1)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
