# Pipeline Fix Log

## Fix F1: Sync the source mirror
- **Fix ID**: F1 (fixes CP-04, CP-35)
- **Files Changed**: `game_src/**` (copied 15 `.gd` files and 16 `.tscn` files from `..\Syntax-error\godot-4game\src\`, backed up to `results/selfcheck/backup_fix/game_src_initial`)
- **Test Before / After**: `tests/selfcheck/test_f1_verify.py` before: 6 differing files, 9 missing files (FAIL); after: 0 diffs, CP-10 spot check PASS, `GameLogger.gd` resolution PASS
- **Evidence**: `test_f1_verify.py` output: 0 differences between `game_src` and real source; CP-35 invalid citation resolved (`GameLogger.gd` now exists at `game_src/Autoload/GameLogger.gd`); gate: 0 `suspected_code` line references in `data/truth.json` changed
- **Open Issues**: `code_loader.py` still uses hardcoded file discovery for review windows; unselected scripts to be addressed in F8

## Fix F2: Stride must only thin snapshots
- **Fix ID**: F2 (fixes CP-09)
- **Files Changed**: `loader.py` (backed up to `results/selfcheck/backup_fix/loader.py.bak`)
- **Test Before / After**: `tests/selfcheck/test_f2_stride.py` before: 43 mismatched event types, critical events count@4 = 0 (FAIL); after: 0 mismatches, all 47 event types identical count@1 vs count@4, snapshots 96 -> 25 (PASS)
- **Evidence**: `tests/selfcheck/print_f2_table.py` table verified all 47 discrete event types (`player_died`: 3/3, `enemy_stomped`: 1/1, `scene_change_pressed`: 1/1) preserved across stride 4; snapshots thinned 96 to 25
- **Open Issues**: Malformed record handling in `loader.py` to be addressed next in F3

## Fix F3: Reject malformed records instead of inventing events
- **Fix ID**: F3 (fixes CP-06)
- **Files Changed**: `loader.py`
- **Test Before / After**: `tests/selfcheck/test_f3_malformed.py` before: `Fake sessions created: ['default_session']` (FAIL); after: 3 malformed records skipped, 0 fake sessions created, real telemetry unchanged at 1680 events and 96 snapshots (PASS)
- **Evidence**: `test_f3_malformed.py` and `test_cp06.py` verified malformed JSON and missing-field records are skipped with summary `[loader] Skipped N malformed record(s)`
- **Open Issues**: None

## Fix F4: Cache key correctness and native handoff
- **Fix ID**: F4 (fixes CP-22, CP-20 risk)
- **Files Changed**: `llm.py` (backed up to `results/selfcheck/backup_fix/llm.py.bak`), created `tools/native_submit.py`
- **Test Before / After**: `tests/selfcheck/test_f4_cache.py` before: `window_cache_key` missing (FAIL); `tests/selfcheck/test_f4_verify.py` after: event payload mutation changes key (PASS), source code edit changes key (PASS), `native_submit.py` tool submission retrieves finding cleanly (PASS)
- **Evidence**: `test_f4_verify.py` passed all 3 assertions; content-addressed caching verified
- **Open Issues**: Waiting on user approval to back up and clear `.cache/` (old v1 cache entries invalid)

## Fix F5: Scoring must check evidence, not title text
- **Fix ID**: F5 (fixes CP-27, CP-29)
- **Files Changed**: None yet (proposal created at `results/selfcheck/scoring_proposal.md`)
- **Test Before / After**: Pending user ground truth enrichment and proposal approval
- **Evidence**: Inspected `data/truth.json`; confirmed entries only contain `title` and `should_be_caught_by` (lacking `frames`, `suspected_code`, and `severity`), and session `session_1792777856_45957` is unlisted
- **Open Issues**: STOPPED per rule F5.3: awaiting user approval for proposal and ground truth enrichment for `session_1792777856_45957`


## Fix F5: Scoring must check evidence, not title text
- **Fix ID**: F5 (fixes CP-27, CP-29)
- **Files Changed**: `eval.py` (backed up to `results/selfcheck/backup_fix/eval.py.bak`), proposal at `results/selfcheck/scoring_proposal.md`
- **Test Before / After**: `tests/selfcheck/test_f5_scoring.py` before: ungrounded truth accepted without refusal (FAIL); `tests/selfcheck/test_f5_verify.py` after: all 6 conditions pass (perfect match, wrong frames rejected, nonsense -> FP, unsure -> rejected, ungrounded truth -> ValueError, 1-to-1 matching enforced)
- **Evidence**: `test_f5_verify.py` passed all assertions; explanation-substring matching completely eliminated
- **Open Issues**: Awaiting user's paste of ground truth entries for `session_1792777856_45957` into `data/truth.json`

## Fix F6: Deduplicate by root cause, not by title
- **Fix ID**: F6 (fixes CP-26)
- **Files Changed**: `eval.py`
- **Test Before / After**: `tests/selfcheck/test_f6_dedupe.py` before: `dedupe_finding_key` missing (FAIL); `tests/selfcheck/test_f6_verify.py` after: all 4 tests pass (same code different titles merged, same title different code kept distinct, null code falls back to title, frame union / highest severity kept)
- **Evidence**: `test_f6_verify.py` passed all assertions; distinct bugs with identical titles no longer shadow each other
- **Open Issues**: None

## Fix F7: Startup FPS false positive
- **Fix ID**: F7 (fixes CP-32)
- **Files Changed**: `data/checks.json` (backed up to `results/selfcheck/backup_fix/checks.json.bak`)
- **Test Before / After**: `tests/selfcheck/test_f7_fps.py` before: startup snapshot (2.0 FPS, `game_state='main_menu'`) flagged as violation (FAIL); after: startup silent, active gameplay low FPS (5.0 FPS, `game_state='playing'`) flagged, clean slice pipeline yields 0 findings (PASS)
- **Evidence**: `test_cp32.py` clean session full pipeline run produced 0 findings (CP-32 PASS)
- **Open Issues**: None

## Fix F8: Source-context completeness
- **Fix ID**: F8 (fixes CP-11, CP-12)
- **Files Changed**: `code_loader.py` (backed up to `results/selfcheck/backup_fix/code_loader.py.bak`)
- **Test Before / After**: `tests/selfcheck/test_f8_context.py` before: `coin_picked` lacked `PlayerData.gd`, `Player.gd` lacked `Actor.gd`, `GameLogger.gd` was missing (FAIL); after: all dependencies resolved recursively via `extends` and autoload scanning (PASS)
- **Evidence**: `test_f8_context.py` passed all 4 assertions; size budget enforced
- **Open Issues**: None

## Fix F9: Soft-lock positive control must go through the agent
- **Fix ID**: F9 (fixes CP-33 methodology)
- **Files Changed**: None in pipeline (created `tests/selfcheck/test_f9_agent_flow.py`, written proposal to `results/selfcheck/goal_telemetry_proposal.md`)
- **Test Before / After**: CP-33 previously failed because fallback heuristics lacked hardcoded coordinates; `test_f9_agent_flow.py` verifies the native agent workflow correctly identifies the progression softlock on mutated telemetry and injects it via `tools/native_submit.py`
- **Evidence**: `test_f9_agent_flow.py` produced `Level Completion Softlock Due to Missing Portal Trigger / Registration` citing `Portal2D.gd:11` and frames `[5700..5818]` in `eval_results.json`
- **Open Issues**: Goal liveness telemetry proposal documented in `results/selfcheck/goal_telemetry_proposal.md`

## Fix F10: Documentation-only items
- **Fix ID**: F10
- **Files Changed**: None (documented in `results/selfcheck/architecture_notes.md`)
- **Test Before / After**: N/A (documentation only)
- **Evidence**: Confirmed `prompts/review_v1.md` is not loaded in external API mode; clarified `SKILL.md` is the effective prompt in native mode; documented 0.0s window overlap and proposed 1.0s overlap
- **Open Issues**: None


## Fix F11: All GDScript under cap & TSCN inclusion
- **Fix ID**: F11 (Code loader context expansion)
- **Files Changed**: `code_loader.py` (backed up to `results/selfcheck/backup_fix/code_loader.py.bak2`)
- **Test Before / After**: `tests/selfcheck/test_code_loader_all_gd_tscn.py` before: only event-dependent `.gd` files included and 0 `.tscn` text included; after: all 15 `.gd` files included under 3,000 line cap (2,418 lines total), 14 referenced `.tscn` files included with `L1: ...` line numbers, and fallback tested (PASS)
- **Evidence**: `test_code_loader_all_gd_tscn.py` and `test_f8_context.py` passed all assertions; complete codebase and scene structure available in every window
- **Open Issues**: None

## Fix F12: Sanitize leaked concrete examples in prompt & LLM auditor
- **Fix ID**: F12 (Anti-leakage prompt & heuristic sanitation)
- **Files Changed**: `prompts/review_v1.md`, `llm.py` (backed up to `results/selfcheck/backup_fix/review_v1.md.bak2`, `llm.py.bak2`)
- **Test Before / After**: `tests/selfcheck/test_prompt_clean_examples.py` before: specific line numbers (`Player.gd:L76`, `L176`, `Enemy.gd:L30`, `Portal2D.gd:L14`), enemy IDs (`Enemy4`), and frame numbers (`12722`, etc.) present; after: zero leak patterns found, replaced with generic or fictional examples (PASS)
- **Evidence**: `test_prompt_clean_examples.py` passed; `eval.py`'s `_normalize_code` seamlessly normalizes function-level references without requiring hardcoded line numbers
- **Open Issues**: None

## Fix F13: Architecture notes update
- **Fix ID**: F13 (Native path, mode prompt, and cache key documentation)
- **Files Changed**: `results/selfcheck/architecture_notes.md` (backed up to `results/selfcheck/backup_fix/architecture_notes.md.bak2`)
- **Test Before / After**: `tests/selfcheck/test_architecture_notes.py` before: missing native submit documentation and cache key breakdown; after: native submission path via `tools/native_submit.py`, prompt per mode, and all 8 cache key fields documented (PASS)
- **Evidence**: `test_architecture_notes.py` passed all assertions
- **Open Issues**: None
