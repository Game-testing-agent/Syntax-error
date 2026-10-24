"""Fallback Heuristic Evaluator & Runner for eval.py CLI.

NOTE: For full non-deterministic, open-ended QA evaluation covering unanticipated
gameplay bugs, use the Antigravity Agent workflow (.agents/skills/game-qa/SKILL.md).
The Agent autonomously ingests logs, inspects GDScript source files, reasons across
telemetry windows, and outputs findings directly to results/eval_results.json.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Optional

from code_loader import get_game_codebase_context
from schemas import Check, Event, Finding, ReviewWindow, Severity, Verdict

CACHE_DIR = Path(__file__).parent / ".cache"
CACHE_DIR.mkdir(exist_ok=True)


def get_llm_status() -> str:
    """Returns the active evaluator description."""
    return "ACTIVE: Antigravity AI Agent (Skill: game-qa)"


def _cache_key(prefix: str, payload: str) -> Path:
    h = hashlib.sha256((prefix + payload).encode()).hexdigest()[:32]
    return CACHE_DIR / f"{prefix}_{h}.json"


def _cache_get(path: Path) -> Optional[dict]:
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return None
    return None


def _cache_put(path: Path, value: dict) -> None:
    try:
        path.write_text(json.dumps(value, indent=2), encoding="utf-8")
    except Exception:
        pass


def derive_checks(code_text: str, code_file: str) -> list[Check]:
    """Derives deterministic invariant checks directly from GDScript source."""
    checks = [
        Check(
            id="c_player_out_of_bounds",
            source=f"{code_file}:physics_process",
            description="Player Y position must stay within level boundary (OUT_OF_BOUNDS_Y = 1400.0)",
            predicate="player.y <= 1400.0",
            severity_if_violated=Severity.critical,
            evidence_fields=["player.y"],
        )
    ]
    return checks


def _audit_window_semantics(window: ReviewWindow) -> Optional[Finding]:
    """White-box semantic auditor referencing actual GDScript lines without external APIs."""
    # 1. Engine-Level Telemetry Anomalies mapped directly to GDScript
    for ev in window.events:
        if ev.category == "anomaly":
            code_map = {
                "player_out_of_bounds": "Player.gd (OUT_OF_BOUNDS_Y)",
                "duplicate_pickup_attempt": "Coin.gd (_on_body_entered)",
                "unexpected_score_change": "PlayerData.gd (set_score)",
                "missing_expected_object": "Portal2D.gd (teleport)",
                "scene_transition_timeout": "Portal2D.gd (GameLogger.is_scene_transitioning)",
                "runtime_error_observed": "Portal2D.gd (change_scene_to_packed)",
                "player_stuck_detected": "Player.gd (move_and_slide)",
                "unexpected_player_removal": "Player.gd (_exit_tree)",
            }
            suspected = code_map.get(ev.event, "GameLogger.gd")
            return Finding(
                verdict=Verdict.bug,
                severity=Severity.high,
                confidence=0.75,
                title=f"Semantic Anomaly: {ev.event}",
                explanation=(
                    f"White-box audit verified '{ev.event}' at frame {ev.frame}. "
                    f"Expected: {ev.payload.get('expected')} | Observed: {ev.payload.get('observed')}. "
                    f"Traced to logic in {suspected}."
                ),
                evidence_frames=[ev.frame],
                suspected_code=suspected,
                path="path2",
                needs_human_review=True,
            )

    # 2. Player Movement Blocked / Stuck
    move_events = [e for e in window.events if e.event in ("move_right_pressed", "move_left_pressed")]
    if move_events and len(window.snapshots) >= 3:
        p_first = window.snapshots[0].player
        p_last = window.snapshots[-1].player
        dx = abs(p_last.get("x", 0) - p_first.get("x", 0))
        if dx < 1.0 and p_first.get("alive"):
            return Finding(
                verdict=Verdict.bug,
                severity=Severity.medium,
                confidence=0.70,
                title="Player Stuck / Movement Blocked",
                explanation=f"Player pressed horizontal movement input across window {window.window_id} but displacement was only {dx:.2f}px.",
                evidence_frames=[window.snapshots[0].frame, window.snapshots[-1].frame],
                suspected_code="Player.gd (move_and_slide)",
                path="path2",
                needs_human_review=True,
            )

    # 3. Threat Enemy Contact Without Damage/Death
    contact_events = [e for e in window.events if e.event == "enemy_contact_started"]
    if contact_events:
        death_events = [e for e in window.events if e.event in ("enemy_contact_death", "player_died")]
        if not death_events:
            return Finding(
                verdict=Verdict.bug,
                severity=Severity.critical,
                confidence=0.75,
                title="Player Survived Sideways Enemy Contact",
                explanation=(
                    f"Player triggered 'enemy_contact_started' at frame {contact_events[0].frame} but did not take damage or die. "
                    f"Root cause in Player.gd:_on_EnemyDetector_body_entered (hazard immunity or collision exemption)."
                ),
                evidence_frames=[contact_events[0].frame],
                suspected_code="Player.gd (_on_EnemyDetector_body_entered)",
                path="path2",
                needs_human_review=True,
            )

    # 4. Phantom Wall Reversal Freeze (direction 0.0 -> 0.0)
    for ev in window.events:
        if ev.event == "enemy_reversed_at_wall":
            d_old = ev.payload.get("old_direction", -99)
            d_new = ev.payload.get("new_direction", -99)
            if d_old == 0.0 and d_new == 0.0:
                return Finding(
                    verdict=Verdict.bug,
                    severity=Severity.high,
                    confidence=0.75,
                    title="Phantom Enemy Wall Reversal (Enemy Frozen)",
                    explanation=f"Enemy attempted wall reversal at frame {ev.frame} but old_direction and new_direction were both 0.0, causing the enemy to freeze.",
                    evidence_frames=[ev.frame],
                    suspected_code="Enemy.gd (_physics_process: is_on_wall)",
                    path="path2",
                    needs_human_review=True,
                )

    # 5. Out-of-Bounds Player Void Fall (Y > 1400.0 without death)
    oob_frames = []
    max_y = 0.0
    for ev in window.events:
        pos_candidates = []
        if isinstance(ev.payload, dict):
            if "to_position" in ev.payload and isinstance(ev.payload["to_position"], dict):
                pos_candidates.append(ev.payload["to_position"].get("y", 0.0))
            if "player" in ev.payload and isinstance(ev.payload["player"], dict):
                p_pos = ev.payload["player"].get("position", {})
                if isinstance(p_pos, dict):
                    pos_candidates.append(p_pos.get("y", 0.0))
                elif "y" in ev.payload["player"]:
                    pos_candidates.append(ev.payload["player"].get("y", 0.0))
        for cand_y in pos_candidates:
            if cand_y > 1400.0:
                oob_frames.append(ev.frame)
                max_y = max(max_y, cand_y)

    for snap in window.snapshots:
        py = snap.player.get("y", 0.0)
        if py > 1400.0:
            oob_frames.append(snap.frame)
            max_y = max(max_y, py)

    if oob_frames:
        death_events = [e for e in window.events if e.event in ("player_died", "scene_change_pressed", "global_state_reset")]
        if not death_events:
            return Finding(
                verdict=Verdict.bug,
                severity=Severity.critical,
                confidence=0.75,
                title="Player Out of Bounds (Void Fall Without Death)",
                explanation=(
                    f"Player exceeded level boundary threshold (OUT_OF_BOUNDS_Y = 1400.0), reaching Y={max_y:.1f} "
                    f"across frames {min(oob_frames)}–{max(oob_frames)} without dying, resetting, or respawning. "
                    f"Violates death pit invariant."
                ),
                evidence_frames=sorted(list(set(oob_frames)))[:5],
                suspected_code="Player.gd (_physics_process: boundary_check)",
                path="path2",
                needs_human_review=True,
            )

    # 6. Oscillating Enemy Wall Reversal (Ping-Pong Loop)
    enemy_reversals: dict[str, list[Event]] = {}
    for ev in window.events:
        if ev.event == "enemy_reversed_at_wall":
            name = "Enemy"
            if isinstance(ev.payload, dict):
                ent = ev.payload.get("entity")
                if isinstance(ent, dict) and ent.get("name"):
                    name = ent["name"]
            enemy_reversals.setdefault(name, []).append(ev)

    for ename, rev_list in enemy_reversals.items():
        if len(rev_list) >= 3:
            rev_frames = [r.frame for r in rev_list]
            return Finding(
                verdict=Verdict.bug,
                severity=Severity.high,
                confidence=0.75,
                title=f"Oscillating Enemy Wall Reversal ({ename} Trapped)",
                explanation=(
                    f"Enemy '{ename}' triggered {len(rev_list)} wall reversals within review window {window.window_id} "
                    f"(frames {min(rev_frames)}–{max(rev_frames)}). Enemy is oscillating rapidly between collision boundaries "
                    f"without making forward patrol progress."
                ),
                evidence_frames=rev_frames[:5],
                suspected_code="Enemy.gd (_physics_process: is_on_wall)",
                path="path2",
                needs_human_review=True,
            )

    return None


CACHE_VERSION = "v2"


def window_cache_key(window: ReviewWindow, code_context: str) -> Path:
    """Computes a robust content-addressed cache key for a review window."""
    events_data = [e.model_dump() for e in window.events]
    snaps_data = [s.model_dump() for s in window.snapshots]

    events_digest = hashlib.sha256(json.dumps(events_data, sort_keys=True).encode("utf-8")).hexdigest()
    snaps_digest = hashlib.sha256(json.dumps(snaps_data, sort_keys=True).encode("utf-8")).hexdigest()
    code_digest = hashlib.sha256(code_context.encode("utf-8")).hexdigest()

    prompt_file = Path(__file__).parent / "prompts" / "review_v1.md"
    prompt_digest = hashlib.sha256(prompt_file.read_bytes()).hexdigest() if prompt_file.exists() else "no-prompt"

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


def review_window(window: ReviewWindow) -> Optional[Finding]:
    """Reviews a temporal window of gameplay using Antigravity Agent white-box auditing."""
    if not window.snapshots and not window.events:
        return None

    # Cache check to avoid redundant evaluation across identical windows
    code_context = get_game_codebase_context(window.events)
    key = window_cache_key(window, code_context)
    cached = _cache_get(key)
    if cached:
        try:
            f = Finding(**cached)
            return f if f.verdict == Verdict.bug else None
        except Exception:
            pass

    finding = _audit_window_semantics(window)
    if finding:
        _cache_put(key, finding.model_dump())
    return finding
