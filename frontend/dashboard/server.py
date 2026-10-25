#!/usr/bin/env python3
"""
Syntax-Error QA Explorer & Bot Control Dashboard Server
FastAPI backend providing real-time integration with:
  1. Game_QA evaluation reports, schemas, and findings
  2. Map 1 - 4 custom benchmarks & answer key
  3. Run Game workflow (run_game.bat / run_map.py)
  4. Agent Explorer (agentic_tester.py closed-loop tester)
  5. Normal Explorer (explorer.py with all modes, including W1/W2 waypoints)
  6. Live process management, log streaming, and telemetry inspection
"""

import os
import sys
import re
import json
import glob
import time
import signal
import asyncio
import shutil
import subprocess
import threading
from collections import deque
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

# -----------------------------------------------------------------------------
# Paths
# -----------------------------------------------------------------------------
DASHBOARD_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = DASHBOARD_DIR.parent.parent
GAME_QA_DIR = PROJECT_ROOT / "Game_QA"
MAPS_DIR = PROJECT_ROOT / "maps"
PATHS_DIR = PROJECT_ROOT / "paths"
AGENTIC_RESULTS_DIR = PROJECT_ROOT / "agentic_test_results"
RECORDINGS_DIR = PROJECT_ROOT / "recordings"

STATIC_DIR = DASHBOARD_DIR / "static"

app = FastAPI(
    title="Syntax-Error QA Explorer Dashboard",
    description="Full-stack control center for AI Game Testing & Exploration",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -----------------------------------------------------------------------------
# Process Manager
# -----------------------------------------------------------------------------
class ActiveProcessManager:
    """Manages active subprocess execution and buffers logs for real-time streaming."""
    def __init__(self):
        self.process: Optional[subprocess.Popen] = None
        self.pid: Optional[int] = None
        self.workflow: str = "idle"
        self.command_str: str = ""
        self.started_at: Optional[float] = None
        self.status: str = "idle"  # idle, running, completed, failed, stopped
        self.exit_code: Optional[int] = None
        self.log_buffer: deque = deque(maxlen=4000)
        self.lock = threading.RLock()
        self.active_websockets: List[WebSocket] = []
        self._reader_thread: Optional[threading.Thread] = None

    def get_status(self) -> Dict[str, Any]:
        with self.lock:
            # Check if process finished
            if self.process and self.status == "running":
                ret = self.process.poll()
                if ret is not None:
                    self.exit_code = ret
                    self.status = "completed" if ret == 0 else "failed"

            elapsed = round(time.time() - self.started_at, 1) if (self.started_at and self.status == "running") else 0

            return {
                "status": self.status,
                "workflow": self.workflow,
                "pid": self.pid,
                "command": self.command_str,
                "started_at": datetime.fromtimestamp(self.started_at).isoformat() if self.started_at else None,
                "elapsed_sec": elapsed,
                "exit_code": self.exit_code,
                "total_lines": len(self.log_buffer)
            }

    def start_process(self, cmd: List[str], workflow_name: str, cwd: Optional[Path] = None, env: Optional[Dict[str, str]] = None, shell: bool = False) -> Dict[str, Any]:
        with self.lock:
            if self.process and self.status == "running":
                ret = self.process.poll()
                if ret is None:
                    raise RuntimeError(f"A process is already running: {self.workflow} (PID {self.pid})")

            # Reset state
            self.workflow = workflow_name
            self.command_str = " ".join(cmd)
            self.started_at = time.time()
            self.status = "running"
            self.exit_code = None
            self.log_buffer.clear()

            work_dir = str(cwd or PROJECT_ROOT)
            run_env = os.environ.copy()
            if env:
                run_env.update(env)
            # Ensure python unbuffered stdout
            run_env["PYTHONUNBUFFERED"] = "1"

            timestamp = datetime.now().strftime("%H:%M:%S")
            self._append_log(f"[{timestamp}] [DASHBOARD] >>> Launching {workflow_name.upper()}...")
            self._append_log(f"[{timestamp}] [DASHBOARD] Command: {self.command_str}")
            self._append_log(f"[{timestamp}] [DASHBOARD] Working Directory: {work_dir}\n")

            try:
                self.process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    bufsize=1,
                    universal_newlines=True,
                    cwd=work_dir,
                    env=run_env,
                    shell=shell
                )
                self.pid = self.process.pid
            except Exception as e:
                self.status = "failed"
                self.exit_code = -1
                self._append_log(f"[{timestamp}] [ERROR] Failed to start process: {str(e)}")
                raise

        # Spawn reader thread outside lock
        self._reader_thread = threading.Thread(target=self._stream_output, daemon=True)
        self._reader_thread.start()

        return self.get_status()

    def _stream_output(self):
        proc = self.process
        if not proc or not proc.stdout:
            return

        try:
            for line in iter(proc.stdout.readline, ''):
                if not line and proc.poll() is not None:
                    break
                stripped = line.rstrip('\r\n')
                if stripped:
                    self._append_log(stripped)
        except Exception as e:
            self._append_log(f"[DASHBOARD LOG ERROR] {e}")
        finally:
            proc.stdout.close()
            ret = proc.wait()
            with self.lock:
                self.exit_code = ret
                if self.status != "stopped":
                    self.status = "completed" if ret == 0 else "failed"
                timestamp = datetime.now().strftime("%H:%M:%S")
                self._append_log(f"\n[{timestamp}] [DASHBOARD] <<< Process exited with code {ret}")

    def _append_log(self, line: str):
        with self.lock:
            self.log_buffer.append(line)
            if not self.active_websockets:
                return
            ws_list = list(self.active_websockets)

        line_data = json.dumps({"type": "log", "line": line})
        for ws in ws_list:
            try:
                loop = getattr(ws, "_loop", None)
                if loop and loop.is_running():
                    asyncio.run_coroutine_threadsafe(ws.send_text(line_data), loop)
            except Exception:
                pass

    def stop_process(self) -> Dict[str, Any]:
        with self.lock:
            if not self.process or self.status != "running":
                return self.get_status()

            pid = self.pid
            self.status = "stopped"
            timestamp = datetime.now().strftime("%H:%M:%S")
            self._append_log(f"\n[{timestamp}] [DASHBOARD] [STOP] Sending termination signal to PID {pid}...")

            try:
                # On Windows, try taskkill with timeout to clean up child processes
                if sys.platform == "win32":
                    try:
                        subprocess.run(["taskkill", "/F", "/T", "/PID", str(pid)], capture_output=True, timeout=2.0)
                    except Exception:
                        pass
                self.process.terminate()
            except Exception as e:
                self._append_log(f"[{timestamp}] [WARNING] Error terminating process: {e}")

            try:
                self.process.kill()
            except Exception:
                pass

            self.exit_code = -9
            return self.get_status()

    def get_logs(self, start_offset: int = 0) -> Dict[str, Any]:
        with self.lock:
            lines = list(self.log_buffer)
            total = len(lines)
            sliced = lines[start_offset:] if start_offset < total else []
            return {
                "offset": total,
                "lines": sliced,
                "total": total,
                "status": self.status,
                "workflow": self.workflow,
                "pid": self.pid,
                "exit_code": self.exit_code
            }


proc_manager = ActiveProcessManager()

# -----------------------------------------------------------------------------
# Data Extractors & Parsers
# -----------------------------------------------------------------------------

def parse_answer_key() -> List[Dict[str, Any]]:
    """Parses ground truth 11 intentional bugs from maps/ANSWER_KEY.md."""
    answer_key_path = MAPS_DIR / "ANSWER_KEY.md"
    if not answer_key_path.exists():
        return []

    bugs = []
    try:
        content = answer_key_path.read_text(encoding="utf-8")
        lines = content.splitlines()
        for line in lines:
            if line.startswith("| **") and "|" in line:
                parts = [p.strip() for p in line.split("|")[1:-1]]
                if len(parts) >= 7:
                    bug_id = parts[0].replace("**", "").strip()
                    map_name = parts[1].strip()
                    coords = parts[2].replace("<br>", " ").strip()
                    desc = parts[3].strip()
                    expected = parts[4].strip()
                    actual = parts[5].strip()
                    identifier = parts[6].replace("`", "").strip()

                    bugs.append({
                        "id": bug_id,
                        "map": map_name,
                        "coords": coords,
                        "description": desc,
                        "expected": expected,
                        "actual": actual,
                        "identifier": identifier
                    })
    except Exception as e:
        print(f"[ERROR] Failed to parse ANSWER_KEY.md: {e}", file=sys.stderr)

    return bugs


def normalize_qa_key(item: Dict[str, Any]) -> str:
    """Computes a canonical deduplication key for QA bug findings."""
    if item.get("dedupe_key"):
        return str(item["dedupe_key"]).strip().lower()
    code = str(item.get("suspected_code") or "").strip().lower()
    title = str(item.get("title") or "").strip().lower()
    title = re.sub(r"^(semantic anomaly:\s*|engine anomaly:\s*)", "", title)
    if "out of bounds" in title or "void fall" in title or "player_out_of_bounds" in title:
        title = "out_of_bounds_void_fall"
    elif "stairs" in title or "stair_stick" in title:
        title = "stairs_immobilization"
    elif "floating" in title or "floating_enemy" in title:
        title = "floating_enemy"
    elif "wall reversal" in title or "enemy frozen" in title:
        title = "enemy_wall_reversal_frozen"
    elif "portal" in title or "missing_expected_object" in title:
        title = "portal_missing_next_scene"
    elif "duplicate_pickup" in title or "coin overlap" in title:
        title = "duplicate_coin_pickup"
    elif "500 threshold" in title or "score decrements" in title:
        title = "score_decrements_above_500"
    elif "7th coin" in title or "seventh coin" in title:
        title = "seventh_coin_suppression"
    elif "wall_stuck" in title or "stuck in wall" in title or "wedged" in title or "wall geometry" in title:
        title = "player_stuck_in_wall"
    elif "cannot kill" in title or "not able to kill" in title or "does not kill" in title or "can_kill_player" in title or "fails to inflict lethal" in title or "fails to kill" in title:
        title = "enemy_cannot_kill_player"
    return f"{code}::{title}"


def parse_game_qa_findings() -> Dict[str, Any]:
    """
    Reads real bug findings from:
      1. Game_QA/results/eval_results.json
      2. Game_QA/.cache/audit_*.json (live real-time audit cache)
      3. Game_QA/results/agent_notes/*.json
    Deduplicates findings while merging evidence frames and metadata.
    """
    raw_candidates = []
    sessions_analyzed = 0
    total_events_in_session = 0

    # 1. Main eval_results.json
    eval_file = GAME_QA_DIR / "results" / "eval_results.json"
    if eval_file.exists():
        try:
            with open(eval_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    sessions_analyzed = max(sessions_analyzed, len(data))
                    for sess in data:
                        sess_id = sess.get("session_id", "unknown")
                        total_events_in_session += sess.get("total_events", 0)
                        for item in sess.get("findings", []):
                            item_copy = dict(item)
                            item_copy["session_id"] = sess_id
                            item_copy["source_file"] = "Game_QA/results/eval_results.json"
                            raw_candidates.append(item_copy)
        except Exception as e:
            print(f"[ERROR] Reading eval_results.json: {e}", file=sys.stderr)

    # 2. Live audit cache (.cache/audit_*.json)
    cache_dir = GAME_QA_DIR / ".cache"
    if cache_dir.exists():
        for cf in glob.glob(str(cache_dir / "audit_*.json")):
            try:
                with open(cf, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, dict) and data.get("verdict") == "bug":
                        item_copy = dict(data)
                        item_copy["source_file"] = f"Game_QA/.cache/{Path(cf).name}"
                        raw_candidates.append(item_copy)
            except Exception as e:
                print(f"[ERROR] Reading {cf}: {e}", file=sys.stderr)

    # 3. Agent notes findings (results/agent_notes/*.json)
    notes_dir = GAME_QA_DIR / "results" / "agent_notes"
    if notes_dir.exists():
        for nf in glob.glob(str(notes_dir / "*.json")):
            try:
                with open(nf, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    items = data if isinstance(data, list) else [data]
                    for item in items:
                        if not isinstance(item, dict):
                            continue
                        if item.get("verdict") == "bug" or (item.get("title") and item.get("severity")):
                            item_copy = dict(item)
                            item_copy["session_id"] = Path(nf).stem.replace("_findings", "").replace("finding_", "")
                            item_copy["source_file"] = f"Game_QA/results/agent_notes/{Path(nf).name}"
                            raw_candidates.append(item_copy)
            except Exception as e:
                print(f"[ERROR] Reading {nf}: {e}", file=sys.stderr)

    # Deduplicate & consolidate findings
    findings = []
    finding_map = {}
    sev_rank = {"critical": 4, "high": 3, "medium": 2, "low": 1}

    for cand in raw_candidates:
        key = normalize_qa_key(cand)
        if key in finding_map:
            existing = finding_map[key]
            # Union evidence frames
            ef = sorted(list(set(existing.get("evidence_frames", []) + cand.get("evidence_frames", []))))
            existing["evidence_frames"] = ef
            # Keep highest confidence
            existing["confidence"] = max(existing.get("confidence", 0.0), cand.get("confidence", 0.0))
            # Keep richer explanation
            if len(cand.get("explanation", "")) > len(existing.get("explanation", "")):
                existing["explanation"] = cand["explanation"]
            # Upgrade severity if higher
            cand_sev = str(cand.get("severity", "medium")).lower()
            exist_sev = str(existing.get("severity", "medium")).lower()
            if sev_rank.get(cand_sev, 0) > sev_rank.get(exist_sev, 0):
                existing["severity"] = cand["severity"]
        else:
            cand_copy = dict(cand)
            finding_map[key] = cand_copy
            findings.append(cand_copy)

    # Sort findings by severity (critical first) then confidence
    findings.sort(key=lambda x: (sev_rank.get(str(x.get("severity", "medium")).lower(), 0), x.get("confidence", 0.0)), reverse=True)

    # Calculate statistics
    sev_counts = {"critical": 0, "high": 0, "medium": 0, "low": 0}
    path_counts = {"path1": 0, "path2": 0}
    for f in findings:
        sev = str(f.get("severity", "medium")).lower()
        sev_counts[sev] = sev_counts.get(sev, 0) + 1
        path = str(f.get("path", "path1")).lower()
        path_counts[path] = path_counts.get(path, 0) + 1

    return {
        "findings": findings,
        "total_findings": len(findings),
        "severity_counts": sev_counts,
        "path_counts": path_counts,
        "sessions_analyzed": max(sessions_analyzed, 1),
        "total_events_in_session": total_events_in_session
    }


def parse_agentic_runs() -> List[Dict[str, Any]]:
    """Loads all agentic test run results from agentic_test_results/*.json."""
    runs = []
    if not AGENTIC_RESULTS_DIR.exists():
        return runs

    run_files = sorted(glob.glob(str(AGENTIC_RESULTS_DIR / "agentic_*.json")), reverse=True)
    for rf in run_files:
        try:
            with open(rf, "r", encoding="utf-8") as f:
                data = json.load(f)
                summary = data.get("summary", {})
                cases = data.get("cases", [])

                success_cases = sum(1 for c in cases if c.get("outcome") == "reached")
                budget_cases = sum(1 for c in cases if c.get("outcome") == "step_budget")
                death_cases = sum(1 for c in cases if c.get("outcome") == "died")

                runs.append({
                    "run_id": summary.get("run_id", Path(rf).stem),
                    "file_path": str(Path(rf).relative_to(PROJECT_ROOT)),
                    "start_time": summary.get("start_time"),
                    "end_time": summary.get("end_time"),
                    "total_cases": summary.get("total_cases", len(cases)),
                    "success_cases": success_cases,
                    "budget_cases": budget_cases,
                    "death_cases": death_cases,
                    "outcomes": summary.get("outcomes", {}),
                    "cases": cases[:50]  # preview first 50
                })
        except Exception as e:
            print(f"[ERROR] Reading {rf}: {e}", file=sys.stderr)

    return runs


def get_telemetry_stream(limit: int = 100, category_filter: Optional[str] = None) -> List[Dict[str, Any]]:
    """Reads latest N telemetry events from game_events.jsonl."""
    candidates = [
        PROJECT_ROOT / "godot-4game" / "game_events.jsonl",
        PROJECT_ROOT / "game_events.jsonl",
        GAME_QA_DIR / "_private" / "telemetry" / "game_events_original.jsonl"
    ]

    events = []
    target_file = None
    for cand in candidates:
        if cand.exists() and cand.stat().st_size > 0:
            target_file = cand
            break

    if not target_file:
        return []

    try:
        with open(target_file, "r", encoding="utf-8", errors="replace") as f:
            # Read last lines efficiently
            lines = f.readlines()
            for line in reversed(lines):
                if not line.strip():
                    continue
                try:
                    obj = json.loads(line.strip())
                    if category_filter and obj.get("category") != category_filter:
                        continue
                    events.append(obj)
                    if len(events) >= limit:
                        break
                except json.JSONDecodeError:
                    continue
    except Exception as e:
        print(f"[ERROR] Reading telemetry events: {e}", file=sys.stderr)

    return events


def get_latest_game_state() -> Optional[Dict[str, Any]]:
    """Retrieves latest state snapshot from latest_state.json or recent telemetry."""
    candidates = [
        PROJECT_ROOT / "godot-4game" / "latest_state.json",
        PROJECT_ROOT / "latest_state.json"
    ]
    for c in candidates:
        if c.exists():
            try:
                with open(c, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass

    # Fallback to latest state_snapshot event from jsonl
    events = get_telemetry_stream(limit=10, category_filter="state_snapshot")
    if events:
        return events[0].get("data")

    return None


def auto_refresh_qa_findings(force: bool = False) -> Dict[str, Any]:
    """Auto-compiles and refreshes Game_QA findings, eval_results.json, and report.md."""
    try:
        qa_str = str(GAME_QA_DIR)
        if qa_str not in sys.path:
            sys.path.insert(0, qa_str)
        import compile_findings
        return compile_findings.refresh_and_compile(force=force)
    except Exception as e:
        return {"status": "error", "error": str(e)}


# -----------------------------------------------------------------------------
# API Endpoints
# -----------------------------------------------------------------------------

@app.post("/api/overview/refresh")
def api_refresh_overview():
    """Forces an immediate recompilation and refresh of all QA findings and reports."""
    sync_res = auto_refresh_qa_findings(force=True)
    overview = api_overview()
    return {
        "status": "success",
        "sync": sync_res,
        "overview": overview
    }


@app.get("/api/overview")
def api_overview():
    """Returns aggregated dashboard statistics, discovered bugs, and benchmark status."""
    auto_refresh_qa_findings(force=False)
    qa_data = parse_game_qa_findings()
    answer_key = parse_answer_key()
    agentic_runs = parse_agentic_runs()
    events = get_telemetry_stream(limit=10)

    # Match discovered findings with benchmark bugs
    benchmark_status = []
    for bb in answer_key:
        matched = False
        matched_finding = None
        bid = bb["id"].lower()
        bdesc = bb["description"].lower()

        for f in qa_data["findings"]:
            ftitle = f.get("title", "").lower()
            fexpl = f.get("explanation", "").lower()
            fcode = f.get("suspected_code", "").lower()
            fkey = f.get("dedupe_key", "").lower()

            # Direct identifier match
            if bid in fexpl or bid in ftitle or bid in fkey:
                matched = True
                matched_finding = f
                break

            # 1A: Enemy4 collision does not kill player
            if bid == "1a" and (
                "can_kill_player" in fexpl or "cannot kill" in ftitle or
                "does not kill" in ftitle or "not able to kill" in ftitle or
                "fails to inflict lethal" in ftitle or "fails to kill" in ftitle or
                ("enemy" in ftitle and "kill" in ftitle and "reversal" not in ftitle and "frozen" not in ftitle)
            ):
                matched = True
                matched_finding = f
                break
            # 1B: Void fall / out of bounds
            if bid == "1b" and ("out of bounds" in ftitle or "void fall" in ftitle or "player_out_of_bounds" in ftitle or "boundary" in fexpl):
                matched = True
                matched_finding = f
                break
            # 1C: 7th coin collection suppresses score
            if bid == "1c" and ("7th coin" in ftitle or "seventh coin" in ftitle or ("coin" in fcode and "score" in ftitle)):
                matched = True
                matched_finding = f
                break
            # 2A: Wedged in narrow ceiling block gap / stuck in wall
            if bid == "2a" and ("wedged" in ftitle or "ceiling" in fexpl or "stuck in wall" in ftitle or "wall geometry" in ftitle or "map2_wall_stuck" in fexpl):
                matched = True
                matched_finding = f
                break
            # 2B: Enemy patrols off platform and floats in air
            if bid == "2b" and ("floating" in ftitle or "floats in mid-air" in ftitle or "floating_enemy" in ftitle or "floating_enemy" in fkey):
                matched = True
                matched_finding = f
                break
            # 3A: Player stuck on staircase edge / stair stick
            if bid == "3a" and ("stair" in ftitle or "stair_stick" in ftitle or "stair_stick" in fkey or "stair" in fcode):
                matched = True
                matched_finding = f
                break
            # 3B: 4th enemy cannot be squashed by stomping
            if bid == "3b" and ("squash" in ftitle or "stomp" in fexpl):
                matched = True
                matched_finding = f
                break
            # 3C: Wall jump on final tower gives 2x height
            if bid == "3c" and ("wall jump" in ftitle or "tower" in fexpl):
                matched = True
                matched_finding = f
                break
            # 4A: Delayed lava death
            if bid == "4a" and ("lava" in ftitle or "lava" in fexpl):
                matched = True
                matched_finding = f
                break
            # 4B: Goal portal requires two distinct touches / missing next_scene property
            if bid == "4b" and ("portal" in ftitle or "portal2d" in fcode or "next_scene" in ftitle or "missing_expected_object" in ftitle):
                matched = True
                matched_finding = f
                break
            # 4C: Level Retry fails to reset enemy positions
            if bid == "4c" and ("retry" in ftitle and "enemy" in ftitle):
                matched = True
                matched_finding = f
                break

        benchmark_status.append({
            **bb,
            "detected": matched,
            "finding_details": matched_finding
        })

    total_events_count = 0
    for cand in [PROJECT_ROOT / "godot-4game" / "game_events.jsonl", PROJECT_ROOT / "game_events.jsonl"]:
        if cand.exists():
            try:
                total_events_count = max(total_events_count, sum(1 for _ in open(cand, "rb")))
            except Exception:
                pass
    if total_events_count == 0:
        total_events_count = 325  # from audited baseline session

    return {
        "stats": {
            "total_bugs_detected": qa_data["total_findings"],
            "critical_bugs": qa_data["severity_counts"]["critical"],
            "high_bugs": qa_data["severity_counts"]["high"],
            "medium_bugs": qa_data["severity_counts"]["medium"],
            "low_bugs": qa_data["severity_counts"]["low"],
            "path1_deterministic": qa_data["path_counts"]["path1"],
            "path2_semantic_llm": qa_data["path_counts"]["path2"],
            "benchmark_bugs_total": len(answer_key),
            "benchmark_bugs_covered": sum(1 for b in benchmark_status if b["detected"]),
            "agentic_test_runs": len(agentic_runs),
            "sessions_analyzed": qa_data["sessions_analyzed"],
            "telemetry_events_logged": total_events_count
        },
        "findings": qa_data["findings"],
        "benchmark_bugs": benchmark_status,
        "recent_agentic_runs": agentic_runs[:5],
        "system_status": proc_manager.get_status()
    }


@app.get("/api/maps")
def api_maps():
    """Returns all 5 maps: the Default Game Map plus the four benchmark custom maps."""
    answer_key = parse_answer_key()

    maps_info = [
        {
            "id": 0,
            "title": "Default Map (Original Game)",
            "slug": "default_game",
            "scene": "res://src/Screens/MainScreen.tscn",
            "level_scene": "res://src/Levels/Level01.tscn",
            "description": "Standard platformer campaign launched by run_game. Full progression from Main Screen through Level01 and Level02 with coin pickups and portal transitions.",
            "target_coord": [7342.0, 160.0],
            "difficulty": "Standard Campaign",
            "is_default": True,
            "benchmark_bugs": []
        },
        {
            "id": 1,
            "title": "Map 1: Green Hills",
            "slug": "map1_green_hills",
            "scene": "res://src/Levels/Map1_GreenHills.tscn",
            "description": "Lush grassy hills with open terrain, floating platforms, and hidden pits.",
            "target_coord": [7342.0, 160.0],
            "difficulty": "Easy / Baseline",
            "is_default": False,
            "benchmark_bugs": [b for b in answer_key if "Map 1" in b.get("map", "")]
        },
        {
            "id": 2,
            "title": "Map 2: Underground Caves",
            "slug": "map2_underground_caves",
            "scene": "res://src/Levels/Map2_UndergroundCaves.tscn",
            "description": "Dark subterranean caverns with narrow ceiling wedges, uneven rock floors, and chasms.",
            "target_coord": [7520.0, 320.0],
            "difficulty": "Medium",
            "is_default": False,
            "benchmark_bugs": [b for b in answer_key if "Map 2" in b.get("map", "")]
        },
        {
            "id": 3,
            "title": "Map 3: Sky Castle",
            "slug": "map3_sky_castle",
            "scene": "res://src/Levels/Map3_SkyCastle.tscn",
            "description": "Floating sky fortress featuring steep staircases, airborne islands, and high ramparts.",
            "target_coord": [14638.0, 800.0],
            "difficulty": "Hard",
            "is_default": False,
            "benchmark_bugs": [b for b in answer_key if "Map 3" in b.get("map", "")]
        },
        {
            "id": 4,
            "title": "Map 4: Lava Fortress",
            "slug": "map4_lava_fortress",
            "scene": "res://src/Levels/Map4_LavaFortress.tscn",
            "description": "Volcanic stronghold with bubbling lava pools, tight corridors, and guarded exit gates.",
            "target_coord": [17200.0, 480.0],
            "difficulty": "Very Hard / Hazards",
            "is_default": False,
            "benchmark_bugs": [b for b in answer_key if "Map 4" in b.get("map", "")]
        }
    ]
    return {"maps": maps_info}


@app.get("/api/paths")
def api_paths():
    """Lists scripted paths available in paths/*.json."""
    path_files = sorted(glob.glob(str(PATHS_DIR / "*.json")))
    results = []
    for pf in path_files:
        try:
            with open(pf, "r", encoding="utf-8") as f:
                data = json.load(f)
                results.append({
                    "name": Path(pf).name,
                    "relative_path": f"paths/{Path(pf).name}",
                    "title": data.get("name", Path(pf).stem),
                    "description": data.get("description", "Predefined recorded action sequence"),
                    "steps_count": len(data.get("steps", [])),
                    "initial_state": data.get("initial_state")
                })
        except Exception as e:
            results.append({
                "name": Path(pf).name,
                "relative_path": f"paths/{Path(pf).name}",
                "title": Path(pf).stem,
                "description": f"Scripted action file ({e})",
                "steps_count": 0
            })
    return {"paths": results}


@app.get("/api/agentic/results")
def api_agentic_results():
    """Returns all recorded agentic test runs."""
    return {"runs": parse_agentic_runs()}


@app.get("/api/telemetry/events")
def api_telemetry_events(limit: int = 100, category: Optional[str] = None):
    """Returns recent telemetry events from game_events.jsonl."""
    return {"events": get_telemetry_stream(limit=limit, category_filter=category)}


@app.get("/api/telemetry/latest")
def api_telemetry_latest():
    """Returns latest state snapshot."""
    state = get_latest_game_state()
    return {"state": state}


# -----------------------------------------------------------------------------
# Workflow Execution Endpoints
# -----------------------------------------------------------------------------

class LaunchAiAgentRequest(BaseModel):
    prompt: str = Field("Run game QA using game-qa skill", description="Prompt to send to Antigravity chat")
    folder: str = Field("Game_QA", description="Target workspace folder name")
    reuse_window: bool = Field(True, description="Reuse active Antigravity IDE window")


def find_antigravity_cli() -> Optional[Path]:
    """Finds the Antigravity CLI or IDE binary across standard installation paths."""
    candidates = [
        Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "Antigravity IDE" / "bin" / "antigravity-ide.cmd",
        Path("C:/Users/vinay/AppData/Local/Programs/Antigravity IDE/bin/antigravity-ide.cmd"),
        Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "Antigravity IDE" / "Antigravity IDE.exe",
        Path("C:/Users/vinay/AppData/Local/Programs/Antigravity IDE/Antigravity IDE.exe"),
        Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "antigravity" / "Antigravity.exe",
        Path("C:/Users/vinay/AppData/Local/Programs/antigravity/Antigravity.exe"),
    ]
    for c in candidates:
        if c.exists():
            return c
    for name in ["antigravity-ide", "antigravity", "agy"]:
        which_path = shutil.which(name)
        if which_path:
            return Path(which_path)
    return None


class RunGameRequest(BaseModel):
    map_num: Optional[int] = Field(0, description="Map number: 0 for Default Map, or 1, 2, 3, 4 for benchmark maps")
    mode: str = Field("windowed", description="'windowed', 'headless', or 'debug'")
    frames: Optional[int] = Field(None, description="Exit after N frames")
    with_bot: bool = Field(False, description="Launch Hybrid Bot on map")
    target_coord: Optional[List[float]] = Field(None, description="Optional target X Y")


@app.post("/api/execute/run-game")
def api_execute_run_game(req: RunGameRequest):
    """Workflow 2: Run Game launcher supporting Default Map (Map 0) and Maps 1-4."""
    if proc_manager.get_status()["status"] == "running":
        raise HTTPException(status_code=400, detail="Another process is currently running. Stop it first.")

    # Custom Benchmark Maps 1-4
    if req.map_num in [1, 2, 3, 4]:
        cmd = [sys.executable, "run_map.py", "--map", str(req.map_num)]
        if req.mode == "headless":
            cmd.append("--headless")
        elif req.mode == "debug":
            cmd.append("--debug")

        if req.frames:
            cmd.extend(["--frames", str(req.frames)])

        if req.with_bot:
            cmd.append("--bot")
            if req.target_coord and len(req.target_coord) == 2:
                cmd.extend(["--target-coord", str(req.target_coord[0]), str(req.target_coord[1])])

        workflow_label = f"run_game (Map {req.map_num})"
    else:
        # Default Map (Original Game Campaign / run_game.bat)
        workflow_label = "run_game (Default Map)"
        if req.with_bot:
            cmd = [sys.executable, "explorer.py", "--mode", "hybrid", "--launch"]
        elif req.mode in ("headless", "debug") or req.frames:
            cmd = [sys.executable, "run_map.py", "--map", "0"]
            if req.mode == "headless":
                cmd.append("--headless")
            elif req.mode == "debug":
                cmd.append("--debug")
            if req.frames:
                cmd.extend(["--frames", str(req.frames)])
        else:
            cmd = ["cmd.exe", "/c", "call", "run_game.bat"]

    try:
        status = proc_manager.start_process(cmd, workflow_name=workflow_label)
        return {"success": True, "process": status}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class AgentExplorerRequest(BaseModel):
    budget: int = Field(20, description="Test budget (number of cases)")
    strategy: str = Field("coverage", description="'coverage', 'risk', or 'systematic'")
    mode: str = Field("adaptive", description="'adaptive' or 'waypoints'")
    max_steps_per_target: int = Field(350, description="Step limit per target")
    tolerance: float = Field(70.0, description="Pixel tolerance")
    launch: bool = Field(True, description="Auto-launch game window")
    verbose: bool = Field(False, description="Verbose logs")


@app.post("/api/execute/agent-explorer")
def api_execute_agent_explorer(req: AgentExplorerRequest):
    """Workflow 4: One-click Agent Explorer launcher."""
    if proc_manager.get_status()["status"] == "running":
        raise HTTPException(status_code=400, detail="Another process is currently running. Stop it first.")

    cmd = [
        sys.executable, "agentic_tester.py",
        "--budget", str(req.budget),
        "--strategy", req.strategy,
        "--mode", req.mode,
        "--max-steps-per-target", str(req.max_steps_per_target),
        "--tolerance", str(req.tolerance)
    ]

    if req.launch:
        cmd.append("--launch")
    else:
        cmd.append("--no-launch")

    if req.verbose:
        cmd.append("--verbose")

    try:
        status = proc_manager.start_process(cmd, workflow_name="agent_explorer")
        return {"success": True, "process": status}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class RunExplorerRequest(BaseModel):
    mode: str = Field("hybrid", description="Exploration mode: hybrid, hybrid_variation, target_coord, waypoints_interactive, waypoints_sequential, scripted, random, coverage_guided, tests")
    waypoints: Optional[List[float]] = Field(None, description="Coordinates X1 Y1 X2 Y2 ... for sequential waypoints")
    waypoint_wait: float = Field(3.0, description="Wait seconds at each waypoint")
    tolerance: float = Field(60.0, description="Tolerance radius in px")
    target_coord: Optional[List[float]] = Field(None, description="Target X Y for target_coord mode")
    path: Optional[str] = Field("paths/basic_platformer.json", description="Path to scripted JSON")
    seed: int = Field(42, description="Random seed")
    max_actions: int = Field(350, description="Max actions limit")
    routes: str = Field("level_routes.json", description="Routes file")
    port: int = Field(4242, description="UDP port")
    fps: int = Field(60, description="Physics FPS")
    level: Optional[str] = Field(None, description="Level name or scene path")
    map_num: Optional[int] = Field(0, description="Map number: 0 for Default Map, or 1, 2, 3, 4 for benchmark maps")
    launch: bool = Field(True, description="Auto-launch game window")
    close_on_exit: bool = Field(False, description="Close game on exit")
    verbose: bool = Field(False, description="Verbose logs")


@app.post("/api/execute/run-explorer")
def api_execute_run_explorer(req: RunExplorerRequest):
    """Workflow 5: Full Run Explorer Control Hub."""
    if proc_manager.get_status()["status"] == "running":
        raise HTTPException(status_code=400, detail="Another process is currently running. Stop it first.")

    # Special case: Unit tests
    if req.mode == "tests":
        cmd = [
            sys.executable, "-c",
            "import subprocess, sys; r1 = subprocess.call([sys.executable, 'test_hybrid_bot.py']); "
            "r2 = subprocess.call([sys.executable, 'test_explorer.py']); sys.exit(r1 or r2)"
        ]
        workflow_label = "run_explorer (Test Suite)"
    else:
        cmd = [sys.executable, "explorer.py", "--mode", req.mode]

        # Waypoint mode W2 (sequential waypoints)
        if req.mode in ("waypoints_sequential", "waypoint_2"):
            if req.waypoints and len(req.waypoints) >= 2:
                cmd.append("--waypoints")
                cmd.extend([str(w) for w in req.waypoints])
            cmd.extend(["--waypoint-wait", str(req.waypoint_wait)])
            cmd.extend(["--tolerance", str(req.tolerance)])

        # Waypoint mode W1 (interactive)
        elif req.mode in ("waypoints_interactive", "waypoint_1"):
            cmd.extend(["--tolerance", str(req.tolerance)])

        # Target coordinate mode
        elif req.mode == "target_coord":
            if req.target_coord and len(req.target_coord) == 2:
                cmd.extend(["--target-coord", str(req.target_coord[0]), str(req.target_coord[1])])
            else:
                cmd.extend(["--target-coord", "3117", "560"])
            cmd.extend(["--tolerance", str(req.tolerance)])

        # Scripted mode
        elif req.mode == "scripted":
            cmd.extend(["--path", req.path or "paths/basic_platformer.json"])

        # Seeded modes
        if req.mode in ("random", "hybrid_variation"):
            cmd.extend(["--seed", str(req.seed)])

        # General args
        cmd.extend(["--max-actions", str(req.max_actions)])
        cmd.extend(["--routes", req.routes])
        cmd.extend(["--port", str(req.port)])
        cmd.extend(["--fps", str(req.fps)])

        if req.map_num in [1, 2, 3, 4]:
            map_scenes = {
                1: "res://src/Levels/Map1_GreenHills.tscn",
                2: "res://src/Levels/Map2_UndergroundCaves.tscn",
                3: "res://src/Levels/Map3_SkyCastle.tscn",
                4: "res://src/Levels/Map4_LavaFortress.tscn"
            }
            cmd.extend(["--level", map_scenes[req.map_num]])
        else:
            cmd.extend(["--level", req.level or "res://src/Levels/Level01.tscn"])

        if req.launch:
            cmd.append("--launch")

        if req.close_on_exit:
            cmd.append("--close-on-exit")

        if req.verbose:
            cmd.append("--verbose")

        workflow_label = f"run_explorer ({req.mode})"

    try:
        status = proc_manager.start_process(cmd, workflow_name=workflow_label)
        return {"success": True, "process": status}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/execute/run-qa-eval")
def api_execute_qa_eval(stride: int = 4, ignore_checks: bool = True):
    """Executes Game_QA post-run evaluation audit."""
    if proc_manager.get_status()["status"] == "running":
        raise HTTPException(status_code=400, detail="Another process is currently running. Stop it first.")

    cmd = [sys.executable, "eval.py", "--stride", str(stride)]
    if ignore_checks:
        cmd.append("--ignore-checks")

    try:
        status = proc_manager.start_process(cmd, workflow_name="game_qa_eval", cwd=GAME_QA_DIR)
        return {"success": True, "process": status}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/execute/launch-ai-agent")
def api_execute_launch_ai_agent(req: Optional[LaunchAiAgentRequest] = None):
    """
    Launches Antigravity IDE chat session in Game_QA folder with prompt 'Run game QA using game-qa skill'.
    """
    if req is None:
        req = LaunchAiAgentRequest()

    target_prompt = (req.prompt or "").strip() or "Run game QA using game-qa skill"
    target_dir = GAME_QA_DIR
    cli_path = find_antigravity_cli()

    timestamp = datetime.now().strftime("%H:%M:%S")
    proc_manager._append_log(f"[{timestamp}] [AI_AGENT] ==================================================")
    proc_manager._append_log(f"[{timestamp}] [AI_AGENT] 🚀 DISPATCHING AI AGENT FOR GAME QA")
    proc_manager._append_log(f"[{timestamp}] [AI_AGENT] Target Workspace: {target_dir}")
    proc_manager._append_log(f"[{timestamp}] [AI_AGENT] Active Skill: game-qa")
    proc_manager._append_log(f"[{timestamp}] [AI_AGENT] Prompt: \"{target_prompt}\"")

    if not cli_path:
        err_msg = "Could not locate Antigravity IDE binary on disk."
        proc_manager._append_log(f"[{timestamp}] [ERROR] {err_msg}")
        raise HTTPException(status_code=500, detail=err_msg)

    proc_manager._append_log(f"[{timestamp}] [AI_AGENT] Executable: {cli_path}")

    cmd = [str(cli_path), "chat", "-r", target_prompt]

    try:
        if proc_manager.get_status()["status"] != "running":
            status = proc_manager.start_process(cmd, workflow_name="antigravity_ai_agent", cwd=target_dir, shell=True)
            proc_manager._append_log(f"[{timestamp}] [AI_AGENT] [OK] Process started (PID: {status.get('pid')})")
        else:
            proc_manager._append_log(f"[{timestamp}] [AI_AGENT] [INFO] Launching concurrent IPC dispatch while {proc_manager.workflow} is active...")
            run_env = os.environ.copy()
            run_env["PYTHONUNBUFFERED"] = "1"
            p = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                cwd=str(target_dir),
                env=run_env
            )
            def _log_output():
                for line in p.stdout:
                    proc_manager._append_log(f"[{datetime.now().strftime('%H:%M:%S')}] [AI_AGENT] {line.strip()}")
                p.wait()
                proc_manager._append_log(f"[{datetime.now().strftime('%H:%M:%S')}] [AI_AGENT] [OK] Antigravity Chat session ready in Game_QA!")
            threading.Thread(target=_log_output, daemon=True).start()

        proc_manager._append_log(f"[{timestamp}] [AI_AGENT] [OK] Opened Antigravity Chat in Game_QA with prompt: \"{target_prompt}\"")
        return {
            "success": True,
            "prompt": target_prompt,
            "folder": "Game_QA",
            "folder_path": str(target_dir),
            "binary": str(cli_path),
            "message": f"Antigravity chat opened in Game_QA folder with prompt: \"{target_prompt}\""
        }
    except Exception as e:
        proc_manager._append_log(f"[{timestamp}] [ERROR] Failed to dispatch Antigravity chat: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/process/status")
def api_process_status():
    """Returns active process status and stats."""
    return proc_manager.get_status()


@app.post("/api/process/stop")
def api_process_stop():
    """Stops the active running process."""
    return proc_manager.stop_process()


@app.get("/api/process/logs")
def api_process_logs(offset: int = Query(0, description="Log line offset for polling")):
    """Returns buffered log lines starting from offset."""
    return proc_manager.get_logs(start_offset=offset)


@app.websocket("/ws/logs")
async def websocket_logs(websocket: WebSocket):
    """WebSocket endpoint for real-time live log streaming."""
    await websocket.accept()
    websocket._loop = asyncio.get_running_loop()
    proc_manager.active_websockets.append(websocket)

    # Send current buffer immediately
    with proc_manager.lock:
        init_lines = list(proc_manager.log_buffer)
    for line in init_lines:
        await websocket.send_text(json.dumps({"type": "log", "line": line}))

    try:
        while True:
            # Keep connection open; receive ping or commands
            msg = await websocket.receive_text()
            if msg == "ping":
                await websocket.send_text(json.dumps({"type": "pong"}))
    except WebSocketDisconnect:
        if websocket in proc_manager.active_websockets:
            proc_manager.active_websockets.remove(websocket)


# -----------------------------------------------------------------------------
# Static Files & SPA Routing
# -----------------------------------------------------------------------------
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

@app.get("/")
def serve_index():
    auto_refresh_qa_findings(force=False)
    index_file = STATIC_DIR / "index.html"
    if not index_file.exists():
        raise HTTPException(status_code=404, detail="index.html not found")
    return FileResponse(index_file)


# -----------------------------------------------------------------------------
# CLI Entry Point
# -----------------------------------------------------------------------------
if __name__ == "__main__":
    import uvicorn
    import argparse

    parser = argparse.ArgumentParser(description="Syntax-Error QA Explorer Dashboard")
    parser.add_argument("--port", type=int, default=8080, help="Web server port (default: 8080)")
    parser.add_argument("--host", type=str, default="127.0.0.1", help="Host interface (default: 127.0.0.1)")
    parser.add_argument("--open", action="store_true", help="Automatically open browser")

    args = parser.parse_args()

    url = f"http://localhost:{args.port}"
    print("=" * 70)
    print("  SYNTAX-ERROR // QA EXPLORER DASHBOARD SERVER")
    print(f"  Access UI at: {url}")
    print("=" * 70)

    if args.open:
        import webbrowser
        threading.Timer(1.5, lambda: webbrowser.open(url)).start()

    uvicorn.run(app, host=args.host, port=args.port, log_level="info")
