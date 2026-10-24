---
name: agentic-platformer-test
description: >
  Runs the closed-loop agentic testing workflow for 2D platformers.
  The skill selects test targets from verified reachable coordinates (cleaned_coordinates.json),
  navigates the bot to each target using the existing HybridBotRunner, evaluates
  the outcome, records evidence, and replans based on what it has learned.
  Use this skill when asked to: run automated tests, check coverage, find
  unreachable areas, or investigate traversal failures.
---

# Agentic Testing Skill

## What this skill does

Executes the `agentic_tester.py` script, which implements a
**observe → select → execute → evaluate → record → replan** loop against the
live Godot platformer game.

## Prerequisites

1. Godot platformer engine (auto-launches game window by default).
2. `level_routes.json` at the project root for waypoint navigation routes.
3. Verified reachable coordinates in `recordings/level1_coordinates/*/cleaned_coordinates.json`.

## Invocation

```
python agentic_tester.py [OPTIONS]
```

| Option | Default | Description |
|--------|---------|-------------|
| `--budget N` | 20 | Number of test cases to run |
| `--mode` | adaptive | `adaptive` (agentic loop) or `waypoints` (dedicated sequential runner) |
| `--max-steps-per-target N` | 350 | Bot step limit per target |
| `--tolerance PX` | 70 | Target-reached tolerance in pixels |
| `--strategy` | coverage | `coverage` / `risk` / `systematic` |
| `--results-dir DIR` | agentic_test_results | Where to save JSON results |
| `--port N` | 4242 | UDP port to Godot game |
| `--launch` | auto | Auto-launch Godot game window (default: on) |
| `--no-launch` | off | Disable auto-launch if connecting to existing window |
| `--verbose` | off | Extra console output |

### Quick launch

```bat
:: Default: automatically pops up Godot game window and runs 20 verified platform tests
run_agentic_test.bat

:: Prioritize high-elevation / high-risk platforms
run_agentic_test.bat --budget 10 --strategy risk

:: Run dedicated sequential waypoint bot through 5 verified targets
run_agentic_test.bat --mode waypoints --budget 5
```

## How target selection works

Targets are **grounded in verified reachable positions** by loading
`cleaned_coordinates.json`. For each platform segment, `TargetSelector.select()`
selects the closest verified player coordinate to ensure test targets reflect
actual reachable positions.

It removes already-confirmed segments and those exceeding the retry limit,
then sorts the remaining candidates by:

- **coverage** (default): fewest prior attempts → highest elevation → widest span
- **risk**: lowest y-value (highest-elevation) first
- **systematic**: left-to-right by X coordinate

It returns the best candidate **and a human-readable rationale string**
explaining why it was chosen.

## How outcome evaluation works

`OutcomeEvaluator.evaluate()` applies these deterministic rules:

| Rule | Outcome |
|------|---------|
| `runner.target_reached == True` | `success` |
| Player within tolerance + alive | `success` |
| `deaths_during > 0` | `died` |
| Step budget exhausted | `step_budget` |

After each case, `_replan_analysis()` emits a reasoning note explaining
the failure and what the next iteration should do.

## Where results are stored

Each run produces a JSON file at:

```
agentic_test_results/<run_id>.json
```

containing:
- **summary**: outcomes breakdown, coverage %, successful/failed segments
- **cases**: full record per test case (target, outcome, attempts, final pos,
  selection rationale, failure reason, event count)

## Stopping conditions

The loop stops when:
- The test budget (`--budget`) is exhausted.
- All platform segments are either confirmed or exceeded `DEFAULT_MAX_ATTEMPTS`.
- The user presses Ctrl+C.

## Architecture

```
CoordinateLoader         reads cleaned_coordinates.json & traversable_segments.json
        |
        v
TargetSelector           selects next verified target + rationale  (AI reasoning)
        |
        v
AgenticTestingLoop       observe -> execute (HybridBotRunner) -> evaluate -> record -> replan
        |
        v
TestLedger               persists results to JSON
```

## Key files

| File | Role |
|------|------|
| `agentic_tester.py` | Agentic loop implementation |
| `bot_controller.py` | HybridBotRunner, LevelRouteManager (unchanged) |
| `explorer.py` | GameController, ActionHistoryRecorder (unchanged) |
| `level_routes.json` | Waypoint routes used by HybridBotRunner (unchanged) |
| `recordings/level1_coordinates/*/cleaned_coordinates.json` | Ground-truth reachable coordinates |
| `recordings/level1_coordinates/*/traversable_segments.json` | Platform segment coordinate data |
| `agentic_test_results/*.json` | Test run results |

## Limitations and next steps

1. **No multi-attempt mid-target retry**: if the bot dies mid-run the whole
   attempt is counted; a future version could resume from the last known
   good position.
2. **Ground segments are low-value**: consider filtering `y >= 750` out of
   the coverage budget and testing them in a fast preliminary sweep.
3. **No cross-run persistence**: ledger is per-run; a future version could
   load prior results to avoid re-testing already-confirmed segments.
4. **Enemy patrol timing**: stomp success depends on patrol phase at time of
   arrival; repeated `step_budget` failures on enemy-guarded segments may
   indicate timing sensitivity.
