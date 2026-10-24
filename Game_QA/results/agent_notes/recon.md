# Reconnaissance & Baseline Configuration (Phase A)

### 1. USE_EXTERNAL_API Setting & Native Agent Behavior
`USE_EXTERNAL_API` is set to `0`. When set to `0`, native agent mode is active without external third-party API calls; `eval.py` (via `llm.review_window`) checks `.cache/audit_<key>.json` for findings submitted by the native agent, falling back to local heuristic checks `_audit_window_semantics` if no cache entry is present.

### 2. Native Handoff Confirmation
Confirmed. Findings are submitted with:
```powershell
python tools/native_submit.py --session <session_id> --window <window_id> --findings <findings_json_file>
```
`tools/native_submit.py` reconstructs the window identically to `eval.py`, extracts the window's codebase context, computes `llm.window_cache_key(target_window, code_context)`, and writes the validated finding to `.cache/audit_<hash>.json`. When `eval.py` runs, `llm.review_window(rw)` calculates the exact same content-addressed cache key and reads the finding from `.cache/`. No part differs from this handoff specification.

### 3. schemas.Finding Required vs. Optional Fields
- **Required fields (no default)**:
  - `title`: `str`
  - `explanation`: `str`
- **Optional fields (have default values)**:
  - `verdict`: `Verdict` (default `Verdict.bug`)
  - `severity`: `Optional[Severity]` (default `None`)
  - `confidence`: `float` (default `0.95`, range `[0.0, 1.0]`)
  - `evidence_frames`: `list[int]` (default `[]`)
  - `suspected_code`: `Optional[str]` (default `None`)
  - `path`: `Literal["path1", "path2"]` (default `"path1"`)
  - `needs_human_review`: `bool` (default `False`)

### 4. Review Window Size, Stride, Overlap, & Function
- **Window size**: 5.0 seconds (`window_sec = 5.0`).
- **Stride & Overlap**: Stride is 5.0 seconds with 0.0 seconds overlap (contiguous, non-overlapping slices `[cur_t, cur_t + window_sec)`).
- **Constructing function**: `run_session_evaluation` in `eval.py` (and mirrored in `submit_finding` in `tools/native_submit.py`).

### 5. Telemetry Files and Exact Disk Paths
- Primary resolved telemetry log: `C:\Users\hunne\Documents\Syntax-error\game_events.jsonl` (3,009,352 bytes; exists: `True`).
- Audit copy on disk: `C:\Users\hunne\Documents\Game_QA\Game_QA_audit\telemetry\game_events.jsonl` (3,009,352 bytes; exists: `True`).
- Relative path `telemetry/game_events.jsonl` in `Game_QA` root: does not exist on disk (`False`).

### 6. Source & Telemetry Sanitization Check
Command run:
`python tools/sanitize_source.py --check --target game_src --telemetry telemetry/game_events.jsonl`
Output:
```
[check] Manifest Integrity Check: PASS
[check] Forbidden Tokens Scan: PASS (hits: 0)
```
Status: PASS (0 drift, 0 unregistered files, 0 forbidden token hits).

### 7. eval.py CLI Flags
- `--log <path>`: Path to game_events.jsonl (default `None`, auto-resolves)
- `--checks <path>`: Path to checks.json (default `None`)
- `--truth <path>`: Path to truth.json (default `None`)
- `--out <path>`: Path to output eval_results.json (default `results/eval_results.json`)
- `--window <float>`: Window size in seconds for Path 2 review (default `5.0`)
- `--stride <int>`: Sampling stride for snapshots (default `4`)
- `--ignore-checks`: Flag to rely completely on LLM/agent intelligence, ignoring checks.json (default `True`)
- `--use-checks`: Flag to enable deterministic checks from checks.json

### 8. eval.py Behavior on results/eval_results.json
`eval.py` **overwrites** `results/eval_results.json` upon completion (`out_file.write_text(json.dumps(all_results, indent=2), encoding="utf-8")`).

---

### Telemetry Reconciliation Report
- **File**: `C:\Users\hunne\Documents\Syntax-error\game_events.jsonl`
- **Total lines in file**: 1306
- **Non-empty lines**: 1306
- **Events parsed**: 1264
- **Snapshots parsed**: 42
- **Malformed / skipped records**: 0
- **Sum (events + snapshots + malformed)**: 1306 (equals non-empty line count exactly: `1264 + 42 + 0 == 1306`)
- **Per-session breakdown**:
  - `session_1792862072_26412`: 1306 total lines (1264 events, 42 snapshots, 0 skipped).

