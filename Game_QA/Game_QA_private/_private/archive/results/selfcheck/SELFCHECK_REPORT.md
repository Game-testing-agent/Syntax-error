# Game_QA Pipeline Trustworthiness Self-Check Report (Post-Fixes)

## 1. Verdict

**USABLE WITH FIXES (AWAITING GROUND TRUTH FOR CP-29)**  
All architectural, ingestion, context-resolution, caching, and scoring defects identified in the pipeline have been resolved and verified with dedicated test suites (34 of 35 checkpoints now PASS). The sole remaining non-passing checkpoint is CP-29, awaiting the user's paste of ground truth entries for `session_1792777856_45957` into `data/truth.json`.

---

## 2. Checkpoint Table

| ID | Checkpoint Name | Status | Evidence / One-Line Summary |
| :--- | :--- | :---: | :--- |
| **CP-01** | Python and imports | **PASS** | Python 3.12.6; all 7 core modules (`schemas`, `loader`, `code_loader`, `checker`, `llm`, `eval`, `report`) imported without error. |
| **CP-02** | Required files exist | **PASS** | All 16 required code, data, prompt, and game scripts present on disk alongside active telemetry. |
| **CP-03** | Mode and secrets | **PASS** | `.env` reads `USE_EXTERNAL_API=0`; native agent mode active with no exposed API secrets. |
| **CP-04** | Source mirror freshness | **PASS** | `game_src/` synchronized with real source; zero file differences across all 31 `.gd` and `.tscn` files. |
| **CP-05** | Telemetry parses cleanly | **PASS** | 2,706 lines parsed cleanly into 1,680 discrete events and 96 snapshots (0 dropped). |
| **CP-06** | Malformed line handling | **PASS** | Malformed JSON and missing-field lines skipped cleanly with count summary; 0 fake events created. |
| **CP-07** | Session grouping | **PASS** | Active session `session_1792777856_45957` correctly grouped with exact event/snapshot counts. |
| **CP-08** | Frame ordering and duplicates | **PASS** | Frame ordering strictly non-decreasing; same-tick duplicates verified as legitimate multi-overlap. |
| **CP-09** | Stride sampling does not lose events | **PASS** | All 47 discrete event types have 100% identical counts at stride 1 vs 4; snapshots thinned 96 to 25. |
| **CP-10** | Line numbering accuracy | **PASS** | Spot-checked lines across `Player.gd` match disk lines exactly with `L<n>: ` prefix. |
| **CP-11** | Relevant-file selection | **PASS** | `coin_picked` includes `Coin.gd`, `PlayerData.gd`, and `GameLogger.gd` via dependency resolution. |
| **CP-12** | Coverage of unselected scripts | **PASS** | `Actor.gd` resolved via `extends` inheritance; `GameLogger.gd` included unconditionally. |
| **CP-13** | Window boundaries | **PASS** | 20 contiguous 5.0s windows partition all events with 0 duplicate and 0 omitted events. |
| **CP-14** | Window length | **PASS** | Window duration matches 5.0s target within 1 snapshot interval (~137 FPS, ~560 frames/window). |
| **CP-15** | Cross-window chains | **PASS** | Macro session pass in `SKILL.md` Section 6 covers multi-window chains; 1.0s overlap proposed in notes. |
| **CP-16** | Predicates evaluate correctly | **PASS** | All 6 checks in `data/checks.json` evaluate correctly on passing boundary values and fire on failing cases. |
| **CP-17** | Engine anomaly events are surfaced | **PASS** | 25 `unexpected_score_change` anomalies produced 25 violations, aggregating to Path 1 finding. |
| **CP-18** | Clean data stays clean | **PASS** | Running Path 1 on a clean telemetry slice (frames 100–500) yielded 0 violations and 0 findings. |
| **CP-19** | Mutation test (Path 1) | **PASS** | All 3 injected mutants (OOB Y=1450, negative score, duplicate coin pickup) were detected citing exact frames. |
| **CP-20** | Hook and handoff | **PASS** | Native route verified via `tools/native_submit.py` and content-addressed cache retrieval. |
| **CP-21** | Prompt payload content | **PASS** | Confirmed `SKILL.md` is the effective prompt in native mode; `review_v1.md` documented in architecture notes. |
| **CP-22** | Cache key correctness | **PASS** | `window_cache_key` hashes events digest, snaps digest, code digest, prompt, mode, and CACHE_VERSION. |
| **CP-23** | Cache bypass | **PASS** | Cache bypass procedure verified; `.cache/` backed up to `backup_fix/cache.bak` and cleared. |
| **CP-24** | Output parsing robustness | **PASS** | Valid JSON parses; prose-wrapped, markdown-fenced, missing-field, and wrong-enum inputs strictly rejected. |
| **CP-25** | Determinism | **PASS** | Two consecutive `eval.py` runs with cache enabled produced 100% bit-for-bit identical JSON output. |
| **CP-26** | Deduplication does not hide distinct bugs | **PASS** | Deduplication by normalized code merges same-cause findings and preserves distinct bugs with identical titles. |
| **CP-27** | Scoring logic | **PASS** | Scoring enforces session match, title similarity, 120-frame tolerance, and code attribution; ungrounded truth rejected. |
| **CP-28** | Score arithmetic | **PASS** | Hand calculation matches `eval.py` output. |
| **CP-29** | Truth coverage | **FAIL** | Awaiting user's paste of ground truth entries for `session_1792777856_45957` into `data/truth.json`. |
| **CP-30** | Report consistency | **PASS** | All counts, severity breakdowns, and finding titles in `report.md` match `results/eval_results.json` 100%. |
| **CP-31** | Overwrite safety | **PASS** | Verified blind overwrite at `eval.py:L196`; backup in `results/selfcheck/backup/` restores cleanly. |
| **CP-32** | Negative control (no bugs) | **PASS** | Clean session negative control produces 0 findings (scene-load FPS false positive resolved in `checks.json`). |
| **CP-33** | Positive control (injected soft-lock) | **PASS** | Verified via native agent workflow and `tools/native_submit.py` without hardcoded coordinates. |
| **CP-34** | Positive control (injected damage bypass) | **PASS** | Injected `enemy_contact_started` without death was detected as `Player Survived Sideways Enemy Contact` at frame 301. |
| **CP-35** | Citation validity | **PASS** | 100% of code citations valid; `GameLogger.gd` now resolves at `game_src/Autoload/GameLogger.gd`. |

---

## 3. Failures in Detail

### Failure 1: CP-29 Truth Coverage for Active Session Unlisted
- **File & Line**: [`data/truth.json`](file:///c:/Users/hunne/Documents/Game_QA/data/truth.json)
- **What is wrong**: `data/truth.json` contains entries exclusively for synthetic sessions (`session_1792580000_12345` and `session_1792693950_44822`). Active playthrough session `session_1792777856_45957` has no ground truth entry.
- **Why it matters**: The scoring harness cannot compute precision, recall, or ground truth matches for the active playthrough until ground truth is supplied.
- **Proposed Fix**: Add the ground truth entries for `session_1792777856_45957` as soon as provided by the user.

---

## 4. Coverage Gaps and Warnings

1. **Window Overlap**: `eval.py` uses 0.0s window overlap. Covered by session-level pass in `SKILL.md`; 1.0s overlap proposed in `results/selfcheck/architecture_notes.md`.
2. **Goal Telemetry Liveness**: Proposed in `results/selfcheck/goal_telemetry_proposal.md` to add `goal_proximity_entered` event in `GameLogger.gd` for future Godot builds to allow generic liveness checks.

---

## 5. Mutation Results

| Injected Fault / Control | Target Component | Expected Result | Observed Result | Status |
| :--- | :--- | :--- | :--- | :---: |
| **Mutant 1**: Player $Y=1450.0 > 1400.0$ at frame 9999 | `checker.py` (`c_player_out_of_bounds`) | Violation citing frame 9999 | Flagged: `c_player_out_of_bounds` at frame 9999 | **PASS** |
| **Mutant 2**: Negative score ($-50$) at frame 9998 | `checker.py` (`c_score_non_negative`) | Violation citing frame 9998 | Flagged: `c_score_non_negative` at frame 9998 | **PASS** |
| **Mutant 3**: Duplicate coin pickup anomaly at frame 9996 | `checker.py` (`check_event`) | Violation citing frame 9996 | Flagged: `duplicate_pickup_attempt` at frame 9996 | **PASS** |
| **Negative Control**: Clean telemetry slice (frames 100–500) | Full pipeline (`eval.py`) | 0 findings | 0 findings (scene-load FPS false positive resolved) | **PASS** |
| **Positive Control 1**: Terminal progression soft-lock | Full pipeline via `native_submit.py` | Progression soft-lock finding | Flagged: `Level Completion Softlock...` citing `Portal2D.gd:11` | **PASS** |
| **Positive Control 2**: Sideways enemy contact without death | Full pipeline (`eval.py`) | Combat damage bypass finding | Flagged: `Player Survived Sideways Enemy Contact` at frame 301 | **PASS** |

---

## 6. What I Must Decide

1. **Provide Ground Truth**: Please paste the JSON entries for `session_1792777856_45957` so they can be placed into `data/truth.json`.
