"""Export ranked promo recommendations in reusable submission formats."""

from __future__ import annotations

import csv
import io
import json
from typing import Any

from .parser import seconds_to_timestamp
from .ranking import RankedPromo


def ranked_to_records(
    ranked: list[RankedPromo], editor_reviews: dict[str, str] | None = None
) -> list[dict[str, Any]]:
    editor_reviews = editor_reviews or {}
    records: list[dict[str, Any]] = []
    for item in ranked:
        candidate = item.candidate
        evaluation = item.evaluation
        records.append(
            {
                "rank": item.rank,
                "promo_id": candidate.candidate_id,
                "episode": candidate.episode_number,
                "start_timestamp": seconds_to_timestamp(candidate.start_seconds),
                "end_timestamp": seconds_to_timestamp(candidate.end_seconds),
                "duration_seconds": candidate.duration_seconds,
                "hook": evaluation.hook.description,
                "hook_evidence": evaluation.hook.evidence,
                "cliffhanger": evaluation.cliffhanger.description,
                "cliffhanger_evidence": evaluation.cliffhanger.evidence,
                "standalone_summary": evaluation.standalone.summary,
                "why_it_works": evaluation.why_it_works,
                "final_score": item.final_score,
                "confidence": evaluation.confidence,
                "spoiler_risk": evaluation.spoiler_risk,
                "warnings": evaluation.warnings,
                "penalties": item.penalties,
                "editor_review": editor_reviews.get(candidate.candidate_id, "not_reviewed"),
                "segments": [
                    {
                        "episode": candidate.episode_number,
                        "start": seconds_to_timestamp(candidate.start_seconds),
                        "end": seconds_to_timestamp(candidate.end_seconds),
                    }
                ],
                "source_entries": [entry.to_dict() for entry in candidate.source_entries],
            }
        )
    return records


def export_json(ranked: list[RankedPromo], editor_reviews: dict[str, str] | None = None) -> str:
    return json.dumps(ranked_to_records(ranked, editor_reviews), indent=2, ensure_ascii=False)


def export_csv(ranked: list[RankedPromo], editor_reviews: dict[str, str] | None = None) -> str:
    records = ranked_to_records(ranked, editor_reviews)
    fields = [
        "rank",
        "promo_id",
        "episode",
        "start_timestamp",
        "end_timestamp",
        "duration_seconds",
        "hook",
        "cliffhanger",
        "standalone_summary",
        "why_it_works",
        "final_score",
        "confidence",
        "spoiler_risk",
        "warnings",
        "penalties",
        "editor_review",
    ]
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=fields, extrasaction="ignore")
    writer.writeheader()
    for record in records:
        row = dict(record)
        row["warnings"] = "; ".join(record["warnings"])
        row["penalties"] = "; ".join(record["penalties"])
        writer.writerow(row)
    return buffer.getvalue()


def export_markdown(
    ranked: list[RankedPromo], editor_reviews: dict[str, str] | None = None
) -> str:
    records = ranked_to_records(ranked, editor_reviews)
    lines = ["# PromoScout Ranked Recommendations", ""]
    for record in records:
        lines.extend(
            [
                f"## #{record['rank']} - Episode {record['episode']}",
                "",
                f"**Segment:** {record['start_timestamp']} to {record['end_timestamp']} "
                f"({record['duration_seconds']:.2f}s)",
                "",
                f"**Hook:** {record['hook']}",
                "",
                f"**Cliffhanger:** {record['cliffhanger']}",
                "",
                f"**Why it works:** {record['why_it_works']}",
                "",
                f"**Score:** {record['final_score']:.2f}/100 | **Confidence:** "
                f"{record['confidence']:.0%} | **Editor:** {record['editor_review']}",
                "",
            ]
        )
    return "\n".join(lines)

