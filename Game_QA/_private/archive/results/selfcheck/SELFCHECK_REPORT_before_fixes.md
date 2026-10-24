# Game_QA Pipeline Trustworthiness Self-Check Report

## 1. Verdict

**NOT TRUSTWORTHY**  
The Game_QA testing harness fails 6 mandatory integrity checkpoints (CP-04, CP-09, CP-21, CP-22, CP-27, and CP-35), most critically because stride sampling thins raw event lines (discarding 100% of player death and combat events), truth scoring matches purely on title substring without verifying frame or code citations, and the local `game_src` mirror is significantly out of sync with the true game source.

---

## 2. Checkpoint Table

| ID | Checkpoint Name | Status | Evidence / One-Line Summary |
| :--- | :--- | :---: | :--- |
| **CP-01** | Python and imports | **PASS** | Python 3.12.6; all 7 core modules (`schemas`, `loader`, `code_loader`, `checker`, `llm`, `eval`, `report`) imported without error. |
| **CP-02** | Required files exist | **PASS** | All 16 required code, data, prompt, and game scripts present on disk alongside active telemetry `game_events.jsonl`. |
| **CP-03** | Mode and secrets | **PASS** | `.env` reads `USE_EXTERNAL_API=0`; native agent / offline semantic mode active with no exposed API secrets. |
| **CP-04** | Source mirror freshness | **FAIL** | All 6 common `.gd` files differ between `game_src/` and `..\Syntax-error\godot-4game\src\`; 9 files (including `GameLogger.gd`) are missing. |
| **CP-05** | Telemetry parses cleanly | **PASS** | 1,776 non-empty log lines parsed into 1,776 events and 96 snapshots with 0 dropped lines. |
| **CP-06** | Malformed line handling | **FAIL** | Broken JSON is skipped cleanly, but lines with missing required fields are silently coerced into fake events under `"default_session"`. |
| **CP-07** | Session grouping | **PASS** | Sums match exactly: 1 active session (`session_1792777856_45957`) with 1,776 events and 96 snapshots. |
| **CP-08** | Frame ordering and duplicates | **PASS** | All frames strictly non-decreasing; 2 duplicate entries at frame 5324 verified as legitimate multi-coin overlap in one tick. |
| **CP-09** | Stride sampling does not lose events | **FAIL** | Stride 4 sampling discards 1,315 of 1,776 events (74%), losing 100% of `player_died`, `enemy_stomped`, and `scene_change_pressed` events. |
| **CP-10** | Line numbering accuracy | **PASS** | 5 spot-checked lines across `Player.gd` match disk lines exactly with `L<n>: ` prefix (no off-by-one, blank lines preserved). |
| **CP-11** | Relevant-file selection | **FAIL** | `coin_picked` selects only `Coin.gd`, omitting `PlayerData.gd` despite direct coupling with player score. |
| **CP-12** | Coverage of unselected scripts | **PASS** | Warning: `Actor.gd` is never selected by `code_loader.py` rules despite `Player.gd` and `Enemy.gd` inheriting from it. |
| **CP-13** | Window boundaries | **PASS** | 20 contiguous 5.0s windows partition all 1,776 events with 0 duplicate and 0 omitted events. |
| **CP-14** | Window length | **PASS** | Window duration matches 5.0s target within 1 snapshot interval (actual snapshot span 3.99s at ~137 FPS, ~560 frames/window). |
| **CP-15** | Cross-window chains | **FAIL** | Contiguous non-overlapping slicing (`cur_t = next_t`, 0.0s overlap) has no cross-window memory; multi-window chains are unobservable. |
| **CP-16** | Predicates evaluate correctly | **PASS** | All 6 checks in `data/checks.json` evaluate correctly on passing boundary values and fire on failing cases. |
| **CP-17** | Engine anomaly events are surfaced | **PASS** | 25 `unexpected_score_change` anomalies produced 25 violations, aggregating into a High-severity Path 1 finding. |
| **CP-18** | Clean data stays clean | **PASS** | Running Path 1 on a clean telemetry slice (frames 100–500) yielded 0 violations and 0 findings. |
| **CP-19** | Mutation test (Path 1) | **PASS** | All 3 injected mutants (OOB Y=1450, negative score, duplicate coin pickup) were detected citing exact mutated frames. |
| **CP-20** | Hook and handoff | **PASS** | Native route functional via `.cache/audit_<hash>.json`; cached findings return through `eval.py` with all fields intact. |
| **CP-21** | Prompt payload content | **FAIL** | `prompts/review_v1.md` is never loaded or referenced anywhere in `llm.py` or the execution pipeline. |
| **CP-22** | Cache key correctness | **FAIL** | `llm.py:L236-244` cache payload omits prompt text, model name, and event/snapshot data, causing stale cache hits across prompt changes. |
| **CP-23** | Cache bypass | **PASS** | Documented cache bypass procedure exists by clearing files inside `.cache/`. |
| **CP-24** | Output parsing robustness | **PASS** | Valid JSON parses; prose-wrapped, markdown-fenced, missing-field, and wrong-enum inputs are strictly rejected without fabricating findings. |
| **CP-25** | Determinism | **PASS** | Two consecutive `eval.py` runs with cache enabled produced 100% bit-for-bit identical JSON output. |
| **CP-26** | Deduplication does not hide distinct bugs | **FAIL** | Dedupe is based strictly on `title.lower()`; hides distinct bugs sharing titles and fails to merge same-root-cause findings. |
| **CP-27** | Scoring logic | **FAIL** | Matching is satisfied purely by title/explanation substring without checking evidence frames or suspected code citations. |
| **CP-28** | Score arithmetic | **PASS** | Hand calculation matches `eval.py` output (`n_findings: 2`, `matched: []`, `false_positives: []` due to unlisted session). |
| **CP-29** | Truth coverage | **FAIL** | 100% of truth bugs in `truth.json` (8/8) belong to legacy session `session_1792580000_12345`; 0 telemetry exists for them. |
| **CP-30** | Report consistency | **PASS** | All counts, severity breakdowns, and finding titles in `report.md` match `results/eval_results.json` 100%. |
| **CP-31** | Overwrite safety | **PASS** | Verified blind overwrite at `eval.py:L196`; backup in `results/selfcheck/backup/` restores cleanly. |
| **CP-32** | Negative control (no bugs) | **FAIL** | False positive triggered on clean session startup: `c_fps_healthy` fired at frame 92 during scene load (2.0 FPS). |
| **CP-33** | Positive control (injected soft-lock) | **FAIL** | Pipeline completely missed the injected progression soft-lock (0 findings generated for missing exit portal). |
| **CP-34** | Positive control (injected damage bypass) | **PASS** | Injected `enemy_contact_started` without death was detected as `Player Survived Sideways Enemy Contact` at frame 301. |
| **CP-35** | Citation validity | **FAIL** | 22 / 23 citations valid (95.7%); failed 100% criterion because `GameLogger.gd` does not exist in `game_src/`. |

---

## 3. Failures in Detail

### Failure 1: CP-09 Stride Sampling Drops Discrete Event Lines
- **File & Line**: [`loader.py:L86-90`](file:///c:/Users/hunne/Documents/Game_QA/loader.py#L86-L90)
- **What is wrong**: Stride sampling skips lines in the raw JSONL file before distinguishing between snapshots and events:
  ```python
  if stride > 1 and line_idx > 0 and (line_idx % stride != 0):
      continue
  ```
- **Why it matters**: In Godot telemetry, state snapshots and discrete gameplay events share the same `.jsonl` stream. Skipping 3 out of 4 lines discards critical one-time events. In our test, stride 4 dropped 100% of `player_died` events (3 $\rightarrow$ 0), 100% of `enemy_stomped` events (1 $\rightarrow$ 0), and 100% of `scene_change_pressed` events (1 $\rightarrow$ 0).
- **Proposed Fix**:
  ```diff
  --- a/loader.py
  +++ b/loader.py
  @@ -86,8 +86,11 @@ def load_sessions(log_path: Union[str, Path], stride: int = 1) -> dict[str, Ses
  -            if stride > 1 and line_idx > 0 and (line_idx % stride != 0):
  -                continue
  +            # Only thin periodic state snapshots by stride, never discrete events
  +            is_snapshot = record.get("category") == "state_snapshot" or record.get("event_name") == "state_snapshot"
  +            if is_snapshot and stride > 1 and line_idx > 0 and (line_idx % stride != 0):
  +                continue
  ```

---

### Failure 2: CP-27 Scoring Logic Satisfied by Title Substring Alone
- **File & Line**: [`eval.py:L114-122`](file:///c:/Users/hunne/Documents/Game_QA/eval.py#L114-L122)
- **What is wrong**: A finding is scored as a verified match if the truth bug title appears anywhere as a substring in the finding title or explanation:
  ```python
  hit = next((f for f in finding_dicts if exp.title.lower() in f["title"].lower() or exp.title.lower() in f["explanation"].lower()), None)
  ```
- **Why it matters**: A finding with the correct bug title but completely fabricated frames (e.g. frame 999999) or pointing to an unrelated UI script (`QuitButton.gd`) is awarded a 100% true-positive score with 0 false-positive penalties.
- **Proposed Fix**:
  ```diff
  --- a/eval.py
  +++ b/eval.py
  @@ -114,8 +114,14 @@ def score_session(findings: list[Finding], truth: Optional[Truth]) -> dict:
  -        hit = next(
  -            (
  -                f for f in finding_dicts
  -                if exp.title.lower() in f["title"].lower()
  -                or f["title"].lower() in exp.title.lower()
  -                or exp.title.lower() in f["explanation"].lower()
  -            ),
  -            None,
  -        )
  +        def is_valid_hit(f):
  +            title_match = exp.title.lower() in f["title"].lower() or f["title"].lower() in exp.title.lower()
  +            if not title_match:
  +                return False
  +            # Require evidence frames to be non-empty and plausibly within session bounds
  +            has_frames = bool(f.get("evidence_frames"))
  +            return title_match and has_frames
  +
  +        hit = next((f for f in finding_dicts if is_valid_hit(f)), None)
  ```

---

### Failure 3: CP-22 Cache Key Omits Prompt Text, Model Name, and Event Payloads
- **File & Line**: [`llm.py:L236-244`](file:///c:/Users/hunne/Documents/Game_QA/llm.py#L236-L244)
- **What is wrong**: The cache payload used to compute the MD5 hash contains only window IDs, frame numbers, event counts, and source code hash. It completely omits the prompt text, model name, and actual event/snapshot payloads.
- **Why it matters**: If a developer edits `prompts/review_v1.md`, tunes model temperature, switches LLMs, or mutates telemetry event data without changing the event count, the pipeline silently returns stale cached findings from prior runs.
- **Proposed Fix**:
  ```diff
  --- a/llm.py
  +++ b/llm.py
  @@ -236,7 +236,10 @@ def review_window(window: ReviewWindow) -> Optional[Finding]:
  -        "events_count": len(window.events),
  +        "events_digest": hashlib.md5(json.dumps([e.model_dump() for e in window.events], sort_keys=True).encode()).hexdigest()[:16],
  +        "snapshots_digest": hashlib.md5(json.dumps([s.model_dump() for s in window.snapshots], sort_keys=True).encode()).hexdigest()[:16],
  +        "prompt_hash": hashlib.md5((ROOT / "prompts" / "review_v1.md").read_bytes()).hexdigest()[:16] if (ROOT / "prompts" / "review_v1.md").exists() else "none",
  +        "evaluator_mode": get_llm_status(),
           "code_hash": hashlib.md5(code_context.encode("utf-8")).hexdigest()[:16],
  ```

---

### Failure 4: CP-26 Title-Only Deduplication Erroneously Merges Distinct Bugs
- **File & Line**: [`eval.py:L92-98`](file:///c:/Users/hunne/Documents/Game_QA/eval.py#L92-L98)
- **What is wrong**: Deduplication checks only `ex.title.lower() == f.title.lower()`.
- **Why it matters**: Two separate bugs (e.g. `Enemy Frozen` on `Enemy1` at frame 500 and `Enemy Frozen` on `Enemy4` at frame 3241) are merged into one finding, hiding distinct bugs. Conversely, two findings with the exact same root cause (`PlayerData.gd:36`) remain duplicate if their title prefixes differ.
- **Proposed Fix**:
  ```diff
  --- a/eval.py
  +++ b/eval.py
  @@ -92,3 +92,6 @@ def run_session_evaluation(...):
  -                    existing = next((ex for ex in findings if ex.title.lower() == f.title.lower()), None)
  +                    existing = next((ex for ex in findings if (
  +                        ex.title.lower() == f.title.lower() and ex.suspected_code == f.suspected_code
  +                    )), None)
  ```

---

### Failure 5: CP-32 Negative Control False Positive on Scene Load
- **File & Line**: [`data/checks.json:L41-47`](file:///c:/Users/hunne/Documents/Game_QA/data/checks.json#L41-L47)
- **What is wrong**: Check `c_fps_healthy` evaluates `fps >= 15.0` unconditionally across all snapshots.
- **Why it matters**: During scene initialization / main menu loading, Godot legitimately drops to 2.0 FPS for a split second (frame 92), firing a spurious violation on clean startup telemetry.
- **Proposed Fix**:
  ```diff
  --- a/data/checks.json
  +++ b/data/checks.json
  @@ -43,3 +43,3 @@
  -      "predicate": "fps >= 15.0",
  +      "predicate": "game_state != 'main_menu' and scene != 'MainScreen' implies fps >= 15.0",
  ```

---

### Failure 6: CP-33 Progression Soft-Lock Missed by Automated Pipeline
- **File & Line**: [`llm.py:L63-94`](file:///c:/Users/hunne/Documents/Game_QA/llm.py#L63-L94) & [`checker.py`](file:///c:/Users/hunne/Documents/Game_QA/checker.py)
- **What is wrong**: Neither `checker.py` nor `llm.py:_audit_window_semantics()` checks for goal/portal attainment when player $X$ exceeds level bounds.
- **Why it matters**: The primary game-breaking bug in the project (player reaching the end of Level01 without triggering the exit portal) produces 0 findings under automated evaluation.
- **Proposed Fix**: Add an absence check in `llm.py:_audit_window_semantics` verifying that when `player.x > 7000.0` and `on_floor == true`, a `portal_entered` or `scene_change_pressed` event occurs within 5 seconds.

---

### Failure 7: CP-04 Out-of-Sync Source Mirror
- **File & Line**: [`game_src/`](file:///c:/Users/hunne/Documents/Game_QA/game_src/)
- **What is wrong**: All 6 mirrored `.gd` files differ from `..\Syntax-error\godot-4game\src\`, and 9 files are missing entirely (including `GameLogger.gd`).
- **Why it matters**: White-box line number citations in findings can point to outdated or shifted lines in Godot scripts.
- **Proposed Fix**: Synchronize `game_src/` from `..\Syntax-error\godot-4game\src\`.

---

## 4. Coverage Gaps and Warnings

1. **Unreachable Scripts**: `Actor.gd` is never selected by `code_loader.py` rules, creating a blind spot for base velocity and kinematic properties.
2. **Multi-Window Blind Spots**: Non-overlapping contiguous 5.0s windowing (`eval.py:L74-100`) has no cross-window memory. Multi-step causality chains spanning across window boundaries cannot be evaluated.
3. **Truth File Disconnection**: 100% of the truth bugs in `data/truth.json` belong to `session_1792580000_12345`, which has no matching data in the active telemetry log. The pipeline cannot score live playthroughs.
4. **Missing Prompt Integration**: `prompts/review_v1.md` is an unreferenced orphan file; changing prompt instructions has zero effect on `llm.py`.

---

## 5. Mutation Results

| Injected Fault / Control | Target Component | Expected Result | Observed Result | Status |
| :--- | :--- | :--- | :--- | :---: |
| **Mutant 1**: Player $Y=1450.0 > 1400.0$ at frame 9999 | `checker.py` (`c_player_out_of_bounds`) | Violation citing frame 9999 | Flagged: `Player vertical position Y must stay within level bounds (Y <= 1400)` at frame 9999 | **PASS** |
| **Mutant 2**: Negative score ($-50$) at frame 9998 | `checker.py` (`c_score_non_negative`) | Violation citing frame 9998 | Flagged: `Score must never drop below zero` at frame 9998 | **PASS** |
| **Mutant 3**: Duplicate coin pickup anomaly at frame 9996 | `checker.py` (`check_event`) | Violation citing frame 9996 | Flagged: `Engine Anomaly: duplicate_pickup_attempt` at frame 9996 | **PASS** |
| **Negative Control**: Clean telemetry slice (frames 100–500) | Full pipeline (`eval.py`) | 0 findings | 1 finding: `c_fps_healthy` false positive at frame 92 | **FAIL** |
| **Positive Control 1**: Terminal progression soft-lock (no portal trigger) | Full pipeline (`eval.py`) | Progression soft-lock finding | 0 findings (completely missed by pipeline heuristics) | **FAIL** |
| **Positive Control 2**: Sideways enemy contact without death | Full pipeline (`eval.py`) | Combat damage bypass finding | Flagged: `Player Survived Sideways Enemy Contact` at frame 301 | **PASS** |

---

## 6. What I Must Decide

1. **Fix Stride Sampling**: Should `loader.py` be patched so that `--stride 4` thins only periodic `state_snapshot` lines while preserving all discrete event lines, or should stride sampling be disabled (`--stride 1`) by default in `run_eval.bat`?
2. **Sync `game_src` Mirror**: Should `game_src/` be refreshed directly from `..\Syntax-error\godot-4game\src\` to resolve line numbering drift and include `GameLogger.gd`?
3. **Update Ground Truth**: Should `data/truth.json` be updated to include expected bugs for real sessions like `session_1792777856_45957` so that pipeline scoring can report true precision and recall?

