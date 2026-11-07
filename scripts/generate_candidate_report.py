"""Generate deterministic candidates and a review report for the private input pack."""

from __future__ import annotations

import argparse
import json
import statistics
import sys
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from promoscout.candidates import CandidateConfig, generate_show_candidates  # noqa: E402
from promoscout.parser import parse_screenplay_zip, seconds_to_timestamp  # noqa: E402


REVIEW_EPISODES = {1, 3, 11, 18, 23, 31, 34, 41, 42, 45, 50}


def clean_excerpt(text: str, limit: int = 170) -> str:
    compact = " ".join(text.split()).replace("|", "\\|")
    return compact if len(compact) <= limit else compact[: limit - 1].rstrip() + "…"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("zip_path", type=Path)
    parser.add_argument("--json-output", type=Path, required=True)
    parser.add_argument("--markdown-output", type=Path, required=True)
    args = parser.parse_args()

    episodes = parse_screenplay_zip(args.zip_path)
    config = CandidateConfig()
    candidates = generate_show_candidates(episodes, config)
    by_episode = Counter(candidate.episode_number for candidate in candidates)
    hook_counts = Counter(signal for candidate in candidates for signal in candidate.hook_signals)
    cliff_counts = Counter(signal for candidate in candidates for signal in candidate.cliffhanger_signals)

    payload = {
        "config": {
            key: getattr(config, key)
            for key in config.__dataclass_fields__
        },
        "summary": {
            "episodes_processed": len(episodes),
            "candidate_count": len(candidates),
            "episodes_with_candidates": len(by_episode),
            "minimum_candidates_per_episode": min(by_episode.values(), default=0),
            "maximum_candidates_per_episode": max(by_episode.values(), default=0),
            "average_candidates_per_episode": round(statistics.mean(by_episode.values()), 2) if by_episode else 0,
            "minimum_duration_seconds": min((candidate.duration_seconds for candidate in candidates), default=0),
            "maximum_duration_seconds": max((candidate.duration_seconds for candidate in candidates), default=0),
            "average_duration_seconds": round(statistics.mean(candidate.duration_seconds for candidate in candidates), 2) if candidates else 0,
            "hook_signal_counts": dict(sorted(hook_counts.items())),
            "cliffhanger_signal_counts": dict(sorted(cliff_counts.items())),
        },
        "candidates": [candidate.to_dict() for candidate in candidates],
    }
    args.json_output.parent.mkdir(parents=True, exist_ok=True)
    args.markdown_output.parent.mkdir(parents=True, exist_ok=True)
    args.json_output.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    summary = payload["summary"]
    lines = [
        "# Step 3 Deterministic Candidate Report",
        "",
        "This is a pre-Gemini shortlist. Scores are transparent heuristic signals, not final promo quality judgments.",
        "",
        "## Summary",
        "",
        f"- Episodes processed: {summary['episodes_processed']}",
        f"- Episodes with candidates: {summary['episodes_with_candidates']}",
        f"- Candidates generated: {summary['candidate_count']}",
        f"- Candidates per episode: {summary['minimum_candidates_per_episode']}-{summary['maximum_candidates_per_episode']} (average {summary['average_candidates_per_episode']})",
        f"- Candidate duration range: {summary['minimum_duration_seconds']:.2f}-{summary['maximum_duration_seconds']:.2f} seconds",
        f"- Average duration: {summary['average_duration_seconds']:.2f} seconds",
        "",
        "## Deterministic safeguards",
        "",
        "- Every window is between 20 and 60 seconds.",
        "- Start and end points come from parsed screenplay boundaries.",
        "- The opening 3 seconds and closing 6 seconds are scored separately.",
        "- Overlap suppression removes near-identical windows within an episode.",
        "- Generation reasons and matched signals are retained for auditability.",
        "- These signals intentionally over-generate; Gemini and later validation will reject semantically weak candidates.",
        "",
        "## Cross-arc spot checks",
        "",
        "| Episode | Window | Score | Opening evidence | Ending evidence | Hook signals | Cliff signals |",
        "|---:|---:|---:|---|---|---|---|",
    ]
    for episode_number in sorted(REVIEW_EPISODES):
        episode_candidates = sorted(
            (candidate for candidate in candidates if candidate.episode_number == episode_number),
            key=lambda candidate: candidate.deterministic_score,
            reverse=True,
        )[:2]
        for candidate in episode_candidates:
            opening_entries = [
                entry
                for entry in candidate.source_entries
                if entry.end_seconds > candidate.start_seconds
                and entry.start_seconds < candidate.start_seconds + 3
            ]
            ending_entries = [
                entry
                for entry in candidate.source_entries
                if entry.end_seconds > candidate.end_seconds - 6
                and entry.start_seconds < candidate.end_seconds
            ]
            opening = clean_excerpt(" ".join(entry.text for entry in opening_entries))
            ending = clean_excerpt(" ".join(entry.text for entry in ending_entries))
            lines.append(
                f"| {episode_number} | {seconds_to_timestamp(candidate.start_seconds)}-"
                f"{seconds_to_timestamp(candidate.end_seconds)} | {candidate.deterministic_score:.2f} | "
                f"{opening} | {ending} | {', '.join(candidate.hook_signals)} | "
                f"{', '.join(candidate.cliffhanger_signals)} |"
            )

    lines.extend(
        [
            "",
            "## Known deterministic limitations",
            "",
            "- Keyword matches do not understand whether a conflict is self-contained.",
            "- A camera direction that says `cliffhanger` can receive a strong signal even when the preceding story setup is weak.",
            "- Character relationships and pronouns are not resolved at this stage.",
            "- The heuristic may favor repeated danger and confrontation language over quieter romantic hooks.",
            "- The candidate score is only a recall-oriented filter for Gemini, not the final ranking.",
            "",
        ]
    )
    args.markdown_output.write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

