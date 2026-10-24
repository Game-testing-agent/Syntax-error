# Architecture Notes: Game_QA Pipeline Execution, Prompts & Caching

## 1. Native Submission Path (`tools/native_submit.py`)
- **Purpose**: Provides a dedicated, validated submission mechanism for the Antigravity Agent to inject white-box findings directly into the pipeline cache without circumventing validation schemas.
- **Workflow**:
  1. The agent inspects telemetry windows and GDScript/TSCN source according to `.agents/skills/game-qa/SKILL.md`.
  2. Findings are saved locally to a JSON file matching the `Finding` schema (`schemas.py`).
  3. The agent calls:
     ```bash
     python tools/native_submit.py --session <session_id> --window <window_id> --findings <findings_json_file>
     ```
  4. `native_submit.py` reconstructs the exact `ReviewWindow` matching `eval.py`'s temporal partition (`window_sec=5.0`, `stride=4`).
  5. It computes the content-addressed cache key via `llm.window_cache_key(target_window, code_context)`.
  6. It writes the finding to `.cache/audit_<sha256>.json` via `llm._cache_put`.
  7. When `eval.py` executes, `llm.review_window()` checks `_cache_get(cache_key)` and immediately returns the cached native finding.

## 2. Prompt Usage Per Mode
- **Native Agent Mode (`USE_EXTERNAL_API=0` or Agent Interactive Session)**:
  - The operational prompt governing the evaluation is [`.agents/skills/game-qa/SKILL.md`](file:///c:/Users/hunne/Documents/Game_QA/.agents/skills/game-qa/SKILL.md).
  - This skill defines the multi-phase audit methodology, telemetry-to-code correlation rules, invariant verification protocols, and anti-hallucination constraints.
- **External API Mode (`USE_EXTERNAL_API=1`)**:
  - `prompts/review_v1.md` is maintained as the reference prompt template for external LLM calls.
  - While live external calls are bypassed in native mode, `prompts/review_v1.md` is actively hashed into the cache key (`prompt_digest`), guaranteeing that any modifications to the prompt template automatically invalidate stale cache entries across runs.

## 3. Real Cache Key Fields (`llm.window_cache_key`)
The cache key filename is generated as `.cache/audit_<hash>.json`, where `<hash>` is the SHA-256 digest (first 32 characters) of the JSON payload containing exactly 8 serialized fields (sorted keys):
1. `version`: Pipeline cache schema version (`CACHE_VERSION = "v3"`).
2. `session_id`: Target telemetry session identifier (e.g. `session_1792777856_45957`).
3. `window_id`: Window identifier (e.g. `w00`, `w01`).
4. `events_digest`: SHA-256 hash of sorted serialized telemetry events within the window.
5. `snaps_digest`: SHA-256 hash of sorted serialized telemetry player snapshots within the window.
6. `code_digest`: SHA-256 hash of the complete code and scene context returned by `code_loader.get_game_codebase_context()`.
7. `prompt_digest`: SHA-256 hash of the raw bytes of `prompts/review_v1.md` (or `"no-prompt"` if absent).
8. `evaluator_mode`: Identifier string returned by `llm.get_llm_status()` (`ACTIVE: Antigravity AI Agent (Skill: game-qa)`).

## 4. Window Overlap & Temporal Boundaries
- **Current Windowing**: `eval.py` advances contiguous non-overlapping windows of `window_sec = 5.0` (`cur_t += window_sec`).
- **Cross-Window Chains**: Multi-window invariants (death/respawn cycles, level transitions) are tracked via the session-level audit pass outlined in `SKILL.md` Section 6.
- Optional 1.0s overlap (`stride_sec = 4.0` with `window_sec = 5.0`) remains documented as an architectural enhancement for high-frequency edge events.
