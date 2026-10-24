# schemas.py — Godot 2D Platformer Telemetry & QA Schemas
from __future__ import annotations

from enum import Enum
from typing import Any, Literal, Optional
from pydantic import BaseModel, Field


class Verdict(str, Enum):
    bug = "bug"
    not_a_bug = "not_a_bug"
    unsure = "unsure"


class Severity(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"
    critical = "critical"


class Snapshot(BaseModel):
    """A periodic numeric telemetry snapshot from latest_state.json or game_events.jsonl."""
    frame: int = 0
    session_time: float = 0.0
    timestamp: float = 0.0
    scene: str = ""
    game_state: str = ""
    fps: float = 60.0
    player: dict[str, Any] = Field(default_factory=dict)
    enemies: dict[str, Any] = Field(default_factory=dict)
    coins: dict[str, Any] = Field(default_factory=dict)
    goal: dict[str, Any] = Field(default_factory=dict)
    inputs: dict[str, Any] = Field(default_factory=dict)
    stats: dict[str, Any] = Field(default_factory=dict)


class Event(BaseModel):
    """A discrete event from game_events.jsonl (lifecycle, inputs, collectibles, anomalies)."""
    event: str
    frame: int = 0
    session_time: float = 0.0
    timestamp: float = 0.0
    scene: Optional[str] = None
    category: Optional[str] = None
    payload: dict[str, Any] = Field(default_factory=dict)
    evidence: dict[str, Any] = Field(default_factory=dict)


class Check(BaseModel):
    id: str
    source: str
    description: str
    predicate: str
    severity_if_violated: Severity
    evidence_fields: list[str] = Field(default_factory=list)


class Violation(BaseModel):
    check_id: str
    frame: int
    session_time: float
    severity: Severity
    evidence: dict[str, Any] = Field(default_factory=dict)


class Finding(BaseModel):
    verdict: Verdict = Verdict.bug
    severity: Optional[Severity] = None
    confidence: float = Field(default=0.95, ge=0.0, le=1.0)
    title: str
    explanation: str
    evidence_frames: list[int] = Field(default_factory=list)
    suspected_code: Optional[str] = None
    path: Literal["path1", "path2"] = "path1"
    needs_human_review: bool = False


class ReviewWindow(BaseModel):
    """Temporal review window of gameplay examined by Path 2 LLM / semantic triage."""
    window_id: str = "w0"
    session_id: str = ""
    scene: str = ""
    start_frame: int = 0
    end_frame: int = 0
    snapshots: list[Snapshot] = Field(default_factory=list)
    events: list[Event] = Field(default_factory=list)
    active_checks: list[Check] = Field(default_factory=list)


class ExpectedBug(BaseModel):
    title: str
    should_be_caught_by: Literal["path1", "path2"] = "path1"
    frame_approx: Optional[int] = None
    t_approx_ms: Optional[float] = None


class Truth(BaseModel):
    session_id: str
    expected_bugs: list[ExpectedBug] = Field(default_factory=list)


class SessionData(BaseModel):
    session_id: str
    snapshots: list[Snapshot] = Field(default_factory=list)
    events: list[Event] = Field(default_factory=list)
