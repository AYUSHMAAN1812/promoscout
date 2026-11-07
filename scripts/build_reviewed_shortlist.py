"""Create a human-reviewed shortlist from automated rankings and manual labels."""

from __future__ import annotations

import argparse
import csv
import io
import json
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ranked", type=Path, required=True)
    parser.add_argument("--reviews", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    ranked = json.loads(args.ranked.read_text(encoding="utf-8"))
    reviews_payload = json.loads(args.reviews.read_text(encoding="utf-8"))
    reviews = {
        review["candidate_id"]: review
        for review in reviews_payload["primary_ranked_reviews"]
    }
    accepted = []
    for promo in ranked:
        review = reviews[promo["promo_id"]]
        if review["decision"] == "reject":
            continue
        enriched = dict(promo)
        enriched["automated_rank"] = promo["rank"]
        enriched["manual_decision"] = review["decision"]
        enriched["manual_rationale"] = review["rationale"]
        accepted.append(enriched)

    decision_order = {"accept": 0, "needs_review": 1}
    accepted.sort(
        key=lambda promo: (
            decision_order[promo["manual_decision"]],
            -promo["final_score"],
            promo["automated_rank"],
        )
    )
    for rank, promo in enumerate(accepted, start=1):
        promo["reviewed_rank"] = rank

    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "reviewed_shortlist.json").write_text(
        json.dumps(accepted, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    csv_fields = [
        "reviewed_rank",
        "automated_rank",
        "manual_decision",
        "promo_id",
        "episode",
        "start_timestamp",
        "end_timestamp",
        "duration_seconds",
        "hook",
        "cliffhanger",
        "why_it_works",
        "final_score",
        "confidence",
        "manual_rationale",
    ]
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=csv_fields, extrasaction="ignore")
    writer.writeheader()
    writer.writerows(accepted)
    (args.output_dir / "reviewed_shortlist.csv").write_text(buffer.getvalue(), encoding="utf-8")

    lines = [
        "# Human-Reviewed Promo Shortlist",
        "",
        "Accepted recommendations are ranked first. Candidates needing boundary/editor review follow them and are clearly labeled.",
        "",
    ]
    for promo in accepted:
        lines.extend(
            [
                f"## #{promo['reviewed_rank']} - Episode {promo['episode']} "
                f"({promo['manual_decision'].replace('_', ' ').title()})",
                "",
                f"**Segment:** {promo['start_timestamp']} to {promo['end_timestamp']} "
                f"({promo['duration_seconds']:.2f}s)",
                "",
                f"**Hook:** {promo['hook']}",
                "",
                f"**Cliffhanger:** {promo['cliffhanger']}",
                "",
                f"**Why it works:** {promo['why_it_works']}",
                "",
                f"**Manual review:** {promo['manual_rationale']}",
                "",
                f"**Automated score:** {promo['final_score']:.2f}/100",
                "",
            ]
        )
    (args.output_dir / "reviewed_shortlist.md").write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps({"reviewed_shortlist_count": len(accepted)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

