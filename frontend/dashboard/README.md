# 🎮 Syntax-Error // QA Explorer Dashboard

A modern, polished, responsive full-stack control dashboard for the **Syntax-Error** AI game testing and autonomous exploration platform.

---

## 🚀 Quick Start (One-Click Launcher)

To launch the dashboard, double-click:
```bat
frontend\dashboard\start_dashboard.bat
```
This automatically verifies dependencies, starts the FastAPI server on port `8080`, and opens your default browser at `http://localhost:8080`.

Alternatively, run from terminal:
```bash
cd frontend/dashboard
python server.py --port 8080 --open
```

---

## 🌟 Key Features & Workflows

### 1. Dashboard Overview & Bug Radar
- **Discovered Bugs & Findings**: Real results parsed from `Game_QA/results/eval_results.json` and `Game_QA/results/agent_notes/*findings*.json`.
- **Master Answer Key Verification**: Matches findings against the 11 documented intentional benchmark bugs across Maps 1 through 4 (from `maps/ANSWER_KEY.md`).
- **Telemetry & Session KPIs**: Real-time counter of critical/high bugs, deterministic (Path 1) vs LLM semantic (Path 2) detections, recorded agentic runs, and logged events.
- **Detailed Finding Inspector**: Inspect suspected GDScript code, evidence frames, severity, confidence, and white-box audit notes.

### 2. Run Game & Custom Map Selector
- **5 Selectable Maps**:
  - **Default Map: Original Game Campaign** (`MainScreen.tscn` / `Level01.tscn`, Map 0) — Standard campaign that launches by default when executing `run_game`.
  - **Map 1: Green Hills** (`Map1_GreenHills.tscn`, 3 benchmark bugs)
  - **Map 2: Underground Caves** (`Map2_UndergroundCaves.tscn`, 2 benchmark bugs)
  - **Map 3: Sky Castle** (`Map3_SkyCastle.tscn`, 3 benchmark bugs)
  - **Map 4: Lava Fortress** (`Map4_LavaFortress.tscn`, 3 benchmark bugs)
- **Map Binding**: Selecting any map in the header or map grid binds that map directly to the launcher (running `run_game.bat` for the default map, or `run_map.py --map <N>` for Maps 1–4).
- **Launch Configurations**: Windowed (GUI), Headless (CI), or Debug mode with verbose logging.
- **Hybrid Bot Traversal**: Optional auto-navigation on the chosen map.

### 3. Agent Explorer (`agentic_tester.py`)
- **One-Click Autonomous Closed-Loop Testing Loop**: `observe -> select target -> navigate -> evaluate -> record -> replan`.
- **Target Grounding**: Uses 1,290 verified reachable coordinates from Level 1 coordinate meshes.
- **Exploration Strategies**:
  - `coverage`: Maximise spatial coverage of unique platform segments.
  - `risk`: Prioritise elevated and hard-to-reach segments.
  - `systematic`: Left-to-right sweep of recorded reachable platform points.
- **Controls**: Test budget, max steps per target, tolerance, auto-launch window, and verbose flags.

### 4. Normal Explorer Control Hub (`explorer.py`)
- **Exposes all terminal exploration modes**:
  - `[1] Hybrid Bot Baseline Mode`
  - `[2] Hybrid Bot Controlled Variation Mode` (with seed)
  - `[3] Target Coordinate Explorer` (with custom X, Y)
  - `[W2] Sequential Waypoints Mode`
  - `[W1] Interactive Waypoints Mode`
  - `[4] Scripted Replay Mode` (selects paths from `paths/*.json`)
  - `[6] Random Exploration Mode`
  - `[7] Coverage-Guided Exploration Mode`
  - `[8] Run Explorer & Bot Test Suite`
- **Dynamic Waypoint Configuration (W1 & W2)**:
  - Dynamically configured within this workflow (not a separate top-level explorer).
  - Waypoint count indicator.
  - Dynamic table to add, remove, and edit (X, Y) pixel coordinates.
  - Quick-load presets: *Level 1 Intro*, *Full Level 1 Route*, *Sky Castle Stairs*, *Bug Hunt Points*.
  - Configurable wait time at each waypoint (`--waypoint-wait`, default 3s).
  - Coordinate arrival tolerance radius (`--tolerance`, default 60px).

### 5. Execution Monitoring & Live Terminal
- **Process Status**: Displays real-time PID, status (Running / Idle / Succeeded / Terminated), and elapsed time.
- **Live Terminal**: Streams `stdout` and `stderr` in real-time via WebSockets or polling with ANSI highlighting for `[OK]`, `[ERROR]`, `[NAVIGATE]`, `[BUGTRIGGER]`, etc.
- **Stop Process**: Cleanly stops running processes and any child processes using `taskkill /F /T`.
- **Run QA Audit**: One-click execution of `Game_QA/eval.py` to re-score telemetry and update findings.

---

## 📁 Directory Structure

```
frontend/dashboard/
├── server.py              # FastAPI server & process execution manager
├── requirements.txt       # Dependencies (fastapi, uvicorn, psutil)
├── start_dashboard.bat    # One-click Windows batch launcher
├── README.md              # Documentation
└── static/
    ├── index.html         # Main single-page dashboard UI
    ├── css/
    │   └── dashboard.css  # Modern dark cyber theme styles
    └── js/
        ├── dashboard.js   # Application logic, tabs, API dispatchers
        └── terminal.js    # Terminal stream renderer with ANSI parsing
```

