# 🎮 Syntax-Error: Autonomous AI Game Testing & Dual-Path QA Framework

> **An end-to-end autonomous Quality Assurance system for 2D platformers in Godot, powered by Reinforcement Learning navigation, high-frequency telemetry streaming, token-efficient schema compression, and Dual-Path AI bug triage (Deterministic Rules + Gemini White-Box Code Audit).**

---

## 📌 Motivation: Why We Built This Project

Testing a video game is **slow, repetitive, and expensive**. 

In conventional game QA, a human tester has to play every level over and over, attempt to reach every platform, and manually spot issues such as falling through the floor, scores calculating incorrectly, enemies failing to react, or exit portals that cannot be reached. Several fundamental obstacles make this nearly impossible to automate with traditional tools:

* **The Coverage Bottleneck**: Human testers cannot realistically replay an entire game in every permutation after every code commit or level design tweak.
* **Scripted Bots are Brittle**: Hardcoded input scripts (`press RIGHT for 2.0s, then JUMP`) immediately break the moment a platform moves, level geometry shifts, or physics parameters change. They only explore the exact paths someone anticipated.
* **Logs are Too Massive to Read**: A game engine processes physics at **60 Hz**, generating thousands of near-identical state lines in just a few minutes of play. A human cannot read through them, and piping raw JSON directly into an LLM exhausts token budgets in seconds while inviting parsing hallucinations.
* **Complex Logic Bugs Bypass Fixed Rules**: Simple rule checks (such as `y <= 1400`) only catch the narrow, predictable failures someone thought to write down. Emergent logic bugs—such as softlocks, enemies that get stuck and never reverse, collision phase-throughs at terminal velocity, or infinite jump exploits—require a deep contextual understanding of both the **design intent** and the underlying **source code contracts**.

---

## 🚀 What This Project Does

This framework automates the game tester's entire workflow **end to end**:

```
+----------------------------------------------------------------------------------------------------+
| 1. PLAY                                                                                            |
|    - Strategic AI Planner (Gemini) evaluates the map and sets target coordinate waypoints (X, Y).  |
|    - A trained RL / kinematic bot traverses to targets, jumping gaps and avoiding enemies.         |
|    - Godot's embedded GameLogger.gd logs every physics frame, input, and event to JSONL.           |
+----------------------------------------------------------------------------------------------------+
                                                  │
                                                  ▼
+----------------------------------------------------------------------------------------------------+
| 2. SIMPLIFY                                                                                        |
|    - The loader splits raw logs into isolated sessions and normalizes kinematics.                  |
|    - Separates continuous 60 FPS telemetry snapshots from discrete events (spawns, coins, deaths).|
|    - Thins snapshots via stride sampling (e.g., every 4th line = 75% reduction) to fit LLM budgets.|
|    - Discrete events and anomalies are NEVER dropped.                                              |
+----------------------------------------------------------------------------------------------------+
                                                  │
                                                  ▼
+----------------------------------------------------------------------------------------------------+
| 3. DETECT (Dual-Path QA Engine)                                                                    |
|    - Path 1 (Deterministic Invariants): Fast AST rule checks catch boundary breaches, speed spikes,|
|      and negative scores instantly with 0.95 confidence.                                           |
|    - Path 2 (Semantic / Gemini White-Box Audit): Slices logs into 5-second ReviewWindows. Gemini   |
|      cross-examines telemetry against actual GDScript code (Player.gd, Enemy.gd) to detect logic   |
|      flaws, checking for innocent explanations first to eliminate false alarms.                    |
+----------------------------------------------------------------------------------------------------+
                                                  │
                                                  ▼
+----------------------------------------------------------------------------------------------------+
| 4. REPORT                                                                                          |
|    - Correlated symptoms across frames are clustered into one root cause (60 falling frames = 1 bug|
|    - Ranks findings by severity (Critical, High, Medium, Low) and attaches exact evidence frames. |
|    - Generates human-readable Markdown (report.md) and machine-readable JSON (eval_results.json).   |
+----------------------------------------------------------------------------------------------------+
```

---

## 💡 What It Solves

* **Eliminates Manual Grind**: Cuts the repetitive manual effort of replaying levels to hunt for regressions.
* **Token-Efficient Ingestion**: Compresses raw telemetry into Schema v3 and samples snapshots, fitting deep multi-window gameplay into LLM context windows.
* **Catches Both Physical & Logic Flaws**: Unifies fast mathematical invariant checking with high-level code and design reasoning.
* **Attribution to Root Cause**: Points developers directly to the offending GDScript file, function, and line number instead of just logging a vague symptom.

---

## 🛠️ Batch Scripts Reference (`.bat`)

The repository includes modular batch scripts configured for different stages of the testing lifecycle:

| Batch Script | Function & Description |
|---|---|
| **`run_game.bat`** | Launches the **Godot 4** game client with active UDP socket (`:4242`) and `GameLogger.gd` telemetry enabled. Automatically detects local Godot 4 installations. |
| **`run_godot3_game.bat`** | Launches the legacy **Godot 3** engine platformer build for backward-compatibility testing. |
| **`edit_godot4_game.bat`** | Opens the Godot 4 project directly in the Godot Editor for level editing and scene configuration. |
| **`edit_godot3_game.bat`** | Opens the Godot 3 project in the editor. |
| **`run_agentic_test.bat`** | **Primary Autonomous Testing Harness**. Spawns the live telemetry monitor and runs `agentic_tester.py` in closed-loop mode (`Observe -> Target -> Navigate -> Evaluate -> Replan`). Supports `--strategy coverage`, `--strategy risk`, and custom budget flags. |
| **`run_explorer.bat`** | **Interactive Explorer Control Hub**. Presents an interactive menu to launch different testing modes: Hybrid Baseline, Controlled Variation, Random Fuzzing, Scripted Paths, or Specific Coordinates. |
| **`run_map3_bot.bat`** | Runs the hybrid bot specifically configured for **Map 3 (Sky Castle)**, steering through long-distance coordinates (`X=14638, Y=800`). |
| **`run_fault_injection.bat`** | Runs headless Godot unit and stress tests (`test_fault_injection.gd`) to simulate corrupt states, broken collisions, and physics anomalies. |
| **`record_level1_coordinates.bat`** | Runs a standalone coordinate profiler while a human plays, mapping safe, reachable platform coordinates to ground future AI waypoints. |
| **`run_recorder.bat`** | Launches manual gameplay recording for a specified level (e.g., `run_recorder.bat 2`) to capture human demonstration data for model training. |
| **`run_reader.bat`** | Spawns a real-time terminal monitor streaming active telemetry events (`log_reader.py`). |
| **`view_logs.bat`** | Launches a live, color-coded terminal visualizer (`view_structured_logs.py`) for formatted inspection of `game_events.jsonl`. |
| **`setup_and_run.bat`** | Initial setup script verifying Python dependencies, checking Godot executables, and bootstrapping the test environment. |
| **`Game_QA\run_eval.bat`** | **Dual-Path QA Evaluator**. Ingests recorded logs at stride 4, runs deterministic invariant checks, triggers Antigravity Gemini semantic review, and compiles `Game_QA/report.md`. |

---

## 📂 Repository Architecture

```
Syntax-error/
├── agentic_tester.py              # Closed-loop autonomous target planner & tester
├── bot_controller.py              # 5-tier reactive behavior state machine bot
├── explorer.py                    # Multi-mode exploration engine (UDP & Mailbox)
├── train_from_demonstration.py    # Trajectory training from recorded human gameplay
├── convert_game_events_to_schema.py # Token-efficient Schema v3 compressor
├── generate_coverage_report.py    # Schema event manifest coverage auditor
├── level_routes.json              # Navigational waypoint graph
├── game_events.jsonl              # Main runtime event log stream
├── latest_state.json              # Atomic real-time physics state snapshot
│
├── Game_QA/                       # Automated Dual-Path QA Subsystem
│   ├── run_eval.bat               # One-click evaluation batch script
│   ├── eval.py                    # Main evaluation orchestrator & deduplication
│   ├── checker.py                 # Path 1 deterministic invariant rule checker
│   ├── llm.py                     # Path 2 semantic evaluator & Gemini agent runner
│   ├── loader.py                  # Log parser, stride sampler, and kinematic flattener
│   ├── code_loader.py             # GDScript source parser & AST extractor
│   ├── schemas.py                 # Pydantic data models (Snapshot, Event, Finding)
│   ├── report.py                  # Markdown & JSON report formatter
│   ├── report.md                  # Generated visual QA audit report
│   ├── data/
│   │   └── checks.json            # Mathematical invariant definitions (bounds, speed, stats)
│   ├── prompts/                   # Prompt templates for Gemini (review_v1.md, judge_v1.md)
│   ├── tools/                     # Agent utilities (native_submit.py, inspect_windows.py)
│   └── results/                   # Evaluation artifacts (eval_results.json)
│
├── frontend/                      # Web Control Hub & Visual Bug Radar Dashboard
│   └── dashboard/
│       ├── start_dashboard.bat    # One-click web dashboard launcher
│       ├── server.py              # FastAPI backend API & process manager
│       ├── requirements.txt       # Dashboard dependencies (FastAPI, Uvicorn, psutil)
│       └── static/                # Single-page web interface (HTML, CSS, JS)
│
├── godot-4game/                   # Godot 4 2D Platformer Project
│   ├── project.godot              # Godot project manifest
│   └── src/
│       ├── Actors/ (Player, Enemy) # Kinematic character controllers
│       ├── Levels/ (Map1 to Map5)  # 2D platformer level scenes
│       └── Autoload/GameLogger.gd  # Global in-engine telemetry singleton
│
└── [Batch Execution Scripts]       # Modular runners for testing, recording, and debugging
```

---

## 📋 Prerequisites & Installation

Before running the project, ensure your environment meets these requirements and the necessary dependencies are installed.

### 1. System Requirements
* **Operating System**: Windows 10 or 11 (64-bit) (Scripts utilize Windows shell and PowerShell commands).
* **Python**: **Python 3.10+** (Python 3.11 recommended). Ensure Python and `pip` are added to your system `PATH`.
* **Standard Windows Tools**: `curl.exe` and `tar.exe` (built-in by default on modern Windows 10/11) — used by `setup_and_run.bat` to automatically download and extract Godot.
* **Game Engine**: **Godot Engine 4.3 Stable (Win64)**:
  * Automatically downloaded and installed into `engine\` when executing `setup_and_run.bat`.
  * Alternatively, place `Godot_v4.3-stable_win64.exe` inside an `engine\` folder manually.

---

### 2. Python Package Installation

Install all required dependencies across the entire repository with a single command:

```cmd
pip install pydantic>=2.5 simpleeval>=0.9.13 python-dotenv>=1.0 fastapi>=0.100.0 uvicorn>=0.20.0 websockets>=11.0 psutil>=5.9.0 requests>=2.28.0
```

#### Individual Component / Subsystem Commands:

* **To install WebSockets for real-time live terminal streaming:**
  ```cmd
  pip install websockets
  ```
* **To install all Web Dashboard dependencies (`frontend/dashboard/`):**
  ```cmd
  pip install -r frontend/dashboard/requirements.txt
  ```
* **To install all QA Engine dependencies (`Game_QA/`):**
  ```cmd
  pip install -r Game_QA/requirements.txt
  ```

#### Dependencies Breakdown by Subsystem:

| Subsystem | Required Packages | Purpose |
|---|---|---|
| **Core Bot & Explorer**<br>`(bot_controller.py, explorer.py)` | *None (Standard Library)* | Zero external dependencies! Relies exclusively on built-in Python modules (`socket`, `json`, `math`, `time`). |
| **QA Engine**<br>`(Game_QA/requirements.txt)` | `pydantic>=2.5`<br>`simpleeval>=0.9.13`<br>`python-dotenv>=1.0` | Invariant evaluation, schema data models, AST rule parsing, and environment variables. |
| **Web Dashboard**<br>`(frontend/dashboard/requirements.txt)` | `fastapi>=0.100.0`<br>`uvicorn>=0.20.0`<br>`websockets>=11.0`<br>`psutil>=5.9.0`<br>`requests>=2.28.0` | Asynchronous REST backend, Uvicorn ASGI server, real-time live terminal streaming (`/ws/logs`), and process/memory monitoring. |
| **Optional LLM SDKs**<br>*(If not using Antigravity Agent)* | `anthropic>=0.30`<br>`openai>=1.30`<br>`google-generativeai` | Optional if calling external cloud LLM APIs directly for Path 2 review. |

---

## ⚡ Quickstart Guide

### 1. Initial Setup & Engine Bootstrap (First-Time Run)
Before running tests, execute `setup_and_run.bat`. This universal launcher automatically verifies your environment, downloads Godot 4.3 stable into `engine\` if missing, pre-imports game textures/assets, and bootstraps the environment:
```cmd
setup_and_run.bat
```

### 2. Launch Autonomous Closed-Loop Testing (Generates Raw Logs)
Run the agentic test harness to have Gemini select spatial target waypoints and the trained kinematic bot navigate the level. This autonomous session generates the raw telemetry stream directly in `game_events.jsonl`:
```cmd
run_agentic_test.bat --budget 20 --strategy coverage
```
*(Alternatively, you can launch interactive testing modes with `run_explorer.bat`)*

### 3. Run the Dual-Path QA Audit on Raw Logs
Navigate to the `Game_QA` directory and launch the evaluation pipeline:
```cmd
cd Game_QA
run_eval.bat
```
*(Or invoke `eval.py` directly with custom sampling stride: `python eval.py --stride 4`)*

#### 🔍 What Happens Under the Hood:
1. **Raw Log Resolution**: `loader.py` automatically resolves the raw `game_events.jsonl` from the parent directory.
2. **In-Memory Simplification & Sampling**: The loader thins continuous 60 FPS snapshots (using `stride=4`, a ~75% reduction) while preserving **100% of discrete events and anomalies**.
3. **Temporal Slicing**: Slices the simplified session into 5-second `ReviewWindow` objects.
4. **Context Loading & LLM Query**: `code_loader.py` loads the active GDScript files (`Player.gd`, `Enemy.gd`, etc.), formats the payload using `prompts/review_v1.md`, and passes the temporal windows to **Gemini** for white-box contract reasoning.
5. **Deduplication & Reporting**: Clustered findings are saved to `results/eval_results.json` and rendered into the Markdown report.

### 4. Review Detected Bugs & Root Causes
Open **`Game_QA/report.md`** to inspect the detected bugs, categorized by severity (🔴 Critical, 🟠 High, 🟡 Medium), alongside exact evidence frame numbers and suspected GDScript files.

### 5. (Optional) Launch the Visual Web Dashboard
For an interactive, browser-based control hub with real-time KPI scorecards, interactive bug radar, map selector, and agent controls:
```cmd
frontend\dashboard\start_dashboard.bat
```
This starts the dashboard server and opens your browser at `http://localhost:8080`.

---

### 🔧 Useful Game_QA CLI Utilities

| Command | Action |
|---|---|
| `python eval.py --stride 4` | Runs full evaluation on raw logs using 4-frame snapshot sampling. |
| `python tools/inspect_windows.py` | Slices the raw session into 5-second time windows and prints frame boundaries. |
| `python tools/map_windows.py` | Maps specific anomaly frames (e.g. frame `337`) to their parent `ReviewWindow` ID. |
| `python tools/native_submit.py --session <SID> --window <WID> --findings <file.json>` | Validates and submits agent findings into the pipeline's cache. |
| `python report.py` | Recompiles and updates `report.md` from `results/eval_results.json`. |
