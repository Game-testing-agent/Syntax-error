"""Auditor Interface & Review Window Cache Dispatcher for Game_QA_audit.

In the audit workspace, review_window resolves findings from the validated
native cache submitted by the Antigravity QA Agent via tools/native_submit.py.
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


CACHE_VERSION = "native-audit-v1"


def window_cache_key(window: ReviewWindow, code_context: str) -> Path:
    """Computes a content-addressed cache key for a review window."""
    events_data = [e.model_dump() for e in window.events]
    snaps_data = [s.model_dump() for s in window.snapshots]

    events_digest = hashlib.sha256(json.dumps(events_data, sort_keys=True).encode("utf-8")).hexdigest()
    snaps_digest = hashlib.sha256(json.dumps(snaps_data, sort_keys=True).encode("utf-8")).hexdigest()
    code_digest = hashlib.sha256(code_context.encode("utf-8")).hexdigest()

    payload = {
        "version": CACHE_VERSION,
        "session_id": window.session_id,
        "window_id": window.window_id,
        "events_digest": events_digest,
        "snaps_digest": snaps_digest,
        "code_digest": code_digest,
        "evaluator_mode": get_llm_status(),
    }
    return _cache_key("audit", json.dumps(payload, sort_keys=True))


def review_window(window: ReviewWindow) -> Optional[Finding]:
    """Reviews a window by consulting the agent native submission cache."""
    if not window.snapshots and not window.events:
        return None

    code_context = get_game_codebase_context(window.events)
    key = window_cache_key(window, code_context)
    cached = _cache_get(key)
    if cached:
        try:
            f = Finding(**cached)
            return f if f.verdict == Verdict.bug else None
        except Exception:
            pass
    return None
