"""Core data models used by the deterministic screenplay parser."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Literal


Severity = Literal["warning", "error"]
EntryKind = Literal["camera", "action", "sound", "dialogue", "other"]


@dataclass(slots=True)
class ValidationIssue:
    code: str
    message: str
    severity: Severity = "warning"
    source_line: int | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class ScriptEntry:
    label: str
    kind: EntryKind
    start_seconds: float
    end_seconds: float
    text: str
    source_line: int
    speaker: str | None = None

    @property
    def duration_seconds(self) -> float:
        return round(self.end_seconds - self.start_seconds, 2)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class Scene:
    number: int
    heading: str
    start_seconds: float
    end_seconds: float
    source_line: int
    entries: list[ScriptEntry] = field(default_factory=list)

    @property
    def duration_seconds(self) -> float:
        return round(self.end_seconds - self.start_seconds, 2)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["duration_seconds"] = self.duration_seconds
        return data


@dataclass(slots=True)
class Episode:
    episode_number: int
    source_id: str | None
    source_name: str
    logline: str
    continuity_notes: str
    scenes: list[Scene]
    issues: list[ValidationIssue] = field(default_factory=list)
    raw_text: str = field(default="", repr=False)

    @property
    def entries(self) -> list[ScriptEntry]:
        return [entry for scene in self.scenes for entry in scene.entries]

    @property
    def duration_seconds(self) -> float:
        scene_end = max((scene.end_seconds for scene in self.scenes), default=0.0)
        entry_end = max((entry.end_seconds for entry in self.entries), default=0.0)
        return round(max(scene_end, entry_end), 2)

    @property
    def error_count(self) -> int:
        return sum(issue.severity == "error" for issue in self.issues)

    @property
    def warning_count(self) -> int:
        return sum(issue.severity == "warning" for issue in self.issues)

    def to_dict(self, include_raw_text: bool = False) -> dict[str, Any]:
        data: dict[str, Any] = {
            "episode_number": self.episode_number,
            "source_id": self.source_id,
            "source_name": self.source_name,
            "logline": self.logline,
            "continuity_notes": self.continuity_notes,
            "duration_seconds": self.duration_seconds,
            "scenes": [scene.to_dict() for scene in self.scenes],
            "issues": [issue.to_dict() for issue in self.issues],
        }
        if include_raw_text:
            data["raw_text"] = self.raw_text
        return data


@dataclass(slots=True)
class PromoCandidate:
    candidate_id: str
    episode_number: int
    start_seconds: float
    end_seconds: float
    deterministic_score: float
    generation_reasons: list[str]
    hook_signals: list[str]
    cliffhanger_signals: list[str]
    source_entries: list[ScriptEntry]

    @property
    def duration_seconds(self) -> float:
        return round(self.end_seconds - self.start_seconds, 2)

    def to_dict(self) -> dict[str, Any]:
        return {
            "candidate_id": self.candidate_id,
            "episode_number": self.episode_number,
            "start_seconds": self.start_seconds,
            "end_seconds": self.end_seconds,
            "duration_seconds": self.duration_seconds,
            "deterministic_score": self.deterministic_score,
            "generation_reasons": self.generation_reasons,
            "hook_signals": self.hook_signals,
            "cliffhanger_signals": self.cliffhanger_signals,
            "source_entries": [entry.to_dict() for entry in self.source_entries],
        }

