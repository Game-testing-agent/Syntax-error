#!/usr/bin/env python3
"""
agentic_tester.py — Autonomous Closed-Loop Game Testing for 2D Platformers

Implements a closed-loop testing workflow:
  observe -> select target -> execute navigation -> evaluate outcome ->
  record evidence -> replan next target -> repeat until budget exhausted.

Targets are grounded in verified reachable coordinates (cleaned_coordinates.json)
to ensure test targets represent genuine player-accessible locations in the level.

Dependencies:
  - bot_controller.py  (LevelRouteManager, HybridBotRunner)
  - explorer.py        (GameController, ActionHistoryRecorder)
  - recordings/level1_coordinates/<session>/cleaned_coordinates.json
  - level_routes.json

Usage:
  python agentic_tester.py [--budget N] [--max-steps-per-target N]
                           [--tolerance PX] [--port N]
                           [--launch] [--results-dir DIR] [--strategy STRATEGY]

Strategies (--strategy):
  coverage   - maximise spatial coverage of unique platform segments  (default)
  risk       - prioritise elevated/hard-to-reach segments first
  systematic - left-to-right sweep of recorded reachable platform points
"""

import os
import sys
import json
import time
import math
import argparse
import hashlib
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from bot_controller import HybridBotRunner, LevelRouteManager
from explorer import (
    GameController, ActionHistoryRecorder,
    TargetCoordinateExplorer, SequentialWaypointsExplorer,
    launch_godot_game,
)

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
DEFAULT_BUDGET           = 20
DEFAULT_STEPS_PER_TARGET = 350
DEFAULT_TOLERANCE        = 70.0
DEFAULT_MAX_ATTEMPTS     = 3
DEFAULT_RESULTS_DIR      = "agentic_test_results"
SEGMENTS_GLOB            = "recordings/level1_coordinates"
GROUND_Y_THRESHOLD       = 750.0

OUTCOME_SUCCESS      = "success"
OUTCOME_DIED         = "died"
OUTCOME_STALL        = "stall"
OUTCOME_STEP_BUDGET  = "step_budget"
OUTCOME_SKIP         = "skip"


# ===========================================================================
# 1.  COORDINATE DATA LOADER
# ===========================================================================

class Level1CoordinateLoader:
    """Loads platform segments and verified reachable coordinates from recorded session."""

    def __init__(self, recordings_dir):
        self.recordings_dir = recordings_dir
        self.segments = []
        self.all_coords = []
        self._load()

    def _find_latest_session(self):
        base = self.recordings_dir
        if not os.path.isdir(base):
            return None
        sessions = sorted(
            [d for d in os.listdir(base) if os.path.isdir(os.path.join(base, d))],
            reverse=True
        )
        return sessions[0] if sessions else None

    def _load(self):
        session = self._find_latest_session()
        if not session:
            print("[CoordinateLoader] No session found in {}".format(self.recordings_dir))
            return
        session_dir = os.path.join(self.recordings_dir, session)
        seg_path   = os.path.join(session_dir, "traversable_segments.json")
        coord_path = os.path.join(session_dir, "cleaned_coordinates.json")

        # Load verified reachable coordinates first
        if os.path.exists(coord_path):
            with open(coord_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.all_coords = data.get("cleaned_coordinates", [])
            if not self.segments:
                self.segments = data.get("platform_segments", [])
            print("[CoordinateLoader] Loaded {} verified reachable coordinates from {}".format(
                len(self.all_coords), session))

        # Fallback or supplementary segment load
        if os.path.exists(seg_path) and not self.segments:
            with open(seg_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.segments = data.get("platform_segments", [])
            print("[CoordinateLoader] Loaded {} platform segments from {}".format(
                len(self.segments), session))

    def midpoints(self):
        """
        Returns representative targets grounded in verified reachable coordinates
        from cleaned_coordinates.json for each platform segment.
        """
        targets = []
        for seg in self.segments:
            mid_x = (seg["x_start"] + seg["x_end"]) / 2.0
            elev = seg["elevation_y"]

            # Filter points from cleaned_coordinates matching this platform segment
            matching = [
                p for p in self.all_coords
                if abs(p["y"] - elev) <= 15 and seg["x_start"] <= p["x"] <= seg["x_end"]
            ]
            if matching:
                # Pick the verified reachable point closest to platform center
                best_pt = min(matching, key=lambda p: abs(p["x"] - mid_x))
                tx = float(best_pt["x"])
                ty = float(best_pt["y"])
                source = "cleaned_coordinates"
            elif self.all_coords:
                # Fallback to closest verified reachable coordinate
                best_pt = min(self.all_coords, key=lambda p: (p["x"] - mid_x)**2 + (p["y"] - elev)**2)
                tx = float(best_pt["x"])
                ty = float(best_pt["y"])
                source = "cleaned_coordinates_nearest"
            else:
                tx = float(mid_x)
                ty = float(elev)
                source = "computed_midpoint"

            targets.append({
                "segment_id": seg["segment_id"],
                "x":          tx,
                "y":          ty,
                "x_start":    seg["x_start"],
                "x_end":      seg["x_end"],
                "span":       seg.get("span_width", 0),
                "source":     source,
            })
        return targets

    # Semantic alias
    targets = midpoints


CoordinateLoader = Level1CoordinateLoader


# ===========================================================================
# 2.  TEST RESULT LEDGER
# ===========================================================================

class TestLedger:
    """Persistent, JSON-serialisable record of every test case and its outcome."""

    def __init__(self, results_dir, run_id):
        self.results_dir = results_dir
        self.run_id      = run_id
        self.start_time  = datetime.now().isoformat()
        self.cases       = []
        os.makedirs(results_dir, exist_ok=True)

    def record(self, target_x, target_y, outcome, attempts, steps_used,
               deaths_during, final_pos, reason, selection_rationale,
               events_count=0, segment_id=None):
        case = {
            "case_id":             len(self.cases) + 1,
            "segment_id":          segment_id,
            "target":              {"x": target_x, "y": target_y},
            "outcome":             outcome,
            "attempts":            attempts,
            "steps_used":          steps_used,
            "deaths_during":       deaths_during,
            "final_pos":           {"x": final_pos[0], "y": final_pos[1]} if final_pos else None,
            "selection_rationale": selection_rationale,
            "failure_reason":      reason,
            "events_count":        events_count,
            "timestamp":           datetime.now().isoformat(),
        }
        self.cases.append(case)
        self._save()
        return case

    def outcomes_for(self, segment_id):
        return [c["outcome"] for c in self.cases if c.get("segment_id") == segment_id]

    def attempted_segments(self):
        return {c["segment_id"] for c in self.cases if c.get("segment_id") is not None}

    def successful_segments(self):
        return {c["segment_id"] for c in self.cases
                if c.get("segment_id") is not None and c["outcome"] == OUTCOME_SUCCESS}

    def failed_segments(self):
        fails = set()
        for c in self.cases:
            sid = c.get("segment_id")
            if sid is None or c["outcome"] == OUTCOME_SUCCESS:
                continue
            if len(self.outcomes_for(sid)) >= DEFAULT_MAX_ATTEMPTS:
                if all(o != OUTCOME_SUCCESS for o in self.outcomes_for(sid)):
                    fails.add(sid)
        return fails

    def attempts_for(self, segment_id):
        return sum(1 for c in self.cases if c.get("segment_id") == segment_id)

    def coverage_pct(self, total_segments):
        if total_segments == 0:
            return 0.0
        return round(len(self.successful_segments()) / total_segments * 100, 1)

    def summary(self):
        by_outcome = {}
        for c in self.cases:
            by_outcome[c["outcome"]] = by_outcome.get(c["outcome"], 0) + 1
        return {
            "run_id":              self.run_id,
            "start_time":          self.start_time,
            "end_time":            datetime.now().isoformat(),
            "total_cases":         len(self.cases),
            "outcomes":            by_outcome,
            "successful_segments": sorted(self.successful_segments()),
            "failed_segments":     sorted(self.failed_segments()),
        }

    def _save(self):
        path = os.path.join(self.results_dir, "{}.json".format(self.run_id))
        doc  = {"summary": self.summary(), "cases": self.cases}
        tmp  = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(doc, f, indent=2)
        if os.path.exists(path):
            os.remove(path)
        os.replace(tmp, path)
        return path

    def finalize(self):
        return self._save()


# ===========================================================================
# 3.  ADAPTIVE TARGET SELECTOR
# ===========================================================================

class TargetSelector:
    """
    Decides which target to test next and explains why.

    Strategies:
      coverage   - prefer untested segments, then least-visited, then elevated
      risk       - prefer high-elevation (small y) segments first
      systematic - strict left-to-right ordering by x_mid
    """

    PORTAL_X_THRESHOLD = 7200.0

    def __init__(self, midpoints, ledger, strategy="coverage"):
        self.midpoints = midpoints
        self.ledger    = ledger
        self.strategy  = strategy

    def select(self):
        """Return (midpoint_dict, rationale_string) or None when done."""
        candidates = self._filter_candidates()
        if not candidates:
            return None

        if self.strategy == "systematic":
            candidates.sort(key=lambda m: m["x"])
        elif self.strategy == "risk":
            candidates.sort(key=lambda m: m["y"])
        else:
            candidates.sort(key=lambda m: (
                self.ledger.attempts_for(m["segment_id"]),
                m["y"],
                -m["span"],
            ))

        chosen    = candidates[0]
        rationale = self._build_rationale(chosen, candidates)
        return chosen, rationale

    def _filter_candidates(self):
        result = []
        for m in self.midpoints:
            sid = m["segment_id"]
            if self.ledger.attempts_for(sid) >= DEFAULT_MAX_ATTEMPTS:
                continue
            if sid in self.ledger.successful_segments():
                continue
            result.append(m)
        return result

    def _build_rationale(self, chosen, candidates):
        sid      = chosen["segment_id"]
        attempts = self.ledger.attempts_for(sid)
        elev_lbl = "ground-level" if chosen["y"] >= GROUND_Y_THRESHOLD else "elevated"
        is_portal = chosen["x"] >= self.PORTAL_X_THRESHOLD

        parts = [
            "Selected segment {} at ({:.0f}, {:.0f})".format(sid, chosen["x"], chosen["y"]),
            "[{}, span={}px, src={}]".format(elev_lbl, chosen["span"], chosen.get("source", "cleaned_coordinates")),
            "strategy={}".format(self.strategy),
            "prior_attempts={}".format(attempts),
            "untested_remaining={}".format(len(candidates)),
        ]
        if is_portal:
            parts.append("near portal area - tests scene-transition boundary")
        if attempts > 0:
            prior = self.ledger.outcomes_for(sid)
            parts.append("previous_outcomes={} - retrying with fresh bot state".format(prior))
        if chosen["y"] < 300:
            parts.append("very high elevation - tests complex jump sequence reliability")
        elif chosen["y"] < 500:
            parts.append("mid-elevation platform - tests jump accuracy")
        else:
            parts.append("low/ground segment - verifies basic traversability")

        return " | ".join(parts)


# ===========================================================================
# 4.  OUTCOME EVALUATOR
# ===========================================================================

class OutcomeEvaluator:
    """Interprets telemetry collected during a navigation attempt."""

    def __init__(self, controller, tolerance):
        self.controller = controller
        self.tolerance  = tolerance

    def evaluate(self, target_x, target_y, runner, deaths_before, steps_limit):
        """Returns (outcome, reason, final_pos, deaths_during)."""
        state  = self.controller.get_latest_state()
        player = (state.get("player") or {}) if state else {}
        pos    = player.get("position", {}) or {}
        px     = float(pos.get("x", 0.0))
        py     = float(pos.get("y", 0.0))
        stats  = (state.get("stats") or {}) if state else {}
        deaths_after  = stats.get("deaths", 0)
        deaths_during = max(0, deaths_after - deaths_before)

        if runner.target_reached:
            return (OUTCOME_SUCCESS,
                    "Bot confirmed target reached within tolerance",
                    (px, py), deaths_during)

        dx    = abs(px - target_x)
        dy    = abs(py - target_y) if target_y is not None else 0.0
        on_fl = player.get("on_floor", False)
        y_ok  = (target_y is None) or (dy <= 80.0) or (on_fl and py <= target_y + 80.0)
        if dx <= self.tolerance and y_ok and player.get("alive", False):
            return (OUTCOME_SUCCESS,
                    "Player within tolerance of target (dx={:.0f}, dy={:.0f})".format(dx, dy),
                    (px, py), deaths_during)

        if deaths_during > 0:
            return (OUTCOME_DIED,
                    "Player died {}x during attempt; final pos=({:.0f},{:.0f})".format(
                        deaths_during, px, py),
                    (px, py), deaths_during)

        return (OUTCOME_STEP_BUDGET,
                "Step budget ({}) exhausted; closest=({:.0f},{:.0f}); dist_x={:.0f}".format(
                    steps_limit, px, py, dx),
                (px, py), deaths_during)


# ===========================================================================
# 5.  THE AGENTIC TESTING LOOP
# ===========================================================================

class AgenticTestingLoop:
    """
    Orchestrates: observe -> select -> execute -> evaluate -> record -> replan
    """

    def __init__(self, controller, coordinate_loader, ledger, selector, evaluator,
                 budget=DEFAULT_BUDGET, max_steps_per_target=DEFAULT_STEPS_PER_TARGET,
                 tolerance=DEFAULT_TOLERANCE, routes_file=None, verbose=True):
        self.controller  = controller
        self.loader      = coordinate_loader
        self.ledger      = ledger
        self.selector    = selector
        self.evaluator   = evaluator
        self.budget      = budget
        self.max_steps   = max_steps_per_target
        self.tolerance   = tolerance
        self.routes_file = routes_file
        self.verbose     = verbose
        self.test_idx    = 0

    # ---- helpers ----

    def _observe(self):
        state  = self.controller.get_latest_state()
        if not state:
            return None, 0, False
        stats  = state.get("stats") or {}
        player = state.get("player") or {}
        deaths = stats.get("deaths", 0)
        alive  = bool(player.get("alive", False)) and state.get("game_state") != "player_died"
        return state, deaths, alive

    def _ensure_level1(self, state=None):
        """Make sure the game is actively running in Level01; issue start_game/retry if needed."""
        for attempt in range(5):
            st = self.controller.get_latest_state()
            scene = (st or {}).get("scene", "")
            if "Level01" in scene:
                player = (st or {}).get("player") or {}
                if player.get("alive", False):
                    return True
                else:
                    print("[Loop] Player dead on spawn - issuing retry...", flush=True)
                    self.controller.retry()
                    time.sleep(1.5)
                    continue

            print("[Loop] Scene is '{}' (not Level01) - sending start_game command...".format(scene or "connecting"), flush=True)
            self.controller.start_game()
            time.sleep(2.0)

        st = self.controller.get_latest_state()
        return "Level01" in (st or {}).get("scene", "")

    def _build_runner(self, tx, ty):
        """
        Builds the dedicated HybridBotRunner / TargetCoordinateExplorer.
        Grounded in level_routes.json waypoints, kinematic guidance, and reactive recovery.
        """
        return HybridBotRunner(
            controller=self.controller,
            routes_file=self.routes_file,
            variation_mode=False,
            seed=42,
            max_steps=self.max_steps,
            target_level="Level01",
            target_coord=(tx, ty),
            coord_tolerance=self.tolerance,
        )

    def _divider(self, char="=", w=72):
        print(char * w, flush=True)

    def _print_outcome(self, case):
        sym = "OK" if case["outcome"] == OUTCOME_SUCCESS else "!!"
        print("[{}] OUTCOME: {}".format(sym, case["outcome"].upper()), flush=True)
        print("    Reason    : {}".format(case["failure_reason"]), flush=True)
        print("    Attempts  : {} | Steps : {} | Deaths : {}".format(
            case["attempts"], case["steps_used"], case["deaths_during"]), flush=True)
        if case["final_pos"]:
            fp = case["final_pos"]
            print("    Final pos : ({:.0f}, {:.0f})".format(fp["x"], fp["y"]), flush=True)

    # ---- main loop ----

    def run(self):
        total_segments = len(self.loader.midpoints())

        self._divider()
        print("  AGENTIC LEVEL-1 TESTING LOOP  -  Starting", flush=True)
        print("  Budget         : {} test cases".format(self.budget), flush=True)
        print("  Segments total : {}".format(total_segments), flush=True)
        print("  Strategy       : {}".format(self.selector.strategy), flush=True)
        print("  Steps/target   : {}".format(self.max_steps), flush=True)
        self._divider()

        # Wait for game state
        print("\n[Loop] Waiting for initial game state...", flush=True)
        t0 = time.time()
        while time.time() - t0 < 10.0:
            state, _, _ = self._observe()
            if state and state.get("scene"):
                break
            time.sleep(0.3)

        state, deaths_baseline, _ = self._observe()
        self._ensure_level1(state)
        state, deaths_baseline, _ = self._observe()

        for case_num in range(1, self.budget + 1):
            self.test_idx = case_num

            # ---- SELECT ----
            selection = self.selector.select()
            if selection is None:
                print("\n[Loop] All testable segments exhausted. Stopping after {} cases.".format(
                    case_num - 1), flush=True)
                break

            target, rationale = selection
            tx  = float(target["x"])
            ty  = float(target["y"])
            sid = target["segment_id"]

            self._divider()
            print("  TEST CASE {}/{}  -  Segment {} @ ({:.0f}, {:.0f})".format(
                case_num, self.budget, sid, tx, ty), flush=True)
            print("  Rationale: {}".format(rationale), flush=True)
            self._divider("-")

            # ---- ENSURE LEVEL01 ----
            state, deaths_before, _ = self._observe()
            self._ensure_level1(state)
            state, deaths_before, _ = self._observe()

            # ---- EXECUTE ----
            attempt_num = self.ledger.attempts_for(sid) + 1
            history_rec = ActionHistoryRecorder(
                mode="agentic_test_case_{}".format(case_num),
                metadata={"target_x": tx, "target_y": ty, "segment_id": sid},
            )
            runner = self._build_runner(tx, ty)

            event_id_before = self.controller.get_latest_event_id()
            print("\n[Loop] Executing navigation to ({:.0f}, {:.0f}) [attempt {}]...".format(
                tx, ty, attempt_num), flush=True)
            try:
                runner.navigate_to(
                    tx=tx,
                    ty=ty,
                    tolerance=self.tolerance,
                    max_steps=self.max_steps,
                    history_recorder=history_rec,
                    pause_on_reach=False,
                )
            except Exception as ex:
                print("[Loop] Navigation raised exception: {}".format(ex), flush=True)

            event_id_after = self.controller.get_latest_event_id()
            events_count   = max(0, event_id_after - event_id_before)

            # ---- EVALUATE ----
            outcome, reason, final_pos, deaths_during = self.evaluator.evaluate(
                target_x=tx,
                target_y=ty,
                runner=runner,
                deaths_before=deaths_before,
                steps_limit=self.max_steps,
            )

            # ---- RECORD ----
            case = self.ledger.record(
                target_x=tx,
                target_y=ty,
                outcome=outcome,
                attempts=attempt_num,
                steps_used=self.max_steps,
                deaths_during=deaths_during,
                final_pos=final_pos,
                reason=reason,
                selection_rationale=rationale,
                events_count=events_count,
                segment_id=sid,
            )
            self._print_outcome(case)

            # ---- REPLAN ANALYSIS ----
            self._replan_analysis(sid, outcome, target, final_pos)

            print("\n[Loop] Pausing 2s before next case...", flush=True)
            time.sleep(2.0)

            if outcome == OUTCOME_DIED:
                print("[Loop] Death detected - issuing retry...", flush=True)
                self.controller.retry()
                time.sleep(2.5)

        # ---- FINAL SUMMARY ----
        summary  = self.ledger.summary()
        out_path = self.ledger.finalize()
        cov      = self.ledger.coverage_pct(total_segments)

        self._divider()
        print("  AGENTIC TEST RUN COMPLETE", flush=True)
        self._divider("-")
        print("  Total test cases  : {}".format(summary["total_cases"]), flush=True)
        print("  Outcomes          : {}".format(summary["outcomes"]), flush=True)
        print("  Coverage          : {}% ({}/{} segments reached)".format(
            cov, len(self.ledger.successful_segments()), total_segments), flush=True)
        print("  Failed segments   : {}".format(sorted(self.ledger.failed_segments())), flush=True)
        print("  Results saved to  : {}".format(out_path), flush=True)
        self._divider()

        return summary

    def _replan_analysis(self, sid, outcome, target, final_pos):
        """Emit reasoning note about this outcome and what the next step should be."""
        tx, ty = target["x"], target["y"]
        attempts_so_far = self.ledger.attempts_for(sid)
        all_outcomes    = self.ledger.outcomes_for(sid)

        print("\n  [Replan Analysis]", flush=True)
        if outcome == OUTCOME_SUCCESS:
            print("  -> Segment {} confirmed traversable. Moving on to untested segments.".format(sid), flush=True)
        elif outcome == OUTCOME_DIED:
            if attempts_so_far < DEFAULT_MAX_ATTEMPTS:
                print("  -> Death during traversal to ({:.0f},{:.0f}). Enemy/fall hazard likely. "
                      "Will retry ({}/{}).".format(tx, ty, attempts_so_far, DEFAULT_MAX_ATTEMPTS), flush=True)
            else:
                print("  -> Segment {} failed {}x with deaths. Possible enemy chokepoint or gap. "
                      "Marking hard_fail.".format(sid, attempts_so_far), flush=True)
        elif outcome == OUTCOME_STEP_BUDGET:
            if final_pos:
                dist = math.hypot(final_pos[0] - tx, final_pos[1] - ty)
                if dist > 500:
                    print("  -> Bot very far from target ({:.0f}px). "
                          "May need route extension. Will retry.".format(dist), flush=True)
                else:
                    print("  -> Bot close ({:.0f}px) but ran out of steps. "
                          "Retry may succeed.".format(dist), flush=True)
        elif outcome == OUTCOME_STALL:
            print("  -> Bot stalled. Possible wall trap. Retry after level reset.", flush=True)

        if set(all_outcomes) == {OUTCOME_STEP_BUDGET} and attempts_so_far >= 2:
            print("  -> Consistently hitting step budget for segment {}. "
                  "Likely requires more steps or specialised jump sequence.".format(sid), flush=True)


# ===========================================================================
# 6.  ENTRY POINT / CLI
# ===========================================================================

def build_run_id():
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    h  = hashlib.md5(ts.encode()).hexdigest()[:6]
    return "agentic_{}_{}".format(ts, h)


def main():
    parser = argparse.ArgumentParser(
        description="Autonomous Agentic Game Testing Loop for 2D Platformers"
    )
    parser.add_argument("--budget", type=int, default=DEFAULT_BUDGET,
                        help="Number of test cases to run (default: {})".format(DEFAULT_BUDGET))
    parser.add_argument("--max-steps-per-target", type=int, default=DEFAULT_STEPS_PER_TARGET,
                        help="Bot step limit per target (default: {})".format(DEFAULT_STEPS_PER_TARGET))
    parser.add_argument("--tolerance", type=float, default=DEFAULT_TOLERANCE,
                        help="Target-reached tolerance in pixels (default: {})".format(DEFAULT_TOLERANCE))
    parser.add_argument("--port", type=int, default=4242,
                        help="UDP port to Godot game (default: 4242)")
    parser.add_argument("--routes", default="level_routes.json",
                        help="Path to level_routes.json (default: level_routes.json)")
    parser.add_argument("--mode", choices=["adaptive", "waypoints"], default="adaptive",
                        help="Execution mode: 'adaptive' agentic testing loop (default) or 'waypoints' runner")
    parser.add_argument("--strategy", choices=["coverage", "risk", "systematic"], default="coverage",
                        help="Target selection strategy (default: coverage)")
    parser.add_argument("--results-dir", default=DEFAULT_RESULTS_DIR,
                        help="Directory to save test results (default: {})".format(DEFAULT_RESULTS_DIR))
    parser.add_argument("--launch", action="store_true",
                        help="Auto-launch Godot game window before testing")
    parser.add_argument("--no-launch", action="store_true",
                        help="Do not auto-launch Godot window if not running")
    parser.add_argument("--verbose", action="store_true",
                        help="Verbose output")
    args = parser.parse_args()

    root_dir        = os.path.dirname(os.path.abspath(__file__))
    recordings_root = os.path.join(root_dir, SEGMENTS_GLOB)
    loader          = Level1CoordinateLoader(recordings_root)
    if not loader.segments:
        print("[ERROR] No platform segments loaded. Run level1_coordinate_recorder.py first.")
        sys.exit(1)

    # Clean up stale state files so fresh runtime state is read
    for st_path in [os.path.join(root_dir, "latest_state.json"), os.path.join(root_dir, "godot-4game", "latest_state.json")]:
        try:
            if os.path.exists(st_path):
                os.remove(st_path)
        except OSError:
            pass

    controller = GameController(port=args.port)
    godot_proc = None

    if args.launch:
        print("\n[INFO] Launching Godot game window...")
        godot_proc = launch_godot_game()
        time.sleep(2.0)
        connected = controller.connect(retries=30, retry_interval=0.5)
    else:
        # Check if game is already running
        connected = controller.connect(retries=3, retry_interval=0.3)
        if not connected and not args.no_launch:
            print("\n[INFO] Game window not detected. Auto-launching Godot platformer game...")
            godot_proc = launch_godot_game()
            time.sleep(2.0)
            print("[INFO] Connecting to game window over UDP...")
            connected = controller.connect(retries=30, retry_interval=0.5)

    if not connected:
        print("[WARNING] Game not responding to UDP handshake on port {}.".format(args.port))
        print("          Continuing with file-based / fallback telemetry...")

    run_id      = build_run_id()
    results_dir = os.path.join(root_dir, args.results_dir)
    ledger      = TestLedger(results_dir=results_dir, run_id=run_id)
    midpoints   = loader.midpoints()
    selector    = TargetSelector(midpoints=midpoints, ledger=ledger, strategy=args.strategy)
    evaluator   = OutcomeEvaluator(controller=controller, tolerance=args.tolerance)

    if args.mode == "waypoints":
        # Run dedicated SequentialWaypointsExplorer using verified cleaned coordinates
        target_pts = [(float(m["x"]), float(m["y"])) for m in midpoints[:args.budget]]
        print("\n[INFO] Running dedicated SequentialWaypointsExplorer on {} verified coordinates...".format(len(target_pts)), flush=True)
        wp_runner = SequentialWaypointsExplorer(
            controller=controller,
            waypoints=target_pts,
            routes_file=args.routes,
            tolerance=args.tolerance,
            wait_between=1.5,
            max_steps_per_point=args.max_steps_per_target,
            target_level="Level01",
        )
        try:
            success = wp_runner.run()
            summary = {"total_cases": len(target_pts), "outcomes": {"success" if success else "failed": len(target_pts)}}
        finally:
            controller.release_all()
            try:
                controller.sock.close()
            except OSError:
                pass
            if godot_proc and godot_proc.poll() is None:
                print("\n[INFO] Godot process remains open. Close the window when done.", flush=True)
    else:
        loop = AgenticTestingLoop(
            controller=controller,
            coordinate_loader=loader,
            ledger=ledger,
            selector=selector,
            evaluator=evaluator,
            budget=args.budget,
            max_steps_per_target=args.max_steps_per_target,
            tolerance=args.tolerance,
            routes_file=args.routes,
            verbose=args.verbose,
        )

        try:
            summary = loop.run()
        finally:
            controller.release_all()
            try:
                controller.sock.close()
            except OSError:
                pass
            if godot_proc and godot_proc.poll() is None:
                print("\n[INFO] Godot process remains open. Close the window when done.", flush=True)

    sys.exit(0 if summary.get("outcomes", {}).get(OUTCOME_SUCCESS, 0) > 0 or summary.get("outcomes", {}).get("success", 0) > 0 else 1)


if __name__ == "__main__":
    main()
