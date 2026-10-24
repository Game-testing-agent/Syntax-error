"""Code Loader: Discovers GDScript source files and feeds relevant code context to the LLM."""
from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Optional

from schemas import Event

ROOT = Path(__file__).parent
LOCAL_SRC = ROOT / "game_src"
EXTERNAL_SRC = ROOT.parent / "Syntax-error" / "godot-4game" / "src"


def find_source_dir() -> Path:
    """Returns the game source directory (prefers local game_src, falls back to Syntax-error)."""
    if LOCAL_SRC.exists() and any(LOCAL_SRC.rglob("*.gd")):
        return LOCAL_SRC
    if EXTERNAL_SRC.exists() and any(EXTERNAL_SRC.rglob("*.gd")):
        return EXTERNAL_SRC
    return LOCAL_SRC


def load_script_with_line_numbers(path: Path) -> str:
    """Reads a script and prefixes each line with its 1-indexed line number."""
    if not path.exists():
        return ""
    lines = path.read_text(encoding="utf-8").splitlines()
    return "\n".join(f"L{i}: {line}" for i, line in enumerate(lines, start=1))


def _resolve_script_dependencies(
    script_names: set[str],
    file_map: dict[str, Path],
    autoload_map: dict[str, str],
) -> set[str]:
    """Expands selected scripts with their extends base classes and referenced autoloads."""
    resolved = set(script_names)
    queue = list(script_names)

    while queue:
        current_name = queue.pop(0)
        current_path = file_map.get(current_name)
        if not current_path or not current_path.exists():
            continue

        try:
            content = current_path.read_text(encoding="utf-8")
        except Exception:
            continue

        # (a) Check 'extends <Class>'
        m_extends = re.search(r"^\s*extends\s+(\w+)", content, re.MULTILINE)
        if m_extends:
            base_class = m_extends.group(1)
            candidate_base = f"{base_class}.gd"
            if candidate_base in file_map and candidate_base not in resolved:
                resolved.add(candidate_base)
                queue.append(candidate_base)

        # (b) Check referenced autoloads
        for al_name, al_file in autoload_map.items():
            if al_name in content and al_file in file_map and al_file not in resolved:
                resolved.add(al_file)
                queue.append(al_file)

    return resolved


ALL_GD_LINE_CAP = 3000


def get_game_codebase_context(events: list[Event], max_lines: int = 5000) -> str:
    """Selects relevant GDScript source files and referenced .tscn scenes for the review window.

    If the total lines of all GDScript files in the codebase is under ALL_GD_LINE_CAP (3,000 lines),
    all .gd files are included in every window; otherwise falls back to dependency resolution.
    Also includes .tscn scene files that reference any included scripts, annotated with line numbers.
    """
    src_dir = find_source_dir()
    if not src_dir.exists():
        return "No GDScript source files found."

    file_map = {p.name: p for p in src_dir.rglob("*.gd")}
    tscn_map = {p.name: p for p in src_dir.rglob("*.tscn")}

    # Calculate total GDScript line count
    total_gd_lines = sum(
        len(p.read_text(encoding="utf-8", errors="ignore").splitlines())
        for p in file_map.values()
    )

    # Autoload mapping from project architecture
    autoload_map = {
        "PlayerData": "PlayerData.gd",
        "GameLogger": "GameLogger.gd",
    }

    # Step 1: Determine included GDScript files
    if total_gd_lines <= ALL_GD_LINE_CAP:
        # Full codebase inclusion mode: all .gd files included
        resolved_scripts = set(file_map.keys())
    else:
        # Fallback mode: dynamic dependency resolution based on window events
        active_scripts: set[str] = set()
        for e in events:
            ev = (e.event or "").lower()
            cat = (e.category or "").lower()
            if cat in ("enemy", "player_lifecycle", "player_movement") or "player" in ev:
                active_scripts.add("Player.gd")
                active_scripts.add("Enemy.gd")
            if "enemy" in ev or "stomp" in ev:
                active_scripts.add("Enemy.gd")
            if cat == "collectible" or "coin" in ev:
                active_scripts.add("Coin.gd")
            if cat == "portal" or "scene" in ev:
                active_scripts.add("Portal2D.gd")
            if "score" in ev or "death" in ev:
                active_scripts.add("PlayerData.gd")

        if not active_scripts:
            active_scripts.add("Player.gd")
            active_scripts.add("Enemy.gd")

        resolved_scripts = _resolve_script_dependencies(active_scripts, file_map, autoload_map)
        if "GameLogger.gd" in file_map:
            resolved_scripts.add("GameLogger.gd")

    code_sections = []
    lines_used = 0
    dropped_files = []

    # Sort scripts with primary gameplay entities first, then bases/autoloads/others
    priority_order = [
        "Player.gd", "Enemy.gd", "Coin.gd", "Portal2D.gd",
        "Actor.gd", "PlayerData.gd", "GameLogger.gd",
        "UserInterface.gd", "EndScreen.gd"
    ]
    sorted_scripts = sorted(
        resolved_scripts,
        key=lambda s: (priority_order.index(s) if s in priority_order else 99, s),
    )

    for script_name in sorted_scripts:
        gd_file = file_map.get(script_name)
        if not gd_file:
            continue

        annotated = load_script_with_line_numbers(gd_file)
        file_lines = annotated.splitlines()

        if lines_used >= max_lines:
            dropped_files.append(script_name)
            continue

        if lines_used + len(file_lines) > max_lines:
            remaining_budget = max(40, max_lines - lines_used)
            file_lines = file_lines[:remaining_budget]
            file_lines.append("... (remaining lines truncated for brevity)")

        lines_used += len(file_lines)
        code_sections.append(
            f"### {gd_file.name} ({gd_file.relative_to(src_dir).as_posix()})\n```gdscript\n"
            + "\n".join(file_lines)
            + "\n```"
        )

    # Step 2: Include .tscn scenes that reference included scripts
    referenced_tscns: set[str] = set()
    for t_name, t_path in tscn_map.items():
        try:
            content = t_path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        if any(gd in content for gd in resolved_scripts):
            referenced_tscns.add(t_name)

    # Propagate instanced scene references (e.g., Level01 instances Portal2D.tscn)
    for t_name, t_path in tscn_map.items():
        try:
            content = t_path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        if any(ts in content for ts in list(referenced_tscns)):
            referenced_tscns.add(t_name)

    priority_tscn = [
        "Player.tscn", "Enemy.tscn", "Coin.tscn", "Portal2D.tscn",
        "PlayerData.tscn", "Level01.tscn", "Level02.tscn", "UserInterface.tscn"
    ]
    sorted_tscns = sorted(
        referenced_tscns,
        key=lambda t: (priority_tscn.index(t) if t in priority_tscn else 99, t),
    )

    for t_name in sorted_tscns:
        t_file = tscn_map.get(t_name)
        if not t_file:
            continue

        annotated = load_script_with_line_numbers(t_file)
        tscn_lines = annotated.splitlines()

        if lines_used >= max_lines:
            dropped_files.append(t_name)
            continue

        if lines_used + len(tscn_lines) > max_lines:
            remaining_budget = max(40, max_lines - lines_used)
            tscn_lines = tscn_lines[:remaining_budget]
            tscn_lines.append("... (remaining lines truncated for brevity)")

        lines_used += len(tscn_lines)
        code_sections.append(
            f"### {t_file.name} ({t_file.relative_to(src_dir).as_posix()})\n```tscn\n"
            + "\n".join(tscn_lines)
            + "\n```"
        )

    if dropped_files:
        code_sections.append(f"<!-- Budget notice: Dropped lower-priority files: {', '.join(dropped_files)} -->")

    return "\n\n".join(code_sections)

