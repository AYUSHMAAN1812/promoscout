"""Deterministic post-validation, scoring, deduplication, and ranking."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Literal

from .evaluation import PromoEvaluation
from .models import PromoCandidate


Decision = Literal["accepted", "human_review", "rejected"]


@dataclass(slots=True)
class RankingConfig:
    minimum_duration_seconds: float = 20.0
    maximum_duration_seconds: float = 60.0
    minimum_hook_score: int = 5
    minimum_cliffhanger_score: int = 5
    minimum_standalone_score: int = 5
    accepted_score: float = 70.0
    human_review_score: float = 55.0
    overlap_threshold: float = 0.70
    max_per_episode: int = 1
    max_per_story_arc: int = 3
    story_arc_size: int = 10


@dataclass(slots=True)
class RankedPromo:
    candidate: PromoCandidate
    evaluation: PromoEvaluation
    final_score: float
    decision: Decision
    rejection_reasons: list[str] = field(default_factory=list)
    penalties: list[str] = field(default_factory=list)
    rank: int | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "rank": self.rank,
            "candidate": self.candidate.to_dict(),
            "evaluation": self.evaluation.to_dict(),
            "final_score": self.final_score,
            "decision": self.decision,
            "rejection_reasons": self.rejection_reasons,
            "penalties": self.penalties,
        }


def _overlap_ratio(first: PromoCandidate, second: PromoCandidate) -> float:
    if first.episode_number != second.episode_number:
        return 0.0
    intersection = max(
        0.0,
        min(first.end_seconds, second.end_seconds)
        - max(first.start_seconds, second.start_seconds),
    )
    shorter = min(first.duration_seconds, second.duration_seconds)
    return intersection / shorter if shorter else 0.0


def _story_arc(episode_number: int, config: RankingConfig) -> int:
    return (episode_number - 1) // config.story_arc_size + 1


def score_candidate(
    candidate: PromoCandidate,
    evaluation: PromoEvaluation,
    config: RankingConfig | None = None,
) -> RankedPromo:
    """Apply hard safety rules followed by the documented weighted score."""

    config = config or RankingConfig()
    rejection_reasons: list[str] = []
    penalties: list[str] = []

    if not config.minimum_duration_seconds <= candidate.duration_seconds <= config.maximum_duration_seconds:
        rejection_reasons.append("Duration is outside the required 20-60 second range.")
    if candidate.start_seconds >= candidate.end_seconds:
        rejection_reasons.append("Candidate timestamp range is invalid.")
    if not candidate.source_entries:
        rejection_reasons.append("Candidate has no source-grounding entries.")
    if evaluation.verdict == "reject":
        rejection_reasons.append("Gemini explicitly rejected the candidate.")
    if evaluation.boundary_verdict == "reject":
        rejection_reasons.append("Gemini rejected the supplied cut boundaries.")
    if not evaluation.hook.confirmed:
        rejection_reasons.append("Hook is not confirmed within the first three seconds.")
    if evaluation.hook.score < config.minimum_hook_score:
        rejection_reasons.append(
            f"Hook score {evaluation.hook.score} is below {config.minimum_hook_score}."
        )
    if not evaluation.cliffhanger.confirmed:
        rejection_reasons.append("Ending is not confirmed as unresolved at the cut.")
    if evaluation.cliffhanger.score < config.minimum_cliffhanger_score:
        rejection_reasons.append(
            f"Cliffhanger score {evaluation.cliffhanger.score} is below {config.minimum_cliffhanger_score}."
        )
    if evaluation.standalone.score < config.minimum_standalone_score:
        rejection_reasons.append(
            f"Standalone score {evaluation.standalone.score} is below {config.minimum_standalone_score}."
        )

    score = (
        evaluation.hook.score * 3.0
        + evaluation.cliffhanger.score * 2.5
        + evaluation.standalone.score * 2.0
        + evaluation.visual_emotional_intensity_score * 1.5
        + evaluation.confidence * 10.0
    )

    if evaluation.spoiler_risk == "medium":
        score -= 2.0
        penalties.append("-2 medium spoiler risk")
    elif evaluation.spoiler_risk == "high":
        score -= 7.0
        penalties.append("-7 high spoiler risk")

    if evaluation.standalone.required_context:
        context_penalty = min(12.0, len(evaluation.standalone.required_context) * 4.0)
        score -= context_penalty
        penalties.append(f"-{context_penalty:g} required prior context")
    if evaluation.boundary_verdict == "needs_adjustment":
        score -= 10.0
        penalties.append("-10 boundary adjustment required")
    if evaluation.verdict == "borderline":
        score -= 5.0
        penalties.append("-5 Gemini borderline verdict")
    if evaluation.warnings:
        warning_penalty = min(3.0, float(len(evaluation.warnings)))
        score -= warning_penalty
        penalties.append(f"-{warning_penalty:g} model warning penalty")

    score = round(max(0.0, min(100.0, score)), 2)
    if rejection_reasons:
        decision: Decision = "rejected"
    elif score >= config.accepted_score and evaluation.verdict == "suitable":
        decision = "accepted"
    elif score >= config.human_review_score:
        decision = "human_review"
    else:
        decision = "rejected"
        rejection_reasons.append(
            f"Final score {score:.2f} is below the human-review threshold {config.human_review_score:.2f}."
        )

    return RankedPromo(
        candidate=candidate,
        evaluation=evaluation,
        final_score=score,
        decision=decision,
        rejection_reasons=rejection_reasons,
        penalties=penalties,
    )


def rank_promos(
    scored: list[RankedPromo],
    config: RankingConfig | None = None,
) -> list[RankedPromo]:
    """Rank usable promos while enforcing overlap and story-diversity caps."""

    config = config or RankingConfig()
    usable = sorted(
        (item for item in scored if item.decision != "rejected"),
        key=lambda item: (
            item.decision == "accepted",
            item.final_score,
            item.evaluation.confidence,
            item.candidate.deterministic_score,
        ),
        reverse=True,
    )
    selected: list[RankedPromo] = []
    episode_counts: dict[int, int] = {}
    arc_counts: dict[int, int] = {}

    for item in usable:
        episode = item.candidate.episode_number
        arc = _story_arc(episode, config)
        if episode_counts.get(episode, 0) >= config.max_per_episode:
            item.decision = "rejected"
            item.rejection_reasons.append("A stronger promo from the same episode was selected.")
            continue
        if arc_counts.get(arc, 0) >= config.max_per_story_arc:
            item.decision = "human_review"
            item.penalties.append("Deferred from primary ranking by story-arc diversity cap")
            continue
        if any(
            _overlap_ratio(item.candidate, existing.candidate) >= config.overlap_threshold
            for existing in selected
        ):
            item.decision = "rejected"
            item.rejection_reasons.append("Overlaps substantially with a stronger selected promo.")
            continue
        selected.append(item)
        episode_counts[episode] = episode_counts.get(episode, 0) + 1
        arc_counts[arc] = arc_counts.get(arc, 0) + 1

    for rank, item in enumerate(selected, start=1):
        item.rank = rank
    return selected

