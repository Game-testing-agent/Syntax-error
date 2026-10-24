"""Path 1: Deterministic rule and invariant checker for Godot game telemetry."""
from __future__ import annotations

from typing import Any, Optional
from schemas import Check, Event, Finding, Severity, Snapshot, Verdict, Violation

try:
    from simpleeval import simple_eval
    _HAS_SIMPLEEVAL = True
except ImportError:
    _HAS_SIMPLEEVAL = False


class AttrDict(dict):
    """Dictionary supporting dot-notation attribute access and safe defaults."""
    def __getattr__(self, item: str) -> Any:
        if item.startswith("__"):
            raise AttributeError(item)
        val = self.get(item)
        if isinstance(val, dict) and not isinstance(val, AttrDict):
            return AttrDict(val)
        return val


def _wrap(val: Any) -> Any:
    if isinstance(val, dict):
        return AttrDict({k: _wrap(v) for k, v in val.items()})
    if isinstance(val, list):
        return [_wrap(v) for v in val]
    return val


def _get_nested(obj: Any, path: str) -> Any:
    cur = obj
    for part in path.split("."):
        if isinstance(cur, dict):
            cur = cur.get(part)
        else:
            cur = getattr(cur, part, None)
        if cur is None:
            return None
    return cur


def _eval_predicate(predicate: str, snap: Snapshot, history: list[Snapshot]) -> bool:
    names = {
        "snap": snap,
        "player": _wrap(snap.player),
        "enemies": _wrap(snap.enemies),
        "coins": _wrap(snap.coins),
        "goal": _wrap(snap.goal),
        "inputs": _wrap(snap.inputs),
        "stats": _wrap(snap.stats),
        "fps": snap.fps,
        "frame": snap.frame,
        "session_time": snap.session_time,
        "scene": snap.scene,
        "game_state": snap.game_state,
        "history": history,
        "abs": abs,
        "min": min,
        "max": max,
        "len": len,
        "True": True,
        "False": False,
    }

    if _HAS_SIMPLEEVAL:
        try:
            return bool(simple_eval(predicate, names=names))
        except Exception:
            pass

    # Safe restricted eval with builtins restricted
    return bool(eval(predicate, {"__builtins__": {}}, names))


def check_snapshot(
    snap: Snapshot,
    checks: list[Check],
    history: list[Snapshot],
) -> list[Violation]:
    """Runs all active invariants against a single snapshot."""
    violations: list[Violation] = []
    for c in checks:
        try:
            ok = _eval_predicate(c.predicate, snap, history)
        except Exception as exc:
            # Skip invalid evaluation or log for debugging
            continue

        if not ok:
            evidence = {f: _get_nested(snap, f) for f in c.evidence_fields}
            violations.append(
                Violation(
                    check_id=c.id,
                    frame=snap.frame,
                    session_time=snap.session_time,
                    severity=c.severity_if_violated,
                    evidence=evidence,
                )
            )
    return violations


def check_event(event: Event) -> Optional[Violation]:
    """Inspects discrete events for contract violations and engine anomalies."""
    # 1. Objective telemetry event checks
    if event.event == "score_changed":
        delta = event.payload.get("delta", 0)
        if delta < 0:
            return Violation(
                check_id="engine_unexpected_score_change",
                frame=event.frame,
                session_time=event.session_time,
                severity=Severity.high,
                evidence={
                    "event_name": "unexpected_score_change",
                    "scene": event.scene,
                    "expected": "Score should only increase during active play",
                    "observed": f"Score decreased by {abs(delta)}",
                    "details": event.payload,
                },
            )
    elif event.event == "coin_overlap_ignored":
        return Violation(
            check_id="engine_duplicate_pickup_attempt",
            frame=event.frame,
            session_time=event.session_time,
            severity=Severity.high,
            evidence={
                "event_name": "duplicate_pickup_attempt",
                "scene": event.scene,
                "expected": "Coin should only trigger overlap before collection",
                "observed": "Duplicate overlap triggered on collected coin",
                "details": event.payload,
            },
        )
    elif event.event == "portal_activation_failed":
        return Violation(
            check_id="engine_missing_expected_object",
            frame=event.frame,
            session_time=event.session_time,
            severity=Severity.critical,
            evidence={
                "event_name": "missing_expected_object",
                "scene": event.scene,
                "expected": "Valid PackedScene assigned to portal",
                "observed": "Portal destination target is empty or missing",
                "details": event.payload,
            },
        )
    elif event.event == "scene_load_failed":
        return Violation(
            check_id="engine_runtime_error_observed",
            frame=event.frame,
            session_time=event.session_time,
            severity=Severity.critical,
            evidence={
                "event_name": "runtime_error_observed",
                "scene": event.scene,
                "expected": "Scene change should return OK (0)",
                "observed": f"Error code {event.payload.get('error_code')}",
                "details": event.payload,
            },
        )

    # 2. Legacy engine-level anomalies
    if event.category == "anomaly" or "anomaly" in event.event:
        sev_str = event.payload.get("severity", "warning").lower()
        if sev_str in ("error", "critical"):
            sev = Severity.critical
        elif sev_str in ("warning", "warn"):
            sev = Severity.high
        else:
            sev = Severity.medium

        evidence = {
            "event_name": event.event,
            "scene": event.scene,
            "expected": event.payload.get("expected"),
            "observed": event.payload.get("observed"),
            "details": event.payload.get("details") or event.payload,
        }

        return Violation(
            check_id=f"engine_{event.event}",
            frame=event.frame,
            session_time=event.session_time,
            severity=sev,
            evidence=evidence,
        )

    return None


def violations_to_findings(
    violations: list[Violation],
    checks_by_id: dict[str, Check],
) -> list[Finding]:
    """Aggregates violations by check_id and produces unified findings."""
    grouped: dict[str, list[Violation]] = {}
    for v in violations:
        grouped.setdefault(v.check_id, []).append(v)

    out: list[Finding] = []
    for check_id, vlist in grouped.items():
        first = vlist[0]
        c = checks_by_id.get(check_id)
        evidence_frames = [v.frame for v in vlist]

        if c:
            title = f"Check Violated: {c.description}"
            explanation = (
                f"Predicate '{c.predicate}' failed across {len(vlist)} frame(s) "
                f"(e.g. frame {first.frame} at t={first.session_time:.2f}s). "
                f"Evidence: {first.evidence}"
            )
            suspected = c.source
            sev = c.severity_if_violated
        else:
            # Engine anomaly
            ev = first.evidence
            ev_name = ev.get('event_name', check_id).replace("engine_", "")
            title = f"Engine Anomaly: {ev_name}"
            explanation = (
                f"Expected: {ev.get('expected', 'Normal execution')} | "
                f"Observed: {ev.get('observed', 'Anomaly logged by GameLogger.gd')} "
                f"across frame(s) {evidence_frames[:5]}."
            )
            code_map = {
                "duplicate_pickup_attempt": "Coin.gd:L21 (_on_body_entered)",
                "player_out_of_bounds": "Player.gd (OUT_OF_BOUNDS_Y)",
                "unexpected_score_change": "PlayerData.gd (set_score)",
                "missing_expected_object": "Portal2D.gd (teleport)",
                "scene_transition_timeout": "Portal2D.gd (GameLogger.is_scene_transitioning)",
                "runtime_error_observed": "Portal2D.gd (change_scene_to_packed)",
                "player_stuck_detected": "Player.gd (move_and_slide)",
                "unexpected_player_removal": "Player.gd (_exit_tree)",
            }
            suspected = code_map.get(ev_name, f"GameLogger.gd / {ev.get('scene', 'GameScene')}")
            sev = first.severity

        out.append(
            Finding(
                verdict=Verdict.bug,
                severity=sev,
                confidence=0.95,
                title=title,
                explanation=explanation,
                evidence_frames=evidence_frames[:10],
                suspected_code=suspected,
                path="path1",
                needs_human_review=False,
            )
        )
    return out
