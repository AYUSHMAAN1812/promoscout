"""Transparent deterministic generation of 20-60 second promo candidates."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass

from .models import Episode, PromoCandidate, ScriptEntry


HOOK_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("question", re.compile(r"\?")),
    ("command", re.compile(r"\b(stop|look|listen|run|leave|arrest|guards?|wait|get up|tell me)\b", re.I)),
    ("shock/reveal", re.compile(r"\b(who are you|you already know|not anymore|impossible|alive|dead|duke|duchess|heir|poison|arsenic|witch|betray|stole|secret|truth|marry|husband|wife)\b", re.I)),
    ("danger", re.compile(r"\b(fire|blood|kill|hang|execution|attack|explosion|blade|poker|burn|choke|gallows|threat)\w*\b", re.I)),
    ("high-impact action", re.compile(r"\b(slap|strik|burst|crash|shatter|kick|grab|seiz|drag|collapse|explode|flames?|scream)\w*\b", re.I)),
    ("emotional confrontation", re.compile(r"\b(how dare|never|liar|monster|love|hate|abandon|humiliat|beg|plead|defiant)\w*\b", re.I)),
)

CLIFF_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("unanswered question", re.compile(r"\?")),
    ("threat/promise", re.compile(r"\b(will pay|swear|vow|destroy|kill|hang|execute|settle|coming for|never let|ten days|plenty of time)\b", re.I)),
    ("identity reveal", re.compile(r"\b(real name|who he is|rightful|duke|duchess|heir|imposter|crest|ring|identity)\b", re.I)),
    ("discovery", re.compile(r"\b(discover|realiz|recogniz|witness|caught|evidence|poison|arsenic|secret|truth|documents?)\w*\b", re.I)),
    ("interruption/arrival", re.compile(r"\b(door|arriv|enters?|burst|explosion|footsteps|knock|bell|someone|unexpected)\w*\b", re.I)),
    ("unresolved danger", re.compile(r"\b(fire|poker|blade|chains?|gallows|execution|arrest|attack|choke|terrified|horrified|danger)\w*\b", re.I)),
    ("explicit cliffhanger direction", re.compile(r"\b(cliffhanger|cut(?:s|ting)? (?:sharply |abruptly )?to black|freeze-frame|unresolved|suspenseful hold)\b", re.I)),
)


@dataclass(slots=True)
class CandidateConfig:
    min_duration_seconds: float = 20.0
    max_duration_seconds: float = 60.0
    target_duration_seconds: float = 42.0
    hook_window_seconds: float = 3.0
    cliff_window_seconds: float = 6.0
    max_candidates_per_episode: int = 8
    minimum_score: float = 2.0
    overlap_threshold: float = 0.72


def _matching_signals(text: str, patterns: tuple[tuple[str, re.Pattern[str]], ...]) -> list[str]:
    return [name for name, pattern in patterns if pattern.search(text)]


def _entries_overlapping(
    entries: list[ScriptEntry], start_seconds: float, end_seconds: float
) -> list[ScriptEntry]:
    return [
        entry
        for entry in entries
        if entry.end_seconds > start_seconds and entry.start_seconds < end_seconds
    ]


def _text(entries: list[ScriptEntry]) -> str:
    return " ".join(entry.text for entry in entries if entry.text)


def _candidate_id(episode_number: int, start_seconds: float, end_seconds: float) -> str:
    raw = f"{episode_number}:{start_seconds:.2f}:{end_seconds:.2f}".encode()
    digest = hashlib.sha1(raw).hexdigest()[:8]
    return f"E{episode_number:03d}-{int(round(start_seconds * 100)):06d}-{int(round(end_seconds * 100)):06d}-{digest}"


def _intersection_over_shorter(a: PromoCandidate, b: PromoCandidate) -> float:
    overlap = max(0.0, min(a.end_seconds, b.end_seconds) - max(a.start_seconds, b.start_seconds))
    shorter = min(a.duration_seconds, b.duration_seconds)
    return overlap / shorter if shorter else 0.0


def _score_window(
    episode: Episode,
    start_seconds: float,
    end_seconds: float,
    config: CandidateConfig,
) -> PromoCandidate:
    all_entries = episode.entries
    source_entries = _entries_overlapping(all_entries, start_seconds, end_seconds)
    hook_entries = _entries_overlapping(
        all_entries, start_seconds, min(end_seconds, start_seconds + config.hook_window_seconds)
    )
    cliff_entries = _entries_overlapping(
        all_entries, max(start_seconds, end_seconds - config.cliff_window_seconds), end_seconds
    )
    hook_signals = _matching_signals(_text(hook_entries), HOOK_PATTERNS)
    cliff_signals = _matching_signals(_text(cliff_entries), CLIFF_PATTERNS)
    reasons: list[str] = []

    score = min(len(hook_signals), 3) * 1.35
    score += min(len(cliff_signals), 3) * 1.25

    if hook_signals:
        reasons.append("Opening three seconds contain hook signals")
    if cliff_signals:
        reasons.append("Final six seconds contain unresolved or reveal signals")

    hook_kinds = {entry.kind for entry in hook_entries}
    if "action" in hook_kinds:
        score += 0.55
        reasons.append("Opens with visible action")
    if "dialogue" in hook_kinds:
        score += 0.35
        reasons.append("Opens with dialogue")
    if any(entry.kind == "dialogue" for entry in source_entries) and any(
        entry.kind in {"action", "camera"} for entry in source_entries
    ):
        score += 0.35
        reasons.append("Contains both spoken and visual story information")

    if abs(end_seconds - episode.duration_seconds) <= 0.15:
        score += 1.1
        reasons.append("Ends at the episode cliffhanger boundary")

    duration = end_seconds - start_seconds
    duration_fit = max(0.0, 1.0 - abs(duration - config.target_duration_seconds) / 22.0)
    score += duration_fit * 0.45

    if len(source_entries) < 3:
        score -= 1.0
        reasons.append("Sparse source coverage")
    if not hook_signals:
        score -= 0.8
        reasons.append("No explicit deterministic hook signal")
    if not cliff_signals and abs(end_seconds - episode.duration_seconds) > 0.15:
        score -= 0.8
        reasons.append("No explicit deterministic cliffhanger signal")

    return PromoCandidate(
        candidate_id=_candidate_id(episode.episode_number, start_seconds, end_seconds),
        episode_number=episode.episode_number,
        start_seconds=round(start_seconds, 2),
        end_seconds=round(end_seconds, 2),
        deterministic_score=round(score, 3),
        generation_reasons=reasons,
        hook_signals=hook_signals,
        cliffhanger_signals=cliff_signals,
        source_entries=source_entries,
    )


def generate_candidates(
    episode: Episode, config: CandidateConfig | None = None
) -> list[PromoCandidate]:
    """Generate explainable candidate windows without using a language model."""

    config = config or CandidateConfig()
    entries = episode.entries
    if not entries:
        return []

    boundaries = sorted(
        {
            round(value, 2)
            for entry in entries
            for value in (entry.start_seconds, entry.end_seconds)
            if 0 <= value <= episode.duration_seconds
        }
        | {scene.start_seconds for scene in episode.scenes}
        | {scene.end_seconds for scene in episode.scenes}
        | {episode.duration_seconds}
    )
    start_boundaries = sorted(
        {
            entry.start_seconds
            for entry in entries
            if entry.kind in {"dialogue", "action", "sound"}
        }
        | {scene.start_seconds for scene in episode.scenes}
    )

    scored: list[PromoCandidate] = []
    for start in start_boundaries:
        valid_ends = [
            end
            for end in boundaries
            if config.min_duration_seconds <= end - start <= config.max_duration_seconds
        ]
        if not valid_ends:
            continue

        # Keep a compact range of plausible endings: best cliff signals plus target/end boundaries.
        ranked_ends: list[tuple[float, float]] = []
        for end in valid_ends:
            cliff_entries = _entries_overlapping(
                entries, max(start, end - config.cliff_window_seconds), end
            )
            signal_count = len(_matching_signals(_text(cliff_entries), CLIFF_PATTERNS))
            end_bonus = 2.0 if abs(end - episode.duration_seconds) <= 0.15 else 0.0
            target_fit = 1.0 - abs((end - start) - config.target_duration_seconds) / 40.0
            ranked_ends.append((signal_count * 2.0 + end_bonus + target_fit, end))
        for _, end in sorted(ranked_ends, reverse=True)[:5]:
            candidate = _score_window(episode, start, end, config)
            if candidate.deterministic_score >= config.minimum_score:
                scored.append(candidate)

    scored.sort(
        key=lambda candidate: (
            candidate.deterministic_score,
            len(candidate.hook_signals),
            len(candidate.cliffhanger_signals),
            -abs(candidate.duration_seconds - config.target_duration_seconds),
        ),
        reverse=True,
    )

    selected: list[PromoCandidate] = []
    for candidate in scored:
        if any(
            _intersection_over_shorter(candidate, existing) >= config.overlap_threshold
            for existing in selected
        ):
            continue
        selected.append(candidate)
        if len(selected) >= config.max_candidates_per_episode:
            break
    return selected


def generate_show_candidates(
    episodes: list[Episode], config: CandidateConfig | None = None
) -> list[PromoCandidate]:
    config = config or CandidateConfig()
    return [candidate for episode in episodes for candidate in generate_candidates(episode, config)]

