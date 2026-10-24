#!/usr/bin/env python3
"""
level1_coordinate_recorder.py — Standalone Level 1 Coordinate Recorder for Godot 2D Platformer

Records player's world-space (x, y) coordinates continuously during manual Level 1 gameplay.
- Completely passive: never restarts the game, never modifies player controls or inputs.
- Continues recording across deaths and respawns.
- Only stops when 'over' is typed into the terminal.
- Rounds coordinates to whole numbers (integers) to remove sub-pixel noise and reduce data size.
- Saves raw data into a unique session directory.
- Post-processes cleaned data: removes redundant consecutive coordinates while preserving
  meaningful changes in position, and groups coordinates into traversable regions and platform segments.
- Telemetry constraint: records coordinates (x, y) only. No timestamps, velocities, physics frames,
  inputs, or screenshots.
"""

import os
import sys
import time
import json
import uuid
import math
import csv
import argparse
import threading
from datetime import datetime
from typing import Optional, Dict, List, Any, Tuple


DEFAULT_STATE_FILENAMES = ["latest_state.json"]
POLL_INTERVAL_SECONDS = 0.025  # ~40 Hz polling (GameLogger exports at ~15 Hz)
STATIONARY_EPSILON = 1.0       # Minimum movement in pixels to consider non-redundant
RESPAWN_GAP_THRESHOLD = 250.0  # Discontinuity threshold marking respawn / attempt boundary
PLATFORM_Y_TOLERANCE = 8.0     # Height tolerance for grouping into horizontal platform segments
PLATFORM_X_MAX_GAP = 90.0      # Maximum horizontal gap to group points into the same platform


class Level1CoordinateRecorder:
    """Manages continuous recording and post-processing of Level 1 coordinates."""

    def __init__(self, workspace_dir: Optional[str] = None, output_base_dir: Optional[str] = None):
        self.workspace_dir = os.path.abspath(workspace_dir or os.getcwd())
        self.output_base_dir = output_base_dir or os.path.join(self.workspace_dir, "recordings", "level1_coordinates")

        # Unique session directory (never overwrites previous sessions)
        timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        unique_token = uuid.uuid4().hex[:6]
        self.session_id = f"session_{timestamp_str}_{unique_token}"
        self.session_dir = os.path.join(self.output_base_dir, self.session_id)

        # Threading control
        self.stop_event = threading.Event()
        self.recording_thread: Optional[threading.Thread] = None

        # Data store: list of dicts with {"x": int, "y": int}
        self.raw_coordinates: List[Dict[str, int]] = []
        self._lock = threading.Lock()

        # Telemetry tracking
        self.last_recorded_pos: Optional[Tuple[int, int]] = None
        self.last_seen_frame: int = -1
        self.state_file_path: Optional[str] = None
        self.is_player_currently_alive: bool = False
        self.total_deaths_observed: int = 0
        self.active_level_detected: bool = False

    def find_state_file(self) -> Optional[str]:
        """Locates the active latest_state.json file in workspace or godot subfolder."""
        candidate_paths = [
            os.path.join(self.workspace_dir, "latest_state.json"),
            os.path.join(self.workspace_dir, "godot-4game", "latest_state.json"),
            os.path.join(self.workspace_dir, "game", "latest_state.json"),
        ]

        # Also check Godot user-data dir if APPDATA is present
        appdata = os.getenv("APPDATA")
        if appdata:
            candidate_paths.append(
                os.path.join(appdata, "Godot", "app_userdata", "Your First Game: 2d Platformer", "latest_state.json")
            )

        existing_candidates = [p for p in candidate_paths if os.path.exists(p)]
        if not existing_candidates:
            return None

        # Return the most recently modified candidate
        return max(existing_candidates, key=lambda p: os.path.getmtime(p))

    def _read_game_state(self) -> Optional[Dict[str, Any]]:
        """Safely reads latest_state.json without blocking on write locks."""
        if not self.state_file_path or not os.path.exists(self.state_file_path):
            self.state_file_path = self.find_state_file()
            if not self.state_file_path:
                return None

        try:
            with open(self.state_file_path, "r", encoding="utf-8", errors="replace") as f:
                return json.load(f)
        except (OSError, json.JSONDecodeError, PermissionError):
            return None

    def _record_loop(self) -> None:
        """Continuous background sampling loop."""
        os.makedirs(self.session_dir, exist_ok=True)
        raw_csv_path = os.path.join(self.session_dir, "raw_coordinates.csv")

        # Open raw CSV stream for progressive real-time flushing
        with open(raw_csv_path, "w", newline="", encoding="utf-8") as csv_file:
            csv_writer = csv.writer(csv_file)
            csv_writer.writerow(["x", "y"])
            csv_file.flush()

            last_wait_log_time = 0.0

            while not self.stop_event.is_set():
                state = self._read_game_state()

                if not state:
                    now = time.time()
                    if now - last_wait_log_time >= 4.0:
                        print("[WAITING] Waiting for Godot game to start and write telemetry...")
                        last_wait_log_time = now
                    time.sleep(POLL_INTERVAL_SECONDS)
                    continue

                scene = str(state.get("scene", ""))
                # Focus exclusively on Level 1
                if scene != "Level01" and "Level01" not in scene:
                    if self.active_level_detected:
                        print(f"[STATUS] Player not in Level 1 (current: '{scene}'). Recording paused.")
                        self.active_level_detected = False
                    time.sleep(POLL_INTERVAL_SECONDS * 2)
                    continue

                if not self.active_level_detected:
                    print(f"[ACTIVE] Level 1 detected ({scene})! Coordinates recording active.")
                    self.active_level_detected = True

                player_data = state.get("player") or {}
                is_alive = bool(player_data.get("alive", False))
                frame = int(state.get("frame", state.get("physics_frame", 0)))

                # Detect death / respawn transitions
                if not is_alive and self.is_player_currently_alive:
                    self.is_player_currently_alive = False
                    self.total_deaths_observed += 1
                    print(f"[EVENT] Player died (Death #{self.total_deaths_observed}). Waiting for retry/respawn...")
                elif is_alive and not self.is_player_currently_alive:
                    self.is_player_currently_alive = True
                    if self.total_deaths_observed > 0:
                        print(f"[EVENT] Player respawned! Continuing Level 1 recording...")

                if is_alive:
                    pos = player_data.get("position")
                    if pos and "x" in pos and "y" in pos:
                        # Round to whole numbers (integers)
                        x = int(round(float(pos["x"])))
                        y = int(round(float(pos["y"])))

                        # Only record if frame changed or position moved
                        if frame != self.last_seen_frame or self.last_recorded_pos is None:
                            self.last_seen_frame = frame
                            coord = {"x": x, "y": y}

                            with self._lock:
                                self.raw_coordinates.append(coord)
                                self.last_recorded_pos = (x, y)

                            # Progressively flush to raw CSV
                            csv_writer.writerow([x, y])
                            csv_file.flush()

                time.sleep(POLL_INTERVAL_SECONDS)

        # After loop finishes, save complete raw_coordinates.json
        raw_json_path = os.path.join(self.session_dir, "raw_coordinates.json")
        with self._lock:
            with open(raw_json_path, "w", encoding="utf-8") as f:
                json.dump(self.raw_coordinates, f, indent=2)

    def start(self) -> None:
        """Starts recording in a background thread."""
        self.stop_event.clear()
        self.recording_thread = threading.Thread(target=self._record_loop, daemon=True)
        self.recording_thread.start()

    def stop(self) -> None:
        """Signals recording thread to stop and waits for completion."""
        self.stop_event.set()
        if self.recording_thread and self.recording_thread.is_alive():
            self.recording_thread.join(timeout=3.0)


# ==============================================================================
# POST-PROCESSING: CLEANING & GROUPING ALGORITHMS
# ==============================================================================

def clean_coordinates(raw_coords: List[Dict[str, Any]],
                      min_dist_epsilon: float = STATIONARY_EPSILON,
                      max_step_dist: float = 35.0) -> List[Dict[str, int]]:
    """
    Cleans raw coordinates by:
    1. Rounding coordinates to integers (whole pixels).
    2. Removing redundant consecutive coordinates when stationary or under min_dist_epsilon.
    3. Preserving meaningful changes in position (movement start/end, direction changes,
       jump apexes, landings, and respawn teleports).
    4. Retaining strictly coordinates only (x, y).
    """
    if not raw_coords:
        return []

    # Ensure integer coordinates
    int_coords: List[Dict[str, int]] = [
        {"x": int(round(float(p["x"]))), "y": int(round(float(p["y"])))}
        for p in raw_coords
    ]

    # Step 1: Remove consecutive identical / sub-threshold points (stationary deduplication)
    deduped: List[Dict[str, int]] = [int_coords[0]]
    for pt in int_coords[1:]:
        last_pt = deduped[-1]
        dx = pt["x"] - last_pt["x"]
        dy = pt["y"] - last_pt["y"]
        dist = math.hypot(dx, dy)
        if dist >= min_dist_epsilon:
            deduped.append(pt)

    if len(deduped) <= 2:
        return deduped

    # Step 2: Segment into continuous runs between respawns / teleports
    runs: List[List[Dict[str, int]]] = []
    current_run: List[Dict[str, int]] = [deduped[0]]

    for i in range(1, len(deduped)):
        prev = deduped[i - 1]
        curr = deduped[i]
        dist = math.hypot(curr["x"] - prev["x"], curr["y"] - prev["y"])
        if dist > RESPAWN_GAP_THRESHOLD:
            # Respawn jump detected: finish current run, start new run
            runs.append(current_run)
            current_run = [curr]
        else:
            current_run.append(curr)

    if current_run:
        runs.append(current_run)

    # Step 3: Simplify each run while preserving direction changes, jump arcs, and step resolutions
    cleaned: List[Dict[str, int]] = []

    for run in runs:
        if len(run) <= 2:
            cleaned.extend(run)
            continue

        run_cleaned: List[Dict[str, int]] = [run[0]]
        accumulated_dist = 0.0

        for i in range(1, len(run) - 1):
            prev = run[i - 1]
            curr = run[i]
            nxt = run[i + 1]

            d_step = math.hypot(curr["x"] - prev["x"], curr["y"] - prev["y"])
            accumulated_dist += d_step

            # Vectors for angle/direction change check
            v1_x = curr["x"] - prev["x"]
            v1_y = curr["y"] - prev["y"]
            v2_x = nxt["x"] - curr["x"]
            v2_y = nxt["y"] - curr["y"]

            mag1 = math.hypot(v1_x, v1_y)
            mag2 = math.hypot(v2_x, v2_y)

            is_inflection = False
            if mag1 > 0.1 and mag2 > 0.1:
                cos_angle = (v1_x * v2_x + v1_y * v2_y) / (mag1 * mag2)
                cos_angle = max(-1.0, min(1.0, cos_angle))
                # Angle change > ~25 degrees (cos_angle < 0.90) indicates direction change
                if cos_angle < 0.90:
                    is_inflection = True

            # Jump apex detection: peak height in 2D platformer (local minimum y)
            is_jump_apex = (curr["y"] < prev["y"]) and (curr["y"] < nxt["y"])
            # Landing point detection: local maximum y where downward motion stops
            is_landing = (curr["y"] > prev["y"]) and (abs(nxt["y"] - curr["y"]) <= 1.0)

            if is_inflection or is_jump_apex or is_landing or accumulated_dist >= max_step_dist:
                run_cleaned.append(curr)
                accumulated_dist = 0.0

        run_cleaned.append(run[-1])
        cleaned.extend(run_cleaned)

    return cleaned


def extract_platform_segments(coords: List[Dict[str, Any]],
                              y_tolerance: float = PLATFORM_Y_TOLERANCE,
                              max_x_gap: float = PLATFORM_X_MAX_GAP) -> List[Dict[str, Any]]:
    """
    Groups coordinates into horizontal platform segments.
    Detects consistent elevation bands where horizontal locomotion occurred.
    """
    if len(coords) < 2:
        return []

    # Ensure integer coordinates
    int_coords = [
        {"x": int(round(float(p["x"]))), "y": int(round(float(p["y"])))}
        for p in coords
    ]

    # Filter candidate points that are part of horizontal traversals (small vertical delta)
    grounded_points: List[Dict[str, int]] = []
    for i in range(len(int_coords)):
        curr = int_coords[i]
        is_horiz = False
        if i > 0 and abs(int_coords[i]["y"] - int_coords[i - 1]["y"]) <= y_tolerance:
            is_horiz = True
        elif i < len(int_coords) - 1 and abs(int_coords[i + 1]["y"] - int_coords[i]["y"]) <= y_tolerance:
            is_horiz = True

        if is_horiz:
            grounded_points.append(curr)

    if not grounded_points:
        return []

    # Cluster points by elevation Y
    sorted_by_y = sorted(grounded_points, key=lambda p: p["y"])
    elevation_clusters: List[List[Dict[str, int]]] = []
    current_cluster: List[Dict[str, int]] = [sorted_by_y[0]]

    for pt in sorted_by_y[1:]:
        if abs(pt["y"] - current_cluster[0]["y"]) <= y_tolerance:
            current_cluster.append(pt)
        else:
            elevation_clusters.append(current_cluster)
            current_cluster = [pt]
    if current_cluster:
        elevation_clusters.append(current_cluster)

    platform_segments: List[Dict[str, Any]] = []
    segment_id = 1

    for cluster in elevation_clusters:
        # Sort cluster by X to identify contiguous platform spans
        sorted_by_x = sorted(cluster, key=lambda p: p["x"])
        sub_spans: List[List[Dict[str, int]]] = []
        current_span: List[Dict[str, int]] = [sorted_by_x[0]]

        for pt in sorted_by_x[1:]:
            if pt["x"] - current_span[-1]["x"] <= max_x_gap:
                current_span.append(pt)
            else:
                sub_spans.append(current_span)
                current_span = [pt]
        if current_span:
            sub_spans.append(current_span)

        for span in sub_spans:
            x_vals = [p["x"] for p in span]
            y_vals = [p["y"] for p in span]
            x_min = min(x_vals)
            x_max = max(x_vals)
            span_width = x_max - x_min

            # Minimum span width or point count for a platform
            if span_width >= 20 or len(span) >= 3:
                approx_y = int(round(sum(y_vals) / len(y_vals)))
                platform_segments.append({
                    "segment_id": segment_id,
                    "elevation_y": approx_y,
                    "x_start": x_min,
                    "x_end": x_max,
                    "span_width": span_width,
                    "point_count": len(span),
                    "coordinates": [{"x": p["x"], "y": p["y"]} for p in span]
                })
                segment_id += 1

    # Sort platform segments horizontally by x_start
    platform_segments.sort(key=lambda s: (s["x_start"], s["elevation_y"]))
    # Re-index segment IDs neatly
    for idx, seg in enumerate(platform_segments, start=1):
        seg["segment_id"] = idx

    return platform_segments


def extract_traversable_regions(coords: List[Dict[str, Any]],
                                platform_segments: List[Dict[str, Any]],
                                max_cluster_gap: float = 220.0) -> List[Dict[str, Any]]:
    """
    Groups coordinates into connected traversable regions.
    Identifies spatial bounding zones of player exploration in Level 1.
    """
    if not coords:
        return []

    # Ensure integer coordinates
    int_coords = [
        {"x": int(round(float(p["x"]))), "y": int(round(float(p["y"])))}
        for p in coords
    ]

    sorted_coords = sorted(int_coords, key=lambda p: p["x"])
    regions: List[List[Dict[str, int]]] = []
    current_region: List[Dict[str, int]] = [sorted_coords[0]]

    for pt in sorted_coords[1:]:
        prev = current_region[-1]
        if pt["x"] - prev["x"] <= max_cluster_gap:
            current_region.append(pt)
        else:
            regions.append(current_region)
            current_region = [pt]
    if current_region:
        regions.append(current_region)

    traversable_regions: List[Dict[str, Any]] = []
    for idx, reg_coords in enumerate(regions, start=1):
        xs = [p["x"] for p in reg_coords]
        ys = [p["y"] for p in reg_coords]
        x_min, x_max = min(xs), max(xs)
        y_min, y_max = min(ys), max(ys)

        # Match platform segments that fall within this traversable region
        matched_segment_ids = [
            seg["segment_id"] for seg in platform_segments
            if x_min - 20 <= seg["x_start"] <= x_max + 20
        ]

        traversable_regions.append({
            "region_id": idx,
            "bounds": {
                "x_min": x_min,
                "x_max": x_max,
                "y_min": y_min,
                "y_max": y_max
            },
            "span": {
                "width": x_max - x_min,
                "height": y_max - y_min
            },
            "point_count": len(reg_coords),
            "platform_segment_ids": matched_segment_ids,
            "coordinates": [{"x": p["x"], "y": p["y"]} for p in reg_coords]
        })

    return traversable_regions


def process_and_save_session(session_dir: str, raw_coords: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Processes collected coordinates and writes all cleaned outputs.
    Ensures raw data is preserved as integers and cleaned coordinates are saved as JSON and CSV.
    """
    os.makedirs(session_dir, exist_ok=True)

    # 1. Round raw coordinates to integers
    int_raw_coords: List[Dict[str, int]] = [
        {"x": int(round(float(p["x"]))), "y": int(round(float(p["y"])))}
        for p in raw_coords
    ]

    # Save raw coordinates (JSON & CSV)
    raw_json_path = os.path.join(session_dir, "raw_coordinates.json")
    with open(raw_json_path, "w", encoding="utf-8") as f:
        json.dump(int_raw_coords, f, indent=2)

    raw_csv_path = os.path.join(session_dir, "raw_coordinates.csv")
    with open(raw_csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["x", "y"])
        for p in int_raw_coords:
            writer.writerow([p["x"], p["y"]])

    # 2. Clean coordinates (remove redundant stationary points, preserve inflections & runs)
    cleaned_coords = clean_coordinates(int_raw_coords)

    # 3. Extract platform segments & traversable regions
    platform_segments = extract_platform_segments(cleaned_coords)
    traversable_regions = extract_traversable_regions(cleaned_coords, platform_segments)

    # 4. Save cleaned coordinates as CSV (pure whole numbers x, y)
    cleaned_csv_path = os.path.join(session_dir, "cleaned_coordinates.csv")
    with open(cleaned_csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["x", "y"])
        for p in cleaned_coords:
            writer.writerow([p["x"], p["y"]])

    # 5. Save cleaned coordinates & groupings as JSON
    cleaned_payload = {
        "summary": {
            "session_id": os.path.basename(session_dir),
            "level": "Level01",
            "raw_point_count": len(int_raw_coords),
            "cleaned_point_count": len(cleaned_coords),
            "redundancy_reduction_percent": round(
                (1.0 - len(cleaned_coords) / max(1, len(int_raw_coords))) * 100.0, 2
            ),
            "platform_segment_count": len(platform_segments),
            "traversable_region_count": len(traversable_regions)
        },
        "cleaned_coordinates": cleaned_coords,
        "platform_segments": platform_segments,
        "traversable_regions": traversable_regions
    }

    cleaned_json_path = os.path.join(session_dir, "cleaned_coordinates.json")
    with open(cleaned_json_path, "w", encoding="utf-8") as f:
        json.dump(cleaned_payload, f, indent=2)

    # 6. Save dedicated traversable segments file for modular consumption
    segments_json_path = os.path.join(session_dir, "traversable_segments.json")
    with open(segments_json_path, "w", encoding="utf-8") as f:
        json.dump({
            "platform_segments": platform_segments,
            "traversable_regions": traversable_regions
        }, f, indent=2)

    return {
        "raw_json": raw_json_path,
        "raw_csv": raw_csv_path,
        "cleaned_json": cleaned_json_path,
        "cleaned_csv": cleaned_csv_path,
        "segments_json": segments_json_path,
        "summary": cleaned_payload["summary"]
    }


def reprocess_session(session_dir: str) -> Optional[Dict[str, Any]]:
    """Loads existing raw coordinates from a session directory and reprocesses with integer rounding."""
    if not os.path.isdir(session_dir):
        print(f"[ERROR] Session directory '{session_dir}' does not exist.")
        return None

    raw_json_path = os.path.join(session_dir, "raw_coordinates.json")
    raw_csv_path = os.path.join(session_dir, "raw_coordinates.csv")

    raw_coords: List[Dict[str, Any]] = []

    if os.path.exists(raw_json_path):
        try:
            with open(raw_json_path, "r", encoding="utf-8") as f:
                raw_coords = json.load(f)
        except Exception as e:
            print(f"[WARN] Could not load {raw_json_path}: {e}")

    if not raw_coords and os.path.exists(raw_csv_path):
        try:
            with open(raw_csv_path, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    raw_coords.append({"x": float(row["x"]), "y": float(row["y"])})
        except Exception as e:
            print(f"[ERROR] Could not load {raw_csv_path}: {e}")
            return None

    if not raw_coords:
        print(f"[ERROR] No raw coordinates found in '{session_dir}'.")
        return None

    print(f"[STATUS] Reprocessing {len(raw_coords)} coordinates with integer rounding...")
    return process_and_save_session(session_dir, raw_coords)


# ==============================================================================
# MAIN TERMINAL INTERFACE
# ==============================================================================

def main():
    """CLI Entrypoint for the Level 1 Coordinate Recorder."""
    parser = argparse.ArgumentParser(description="Standalone Level 1 Coordinate Recorder for Godot 2D Platformer")
    parser.add_argument("--reprocess", type=str, default="", help="Path to existing session folder to reprocess with integer rounding")
    args = parser.parse_args()

    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

    if args.reprocess:
        target_dir = os.path.abspath(args.reprocess)
        print("=" * 80)
        print("   🔄 REPROCESSING EXISTING SESSION WITH INTEGER ROUNDING")
        print("=" * 80)
        print(f"  Target Session   : {target_dir}")
        print("=" * 80 + "\n")
        results = reprocess_session(target_dir)
        if results:
            summary = results["summary"]
            print("\n" + "=" * 80)
            print("   ✅ REPROCESSING COMPLETE")
            print("=" * 80)
            print(f"  Raw Coordinates (Rounded)   : {summary['raw_point_count']}")
            print(f"  Cleaned Coordinates Saved   : {summary['cleaned_point_count']}")
            print(f"  Redundant Points Filtered   : {summary['redundancy_reduction_percent']}%")
            print(f"  Platform Segments Detected  : {summary['platform_segment_count']}")
            print(f"  Traversable Regions Mapped  : {summary['traversable_region_count']}")
            print("-" * 80)
            print("  SAVED FILES:")
            print(f"  📄 Raw (JSON)       : {results['raw_json']}")
            print(f"  📄 Raw (CSV)        : {results['raw_csv']}")
            print(f"  📄 Cleaned (JSON)   : {results['cleaned_json']}")
            print(f"  📄 Cleaned (CSV)    : {results['cleaned_csv']}")
            print(f"  📄 Segments (JSON)  : {results['segments_json']}")
            print("=" * 80 + "\n")
        return

    recorder = Level1CoordinateRecorder()

    print("=" * 80)
    print("   🎮 GODOT LEVEL 1 COORDINATE RECORDER (STANDALONE)")
    print("=" * 80)
    print(f"  Target Level     : Level01 (Godot 4 2D Platformer)")
    print(f"  Session ID       : {recorder.session_id}")
    print(f"  Output Directory : {recorder.session_dir}")
    print("=" * 80)
    print("  INSTRUCTIONS:")
    print("  1. Launch or keep Godot running on Level 1 (run_game.bat).")
    print("  2. Play normally using keyboard/controller.")
    print("  3. Die and retry as many times as needed — recording persists seamlessly.")
    print("  4. When you are finished, type 'over' and press Enter below.")
    print("=" * 80 + "\n")

    # Start continuous recording thread
    recorder.start()
    print("[STATUS] Recorder is listening for player coordinates...")

    # Wait for user to type 'over'
    while True:
        try:
            line = input("Type 'over' to finish recording: ").strip().lower()
            if line == "over":
                print("\n[STOP] 'over' command received. Finalizing recording session...")
                break
            elif line:
                print(f"[NOTE] Unknown command '{line}'. Type 'over' when you wish to finish recording.")
        except (KeyboardInterrupt, EOFError):
            print("\n[STOP] Exit signal received. Finalizing recording session...")
            break

    # Stop recording thread
    recorder.stop()

    with recorder._lock:
        captured_coords = list(recorder.raw_coordinates)

    print(f"[STATUS] Total raw coordinates captured: {len(captured_coords)}")
    print("[STATUS] Processing coordinates (removing redundancy & grouping platform segments)...")

    results = process_and_save_session(recorder.session_dir, captured_coords)
    summary = results["summary"]

    print("\n" + "=" * 80)
    print("   ✅ LEVEL 1 RECORDING & PROCESSING COMPLETE")
    print("=" * 80)
    print(f"  Raw Coordinates Captured    : {summary['raw_point_count']}")
    print(f"  Cleaned Coordinates Saved   : {summary['cleaned_point_count']}")
    print(f"  Redundant Points Filtered   : {summary['redundancy_reduction_percent']}%")
    print(f"  Platform Segments Detected  : {summary['platform_segment_count']}")
    print(f"  Traversable Regions Mapped  : {summary['traversable_region_count']}")
    print("-" * 80)
    print("  SAVED FILES:")
    print(f"  📁 Session Folder   : {recorder.session_dir}")
    print(f"  📄 Raw (JSON)       : {results['raw_json']}")
    print(f"  📄 Raw (CSV)        : {results['raw_csv']}")
    print(f"  📄 Cleaned (JSON)   : {results['cleaned_json']}")
    print(f"  📄 Cleaned (CSV)    : {results['cleaned_csv']}")
    print(f"  📄 Segments (JSON)  : {results['segments_json']}")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    main()
