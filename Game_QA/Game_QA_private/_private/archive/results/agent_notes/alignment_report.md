# Pipeline Alignment Report (Phase 1: Read-Only Analysis)

## 1. Prompt Loading Verification (`prompts/review_v1.md`)

- **Code Loading Location**:
  `prompts/review_v1.md` is loaded at exactly **one** location:
  - [`llm.py:L241-L242`](file:///c:/Users/hunne/Documents/Game_QA/llm.py#L241-L242):
    ```python
    prompt_file = Path(__file__).parent / "prompts" / "review_v1.md"
    prompt_digest = hashlib.sha256(prompt_file.read_bytes()).hexdigest() if prompt_file.exists() else "no-prompt"
    ```
  It is read strictly as raw bytes to compute `prompt_digest` for the content-addressed cache key.

- **Actual Prompt Used per Mode**:
  - **Native Mode (`USE_EXTERNAL_API=0`)**:
    The active prompt guiding the white-box QA audit is [`.agents/skills/game-qa/SKILL.md`](file:///c:/Users/hunne/Documents/Game_QA/.agents/skills/game-qa/SKILL.md) (the Antigravity agent system skill). `prompts/review_v1.md` is **not** sent as an instruction prompt to an LLM; only its SHA-256 byte digest is hashed into the cache key.
  - **External API Mode (`USE_EXTERNAL_API=1`)**:
    External API calling is **not implemented** in `llm.py`. Neither `eval.py` nor `llm.py` contains API request handling (e.g. OpenAI/Groq/Gemini client calls). In external mode, `llm.py` falls back to `_audit_window_semantics()` without using any prompt.

---

## 2. Window Context Injection in `code_loader.py`

- **Selection Logic**:
  [`code_loader.py:get_game_codebase_context()`](file:///c:/Users/hunne/Documents/Game_QA/code_loader.py#L71) scans discrete events in the review window:
  - Categories `enemy`, `player_lifecycle`, `player_movement` &rarr; adds `Player.gd`, `Enemy.gd`
  - Category `collectible` or `coin` in event name &rarr; adds `Coin.gd`
  - Category `portal` or `scene` in event name &rarr; adds `Portal2D.gd`
  - Event contains `score` or `death` &rarr; adds `PlayerData.gd`
  - Expands base classes via regex `extends <Class>` (`Actor.gd` for `Player.gd` and `Enemy.gd`) and autoload references (`PlayerData.gd`, `GameLogger.gd`).
  - Always appends `GameLogger.gd`.
  - Priority sort: `["Player.gd", "Enemy.gd", "Coin.gd", "Portal2D.gd", "Actor.gd", "PlayerData.gd", "GameLogger.gd"]`.
  - Budget cap: `max_lines = 500`. Truncates remaining scripts once line budget is reached.

- **`.tscn` Scene File Inclusion**:
  **None**. [`code_loader.py:L80`](file:///c:/Users/hunne/Documents/Game_QA/code_loader.py#L80) searches strictly for `*.gd`:
  ```python
  file_map = {p.name: p for p in src_dir.rglob("*.gd")}
  ```
  No `.tscn` text is ever read or provided to the window context.

- **Files in `game_src/` NEVER Included in Any Window Type**:
  - **8 `.gd` Scripts**:
    1. `Screens/EndScreen.gd` (12 lines)
    2. `UserInterface/UserInterface.gd` (66 lines)
    3. `UserInterface/RetryButton.gd` (14 lines)
    4. `UserInterface/QuitButton.gd` (7 lines)
    5. `UserInterface/SceneChangeButton.gd` (20 lines)
    6. `Tests/test_fault_injection.gd` (184 lines)
    7. `Tests/test_gameplay_flow.gd` (151 lines)
    8. `Tests/test_logger_suite.gd` (272 lines)
  - **All 16 `.tscn` Scene Files**:
    `Actors/Enemy.tscn`, `Actors/Player.tscn`, `Autoload/PlayerData.tscn`, `Levels/Level01.tscn`, `Levels/Level02.tscn`, `Levels/LevelTemplate.tscn`, `Objects/Bumper.tscn`, `Objects/Coin.tscn`, `Objects/Portal2D.tscn`, `Screens/EndScreen.tscn`, `Screens/MainScreen.tscn`, `UserInterface/QuitButton.tscn`, `UserInterface/RetryButton.tscn`, `UserInterface/SceneChangeButton.tscn`, `UserInterface/Title.tscn`, `UserInterface/UserInterface.tscn`.

- **Source Size Metrics**:
  - All 15 `.gd` files total: **2,418 lines** (83,225 characters).
  - Production game scripts only (excluding 3 test suite `.gd` files): **1,811 lines** (58,785 characters).

---

## 3. Exact Fields Hashed in `llm.window_cache_key`

In [`llm.py:window_cache_key()`](file:///c:/Users/hunne/Documents/Game_QA/llm.py#L232-L255):
```python
payload = {
    "version": CACHE_VERSION,
    "session_id": window.session_id,
    "window_id": window.window_id,
    "events_digest": events_digest,
    "snaps_digest": snaps_digest,
    "code_digest": code_digest,
    "prompt_digest": prompt_digest,
    "evaluator_mode": get_llm_status(),
}
return _cache_key("audit", json.dumps(payload, sort_keys=True))
```
1. `version`: String `"v2"` (`CACHE_VERSION`).
2. `session_id`: String (e.g. `"session_1792788454_15318"`).
3. `window_id`: String (e.g. `"w00"`).
4. `events_digest`: SHA-256 hex digest of `json.dumps([e.model_dump() for e in window.events], sort_keys=True)`.
5. `snaps_digest`: SHA-256 hex digest of `json.dumps([s.model_dump() for s in window.snapshots], sort_keys=True)`.
6. `code_digest`: SHA-256 hex digest of the UTF-8 `code_context` string.
7. `prompt_digest`: SHA-256 hex digest of the raw bytes of `prompts/review_v1.md` (or `"no-prompt"`).
8. `evaluator_mode`: String `"ACTIVE: Antigravity AI Agent (Skill: game-qa)"` from `get_llm_status()`.

The output filename is `audit_<hash>.json`, where `<hash>` is the first 32 characters of `SHA256("audit" + json.dumps(payload, sort_keys=True))`.

---

## 4. Search for Leaked Concrete Bug Values & Defect Claims

Files scanned: `prompts/**`, `.agents/skills/game-qa/SKILL.md`, `llm.py`, `eval.py`, `checker.py`, `code_loader.py`, `game_src/**`.

### A. Prompts Directory (`prompts/review_v1.md`)
- **`prompts/review_v1.md:L44`**: Cites specific defect line:
  `In suspected_code, cite the exact file name and line number or function (e.g. Player.gd:L76 or Portal2D.gd:L29)`
  *(Note: Line 76 of `Player.gd` is the exact line of the Enemy4 damage exemption bug).*
- **`prompts/review_v1.md:L60`**: Cites specific defect lines:
  `suspected_code: string like "Enemy.gd:L30" or "Portal2D.gd:L14" or null`
  *(Note: Line 30 of `Enemy.gd` is the exact line of the wall reversal freeze bug; Line 14 of `Portal2D.gd` is `_on_body_entered`).*
- **`prompts/review_v1.md:L63`**: Concrete leak in the illustrative example containing exact telemetry frames, defect title, and file:line from the game:
  ```json
  {"verdict": "bug", "severity": "critical", "confidence": 0.90, "title": "Level Not Completed (Player Reached End Without Portal Trigger)", "explanation": "Player cleared all level objectives and reached the exit portal coordinates at frame 12722, but no portal_entered or level_completed event was emitted, and goal.found remained false. The game failed to transition scenes, leaving the player stranded.", "evidence_frames": [5695, 12722, 13285], "suspected_code": "Portal2D.gd:L14 (_on_body_entered)"}
  ```
  *(Leaked: Frames `5695`, `12722`, `13285`, coordinate claims, and `Portal2D.gd:L14`).*

### B. Heuristic Evaluator (`llm.py`)
- **`llm.py:L54`**: Hardcoded coordinate threshold: `OUT_OF_BOUNDS_Y = 1400.0`.
- **`llm.py:L69-L76`**: Hardcoded `code_map` with exact defect line numbers:
  - `L69`: `"player_out_of_bounds": "Player.gd:L176 (OUT_OF_BOUNDS_Y)"`
  - `L70`: `"duplicate_pickup_attempt": "Coin.gd:L27 (_on_body_entered)"`
  - `L71`: `"unexpected_score_change": "PlayerData.gd:L36 (set_score)"`
  - `L72`: `"missing_expected_object": "Portal2D.gd:L35 (teleport)"`
  - `L73`: `"scene_transition_timeout": "Portal2D.gd:L53 (GameLogger.is_scene_transitioning)"`
  - `L74`: `"runtime_error_observed": "Portal2D.gd:L92 (change_scene_to_packed)"`
  - `L75`: `"player_stuck_detected": "Player.gd:L105 (move_and_slide)"`
  - `L76`: `"unexpected_player_removal": "Player.gd:L43 (_exit_tree)"`
- **`llm.py:L114`**: Comment naming specific defect: `# 3. Threat Enemy Contact Without Damage/Death (Godmode or Enemy4 Bug)`.
- **`llm.py:L126`**: Concrete defect lines: `f"Root cause in Player.gd:_on_EnemyDetector_body_entered (line L73 is_invincible check or line L76 Enemy4 exemption)."`
- **`llm.py:L129`**: Suspected code: `"Player.gd:L73-L77 (_on_EnemyDetector_body_entered)"`.
- **`llm.py:L147`**: Suspected code: `"Enemy.gd:L30 (_physics_process: is_on_wall)"`.
- **`llm.py:L186-L191`**: `OUT_OF_BOUNDS_Y = 1400.0` and `suspected_code="Player.gd:L176 (OUT_OF_BOUNDS_Y) / Player.gd:L4 (is_invincible)"`.
- **`llm.py:L221`**: Suspected code: `"Enemy.gd:L30 (_physics_process: is_on_wall)"`.

### C. Game Source Code Comments (`game_src/**`)
- **`game_src/Actors/Enemy.gd:L6`**: `# [TEMPORARY BUG 1 TOGGLE] High-speed stomp tunneling miss`
- **`game_src/Actors/Enemy.gd:L51-L56`**: `# TRICKY BUG 1: Stomp Tunneling Miss on Fast Descent \n # When falling at high downward speed (> 500 px/s)... Shifting the threshold causes stomps at terminal fall speeds to bypass die()`
- **`game_src/Actors/Player.gd:L4`**: `# TEMPORARY: God mode (set to false to re-enable death)`
- **`game_src/Actors/Player.gd:L5`**: `# [TEMPORARY BUG 2 TOGGLE] Wall-friction jump dampening`
- **`game_src/Actors/Player.gd:L77`**: `# Bug: 4th enemy cannot kill the player`
- **`game_src/Actors/Player.gd:L224-L226`**: `# TRICKY BUG 2: Wall-Friction Jump Dampening \n # Pressing towards a wall during ascent dampens upward impulse by 35%...`
- **`game_src/Autoload/PlayerData.gd:L10`**: `# [TEMPORARY BUG 4 TOGGLE] Milestone score regression`
- **`game_src/Autoload/PlayerData.gd:L36-L39`**: `# TRICKY BUG 4: Milestone Score Regression \n # On collecting subsequent collectibles after reaching or exceeding 500 points, an erroneous tier-adjustment logic applies a -10 deduction...`
- **`game_src/Objects/Coin.gd:L5`**: `# [TEMPORARY BUG 3 TOGGLE] Deferred collision pickup race condition`
- **`game_src/Objects/Coin.gd:L37-L39`**: `# TRICKY BUG 3: Sub-Frame Multi-Pickup Collision Race \n # When moving through a coin at sprint speed (> 300 px/s)...`
- **`game_src/Objects/Portal2D.gd:L7`**: `# [TEMPORARY BUG 5 TOGGLE] Unpaused physics fall during airborne portal transition`
- **`game_src/Objects/Portal2D.gd:L61-L64`**: `# TRICKY BUG 5: Airborne Portal Transition Fall-Through \n # If the player touches the portal while airborne and moving downward, pausing the scene tree is skipped...`

### D. Skill Instructions (`.agents/skills/game-qa/SKILL.md`)
- **Lines 212–215 & 224**:
  The example in `SKILL.md` is **clean/fictional**: it refers to fictional components (`Hud.gd:L22-L30`, `GameState.gd:L15`, `lives_changed`, frames `940`, `1500`, `2210`) that do not exist in the game. It contains no leaks of real game code, frames, or coordinates.

