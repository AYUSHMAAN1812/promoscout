"""Structured Gemini evaluation contract and local response validation."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Literal


Verdict = Literal["suitable", "borderline", "reject"]
Risk = Literal["low", "medium", "high"]


PROMO_EVALUATION_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "candidate_id": {"type": "string"},
        "verdict": {"type": "string", "enum": ["suitable", "borderline", "reject"]},
        "hook": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "description": {"type": "string"},
                "evidence": {"type": "string"},
                "score": {"type": "integer", "minimum": 0, "maximum": 10},
                "within_first_three_seconds": {"type": "boolean"},
            },
            "required": ["description", "evidence", "score", "within_first_three_seconds"],
        },
        "cliffhanger": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "description": {"type": "string"},
                "evidence": {"type": "string"},
                "score": {"type": "integer", "minimum": 0, "maximum": 10},
                "unresolved_at_cut": {"type": "boolean"},
            },
            "required": ["description", "evidence", "score", "unresolved_at_cut"],
        },
        "standalone": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "summary": {"type": "string"},
                "score": {"type": "integer", "minimum": 0, "maximum": 10},
                "required_context": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["summary", "score", "required_context"],
        },
        "visual_emotional_intensity_score": {"type": "integer", "minimum": 0, "maximum": 10},
        "spoiler_risk": {"type": "string", "enum": ["low", "medium", "high"]},
        "why_it_works": {"type": "string"},
        "failure_reasons": {"type": "array", "items": {"type": "string"}},
        "warnings": {"type": "array", "items": {"type": "string"}},
        "boundary_verdict": {"type": "string", "enum": ["keep", "needs_adjustment", "reject"]},
        "boundary_reason": {"type": "string"},
        "overall_score": {"type": "integer", "minimum": 0, "maximum": 100},
        "confidence": {"type": "number", "minimum": 0, "maximum": 1},
    },
    "required": [
        "candidate_id",
        "verdict",
        "hook",
        "cliffhanger",
        "standalone",
        "visual_emotional_intensity_score",
        "spoiler_risk",
        "why_it_works",
        "failure_reasons",
        "warnings",
        "boundary_verdict",
        "boundary_reason",
        "overall_score",
        "confidence",
    ],
}


class EvaluationValidationError(ValueError):
    """Raised when model output violates the local evaluation contract."""


@dataclass(slots=True)
class MomentAssessment:
    description: str
    evidence: str
    score: int
    confirmed: bool


@dataclass(slots=True)
class StandaloneAssessment:
    summary: str
    score: int
    required_context: list[str] = field(default_factory=list)


@dataclass(slots=True)
class PromoEvaluation:
    candidate_id: str
    verdict: Verdict
    hook: MomentAssessment
    cliffhanger: MomentAssessment
    standalone: StandaloneAssessment
    visual_emotional_intensity_score: int
    spoiler_risk: Risk
    why_it_works: str
    failure_reasons: list[str]
    warnings: list[str]
    boundary_verdict: Literal["keep", "needs_adjustment", "reject"]
    boundary_reason: str
    overall_score: int
    confidence: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "candidate_id": self.candidate_id,
            "verdict": self.verdict,
            "hook": {
                "description": self.hook.description,
                "evidence": self.hook.evidence,
                "score": self.hook.score,
                "within_first_three_seconds": self.hook.confirmed,
            },
            "cliffhanger": {
                "description": self.cliffhanger.description,
                "evidence": self.cliffhanger.evidence,
                "score": self.cliffhanger.score,
                "unresolved_at_cut": self.cliffhanger.confirmed,
            },
            "standalone": asdict(self.standalone),
            "visual_emotional_intensity_score": self.visual_emotional_intensity_score,
            "spoiler_risk": self.spoiler_risk,
            "why_it_works": self.why_it_works,
            "failure_reasons": self.failure_reasons,
            "warnings": self.warnings,
            "boundary_verdict": self.boundary_verdict,
            "boundary_reason": self.boundary_reason,
            "overall_score": self.overall_score,
            "confidence": self.confidence,
        }


def _object(value: Any, field_name: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise EvaluationValidationError(f"{field_name} must be an object")
    return value


def _string(value: Any, field_name: str, *, allow_empty: bool = False) -> str:
    if not isinstance(value, str) or (not allow_empty and not value.strip()):
        raise EvaluationValidationError(f"{field_name} must be a non-empty string")
    return value.strip()


def _integer_score(value: Any, field_name: str, maximum: int = 10) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= maximum:
        raise EvaluationValidationError(f"{field_name} must be an integer from 0 to {maximum}")
    return value


def _string_list(value: Any, field_name: str) -> list[str]:
    if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
        raise EvaluationValidationError(f"{field_name} must be an array of strings")
    return [item.strip() for item in value if item.strip()]


def validate_evaluation(data: Any, expected_candidate_id: str) -> PromoEvaluation:
    """Validate untrusted model JSON independently of SDK schema enforcement."""

    root = _object(data, "response")
    missing = set(PROMO_EVALUATION_SCHEMA["required"]) - set(root)
    if missing:
        raise EvaluationValidationError(f"missing required fields: {sorted(missing)}")

    candidate_id = _string(root["candidate_id"], "candidate_id")
    if candidate_id != expected_candidate_id:
        raise EvaluationValidationError(
            f"candidate_id mismatch: expected {expected_candidate_id!r}, got {candidate_id!r}"
        )

    verdict = root["verdict"]
    if verdict not in {"suitable", "borderline", "reject"}:
        raise EvaluationValidationError("verdict is invalid")
    spoiler_risk = root["spoiler_risk"]
    if spoiler_risk not in {"low", "medium", "high"}:
        raise EvaluationValidationError("spoiler_risk is invalid")
    boundary_verdict = root["boundary_verdict"]
    if boundary_verdict not in {"keep", "needs_adjustment", "reject"}:
        raise EvaluationValidationError("boundary_verdict is invalid")

    hook = _object(root["hook"], "hook")
    cliff = _object(root["cliffhanger"], "cliffhanger")
    standalone = _object(root["standalone"], "standalone")
    hook_confirmed = hook.get("within_first_three_seconds", hook.get("confirmed"))
    cliff_confirmed = cliff.get("unresolved_at_cut", cliff.get("confirmed"))
    for field_name, value in (
        ("hook.within_first_three_seconds", hook_confirmed),
        ("cliffhanger.unresolved_at_cut", cliff_confirmed),
    ):
        if not isinstance(value, bool):
            raise EvaluationValidationError(f"{field_name} must be boolean")

    confidence = root["confidence"]
    if isinstance(confidence, bool) or not isinstance(confidence, (int, float)) or not 0 <= confidence <= 1:
        raise EvaluationValidationError("confidence must be a number from 0 to 1")

    return PromoEvaluation(
        candidate_id=candidate_id,
        verdict=verdict,
        hook=MomentAssessment(
            description=_string(hook.get("description"), "hook.description"),
            evidence=_string(hook.get("evidence"), "hook.evidence", allow_empty=True),
            score=_integer_score(hook.get("score"), "hook.score"),
            confirmed=hook_confirmed,
        ),
        cliffhanger=MomentAssessment(
            description=_string(cliff.get("description"), "cliffhanger.description"),
            evidence=_string(cliff.get("evidence"), "cliffhanger.evidence", allow_empty=True),
            score=_integer_score(cliff.get("score"), "cliffhanger.score"),
            confirmed=cliff_confirmed,
        ),
        standalone=StandaloneAssessment(
            summary=_string(standalone.get("summary"), "standalone.summary"),
            score=_integer_score(standalone.get("score"), "standalone.score"),
            required_context=_string_list(standalone.get("required_context"), "standalone.required_context"),
        ),
        visual_emotional_intensity_score=_integer_score(
            root["visual_emotional_intensity_score"], "visual_emotional_intensity_score"
        ),
        spoiler_risk=spoiler_risk,
        why_it_works=_string(root["why_it_works"], "why_it_works", allow_empty=True),
        failure_reasons=_string_list(root["failure_reasons"], "failure_reasons"),
        warnings=_string_list(root["warnings"], "warnings"),
        boundary_verdict=boundary_verdict,
        boundary_reason=_string(root["boundary_reason"], "boundary_reason"),
        overall_score=_integer_score(root["overall_score"], "overall_score", maximum=100),
        confidence=float(confidence),
    )

