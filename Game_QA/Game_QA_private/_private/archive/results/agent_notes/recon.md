# Phase A Reconnaissance Notes

## 1. Telemetry Log Path
`loader.py:resolve_log_path()` resolves to:
`C:\Users\hunne\Documents\Syntax-error\game_events.jsonl`

## 2. Model Configured in `.env`
`.env` specifies:
`USE_EXTERNAL_API=0`
No external model or API keys are active; external keys (`GROQ_API_KEY`, `GEMINI_API_KEY`, etc.) are commented out. The pipeline runs in native Antigravity AI Agent mode with white-box heuristic triage fallback in `llm.py`.

## 3. Window Size and Stride
- **Window size**: `5.0` seconds (defined in `eval.py:run_evaluation(window_sec=5.0)` / `ReviewWindow`).
- **Stride**: `4` (defined in `run_eval.bat` and `eval.py:main(stride=4)`). Stride 4 samples the 1st snapshot, then multiples of 4 (4, 8, 12, ...), while preserving 100% of discrete events.

## 4. Matching Rules in `eval.py`
`eval.py:score_session()` matches agent/eval findings 1-to-1 against truth:
1. **Verdict Filter**: Only findings with `verdict == Verdict.bug` are eligible; `unsure` and `not_a_bug` are never counted as hits.
2. **Title/Category Similarity**: `norm_exp_title in norm_f_title or norm_f_title in norm_exp_title or (bool(exp_cat) and exp_cat in norm_f_title)`. (Explanation substring matching was removed).
3. **Evidence Grounding**: Must satisfy at least one of:
   - **Frame Proximity**: Finding evidence frame within `FRAME_TOLERANCE_FRAMES = 120` frames of any truth frame (`abs(ff - tf) <= 120`).
   - **Code Match**: Suspected code file matches normalized truth filename, and if truth function is specified, finding function matches.
4. **False Positives**: Any finding not consumed in a 1-to-1 match is scored as a false positive.
5. **Truth Refusal Rule**: A truth entry lacking both `evidence_frames` (or `frame_approx`) and `suspected_code` raises a `ValueError` refusing to score.

## 5. Source Files in `game_src/` with Line Counts
Total files: 31 (15 GDScript files, 16 Scene/Resource files).
- `Actors\Actor.gd`: 10 lines
- `Actors\Enemy.gd`: 92 lines
- `Actors\Enemy.tscn`: 43 lines
- `Actors\Player.gd`: 247 lines
- `Actors\Player.tscn`: 59 lines
- `Autoload\GameLogger.gd`: 1056 lines
- `Autoload\PlayerData.gd`: 69 lines
- `Autoload\PlayerData.tscn`: 8 lines
- `Levels\Level01.tscn`: 137 lines
- `Levels\Level02.tscn`: 123 lines
- `Levels\LevelTemplate.tscn`: 45 lines
- `Objects\Bumper.tscn`: 19 lines
- `Objects\Coin.gd`: 87 lines
- `Objects\Coin.tscn`: 108 lines
- `Objects\Portal2D.gd`: 131 lines
- `Objects\Portal2D.tscn`: 78 lines
- `Screens\EndScreen.gd`: 12 lines
- `Screens\EndScreen.tscn`: 81 lines
- `Screens\MainScreen.tscn`: 59 lines
- `Tests\test_fault_injection.gd`: 184 lines
- `Tests\test_gameplay_flow.gd`: 151 lines
- `Tests\test_logger_suite.gd`: 272 lines
- `UserInterface\QuitButton.gd`: 7 lines
- `UserInterface\QuitButton.tscn`: 14 lines
- `UserInterface\RetryButton.gd`: 14 lines
- `UserInterface\RetryButton.tscn`: 11 lines
- `UserInterface\SceneChangeButton.gd`: 20 lines
- `UserInterface\SceneChangeButton.tscn`: 10 lines
- `UserInterface\Title.tscn`: 13 lines
- `UserInterface\UserInterface.gd`: 66 lines
- `UserInterface\UserInterface.tscn`: 77 lines

## 6. How `.cache/` Caching Works in `llm.py`
- **Cache Key Computation**: `window_cache_key(window, code_context)` computes SHA256 digests over:
  - Canonical JSON dump of all `Event` objects in the review window.
  - Canonical JSON dump of all `Snapshot` objects in the review window.
  - The annotated GDScript code context string with line numbers.
  - Content of `prompts/review_v1.md`.
  - Evaluator mode string, cache version (`v2`), `session_id`, and `window_id`.
  The digest is saved as `.cache/audit_<sha256[:32]>.json`.
- **Hit Behavior**: `review_window()` checks if the cache file exists. If so, loads it into a `Finding`. If `verdict == Verdict.bug`, it returns the cached finding directly without re-evaluation. On cache miss, it runs heuristic triage and caches any returned finding.

## 7. Number of Checks in `data/checks.json`
`data/checks.json` contains exactly **6** invariant checks. (`data/truth.json` was NOT accessed).

## 8. Total Lines in Telemetry File
`C:\Users\hunne\Documents\Syntax-error\game_events.jsonl` contains **2,706** non-empty lines:
- Session `session_1792777856_45957`: 1,680 events + 96 snapshots = 1,776 lines.
- Session `session_792785118_99684` (`session_1792785118_99684`): 874 events + 56 snapshots = 930 lines.
- Total parsed: 2,554 events + 152 snapshots = 2,706 lines (0 malformed/skipped).
