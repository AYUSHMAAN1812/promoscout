"""Apply deterministic Step 5 rules to the live Step 4 Gemini sample."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from promoscout.evaluation import validate_evaluation  # noqa: E402
from promoscout.models import PromoCandidate, ScriptEntry  # noqa: E402
from promoscout.parser import seconds_to_timestamp  # noqa: E402
from promoscout.ranking import rank_promos, score_candidate  # noqa: E402


def candidate_from_dict(data: dict) -> PromoCandidate:
    return PromoCandidate(
        candidate_id=data["candidate_id"],
        episode_number=data["episode_number"],
        start_seconds=data["start_seconds"],
        end_seconds=data["end_seconds"],
        deterministic_score=data["deterministic_score"],
        generation_reasons=data["generation_reasons"],
        hook_signals=data["hook_signals"],
        cliffhanger_signals=data["cliffhanger_signals"],
        source_entries=[ScriptEntry(**entry) for entry in data["source_entries"]],
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("sample_json", type=Path)
    parser.add_argument("--json-output", type=Path, required=True)
    parser.add_argument("--markdown-output", type=Path, required=True)
    args = parser.parse_args()

    sample = json.loads(args.sample_json.read_text(encoding="utf-8"))
    scored = []
    for result in sample["results"]:
        candidate = candidate_from_dict(result["candidate"])
        evaluation = validate_evaluation(result["evaluation"], candidate.candidate_id)
        scored.append(score_candidate(candidate, evaluation))
    ranked = rank_promos(scored)

    payload = {
        "sample_size": len(scored),
        "accepted_count": sum(item.decision == "accepted" for item in scored),
        "human_review_count": sum(item.decision == "human_review" for item in scored),
        "rejected_count": sum(item.decision == "rejected" for item in scored),
        "ranked_candidate_ids": [item.candidate.candidate_id for item in ranked],
        "results": [item.to_dict() for item in sorted(scored, key=lambda x: x.final_score, reverse=True)],
    }
    args.json_output.parent.mkdir(parents=True, exist_ok=True)
    args.markdown_output.parent.mkdir(parents=True, exist_ok=True)
    args.json_output.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    lines = [
        "# Step 5 Validation and Ranking Report",
        "",
        f"- Sample candidates: {payload['sample_size']}",
        f"- Accepted: {payload['accepted_count']}",
        f"- Human review: {payload['human_review_count']}",
        f"- Rejected: {payload['rejected_count']}",
        "",
        "| Rank | Episode | Window | Gemini verdict | Final score | Decision | Main reason |",
        "|---:|---:|---:|---|---:|---|---|",
    ]
    ranked_ids = {item.candidate.candidate_id: item.rank for item in ranked}
    for item in sorted(scored, key=lambda value: value.final_score, reverse=True):
        reason = item.rejection_reasons[0] if item.rejection_reasons else (
            item.penalties[0] if item.penalties else "Passed all deterministic checks"
        )
        lines.append(
            f"| {ranked_ids.get(item.candidate.candidate_id, '')} | {item.candidate.episode_number} | "
            f"{seconds_to_timestamp(item.candidate.start_seconds)}-{seconds_to_timestamp(item.candidate.end_seconds)} | "
            f"{item.evaluation.verdict} | {item.final_score:.2f} | {item.decision} | {reason} |"
        )

    lines.extend(["", "## Deterministic contradiction handling", ""])
    lines.extend(
        [
            "- A candidate is rejected if Gemini denies a first-three-second hook or unresolved ending.",
            "- Hook, cliffhanger, or standalone scores below 5 are hard failures even when the overall verdict is `borderline`.",
            "- Invalid duration, empty source grounding, or rejected boundaries are hard failures.",
            "- Context, spoiler, warning, and boundary-adjustment concerns reduce the weighted score.",
            "- Overlap, per-episode limits, and story-arc caps prevent a repetitive top list.",
            "",
        ]
    )
    args.markdown_output.write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps({key: value for key, value in payload.items() if key != "results"}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

