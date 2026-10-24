#!/usr/bin/env python3
"""
run_map.py — Terminal Launcher for QA Benchmark Maps

Usage:
  python run_map.py --list
  python run_map.py --map 1
  python run_map.py --map 3 --debug
  python run_map.py --map 2 --headless --frames 600
"""

import os
import sys
import shutil
import argparse
import subprocess
from glob import glob

MAPS = {
    1: {
        "title": "Map 1: Green Hills",
        "slug": "map1_green_hills",
        "scene": "res://src/Levels/Map1_GreenHills.tscn",
        "desc": "Lush grassy hills with open terrain, floating platforms, and hidden pits."
    },
    2: {
        "title": "Map 2: Underground Caves",
        "slug": "map2_underground_caves",
        "scene": "res://src/Levels/Map2_UndergroundCaves.tscn",
        "desc": "Dark subterranean caverns with narrow ceiling wedges, uneven rock floors, and chasms."
    },
    3: {
        "title": "Map 3: Sky Castle",
        "slug": "map3_sky_castle",
        "scene": "res://src/Levels/Map3_SkyCastle.tscn",
        "desc": "Floating sky fortress featuring steep staircases, airborne islands, and high ramparts."
    },
    4: {
        "title": "Map 4: Lava Fortress",
        "slug": "map4_lava_fortress",
        "scene": "res://src/Levels/Map4_LavaFortress.tscn",
        "desc": "Volcanic stronghold with bubbling lava pools, tight corridors, and guarded exit gates."
    }
}


def find_godot_binary() -> str:
    """Finds a valid Godot 4 executable path or returns empty string."""
    env_bin = os.environ.get("GODOT_BIN")
    if env_bin and os.path.isfile(env_bin):
        return env_bin

    root_dir = os.path.dirname(os.path.abspath(__file__))
    candidates = [
        os.path.join(root_dir, "engine", "godot.exe"),
        os.path.join(root_dir, "engine", "Godot_v4.3-stable_win64.exe"),
        os.path.join(root_dir, "engine", "Godot_v4.4-stable_win64.exe"),
    ]

    home = os.path.expanduser("~")
    dl_pattern = os.path.join(home, "Downloads", "Godot*", "*win64_console.exe")
    for p in glob(dl_pattern):
        candidates.append(p)
    dl_pattern_exe = os.path.join(home, "Downloads", "Godot*", "*win64.exe")
    for p in glob(dl_pattern_exe):
        candidates.append(p)

    for c in candidates:
        if os.path.isfile(c):
            return c

    which_godot = shutil.which("godot") or shutil.which("godot.exe")
    if which_godot:
        return which_godot

    return ""


def main():
    parser = argparse.ArgumentParser(description="Launcher for QA Benchmark Maps", add_help=False)
    parser.add_argument("--map", type=str, default=None, help="Map number to load (1, 2, 3, or 4)")
    parser.add_argument("--list", action="store_true", help="List all available maps")
    parser.add_argument("--debug", action="store_true", help="Run with debug logging enabled")
    parser.add_argument("--headless", action="store_true", help="Run Godot in headless mode")
    parser.add_argument("--frames", type=int, default=None, help="Automatically exit after N frames")
    parser.add_argument("-h", "--help", action="store_true", help="Show help message")

    args = parser.parse_args()

    if args.help:
        print(__doc__)
        sys.exit(0)

    if args.list:
        print("Available QA Benchmark Maps:")
        for num, info in sorted(MAPS.items()):
            print(f"  [{num}] {info['title']} - {info['desc']}")
        sys.exit(0)

    if args.map is None:
        print("Error: Missing required argument '--map <N>' or '--list'. Run with --help for usage.", file=sys.stderr)
        sys.exit(1)

    try:
        map_num = int(args.map)
        if map_num not in MAPS:
            raise ValueError()
    except ValueError:
        print(f"Error: Invalid map number '{args.map}'. Valid options are 1, 2, 3, 4.", file=sys.stderr)
        sys.exit(1)

    godot_bin = find_godot_binary()
    if not godot_bin:
        print("Error: Godot executable not found. Please set GODOT_BIN environment variable or place Godot in 'engine/' folder.", file=sys.stderr)
        sys.exit(1)

    root_dir = os.path.dirname(os.path.abspath(__file__))
    project_dir = os.path.join(root_dir, "godot-4game")
    map_info = MAPS[map_num]
    log_dir = os.path.join(root_dir, "maps", map_info["slug"], "logs")
    os.makedirs(log_dir, exist_ok=True)

    cmd = [godot_bin]
    if args.headless:
        cmd.append("--headless")
    cmd.extend(["--path", project_dir, "--"])
    cmd.append(f"--map={map_num}")
    cmd.append(f"--log-dir={log_dir}")
    if args.debug:
        cmd.append("--debug")
    if args.frames is not None:
        if args.frames <= 0:
            print(f"Error: --frames must be a positive integer, got '{args.frames}'.", file=sys.stderr)
            sys.exit(1)
        cmd.append(f"--frames={args.frames}")

    print(f"Launching {map_info['title']}...")
    print(f"Logs destination: {log_dir}")

    try:
        proc = subprocess.run(cmd)
        sys.exit(proc.returncode)
    except KeyboardInterrupt:
        print("\nSession interrupted by user.")
        sys.exit(0)
    except Exception as e:
        print(f"Error launching game process: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

