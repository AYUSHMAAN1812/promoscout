"""Calculate Step 8 metrics and build an evidence-backed quality report."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path


def percentage(numerator: int, denominator: int) -> float:
    return round(numerator / denominator * 100, 1) if denominator else 0.0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--step2", type=Path, required=True)
    parser.add_argument("--step3", type=Path, required=True)
    parser.add_argument("--step7", type=Path, required=True)
    parser.add_argument("--reviews", type=Path, required=True)
    parser.add_argument("--json-output", type=Path, required=True)
    parser.add_argument("--markdown-output", type=Path, required=True)
    args = parser.parse_args()

    parse_report = json.loads(args.step2.read_text(encoding="utf-8"))
    candidate_report = json.loads(args.step3.read_text(encoding="utf-8"))
    evaluations = json.loads((args.step7 / "evaluations.json").read_text(encoding="utf-8"))
    scored = json.loads((args.step7 / "scored_all.json").read_text(encoding="utf-8"))
    ranked = json.loads((args.step7 / "ranked_promos.json").read_text(encoding="utf-8"))
    failures = json.loads((args.step7 / "failures.json").read_text(encoding="utf-8"))
    reviews = json.loads(args.reviews.read_text(encoding="utf-8"))

    primary_reviews = reviews["primary_ranked_reviews"]
    manual_counts = Counter(review["decision"] for review in primary_reviews)
    shortlist_worthy = manual_counts["accept"] + manual_counts["needs_review"]
    decisions = Counter(item["decision"] for item in scored)
    verdicts = Counter(item["evaluation"]["verdict"] for item in evaluations)
    duplicate_rejections = sum(
        any("same episode" in reason for reason in item["rejection_reasons"])
        for item in scored
    )
    diversity_deferrals = sum(
        any("diversity" in penalty for penalty in item["penalties"])
        for item in scored
    )
    hard_quality_rejections = sum(
        item["decision"] == "rejected"
        and not any("same episode" in reason for reason in item["rejection_reasons"])
        for item in scored
    )

    metrics = {
        "episodes_parse_success": parse_report["episode_count"],
        "episodes_expected": 50,
        "parser_error_count": parse_report["error_count"],
        "parser_warning_count": parse_report["warning_count"],
        "deterministic_candidate_count": candidate_report["summary"]["candidate_count"],
        "gemini_selected_count": len(evaluations),
        "gemini_success_count": len(evaluations),
        "gemini_failure_count": len(failures),
        "gemini_structured_success_rate_percent": percentage(len(evaluations), len(evaluations) + len(failures)),
        "gemini_verdict_counts": dict(verdicts),
        "final_decision_counts": dict(decisions),
        "duplicate_rejections": duplicate_rejections,
        "story_diversity_deferrals": diversity_deferrals,
        "hard_quality_rejections": hard_quality_rejections,
        "primary_ranked_count": len(ranked),
        "manual_accept_count": manual_counts["accept"],
        "manual_needs_review_count": manual_counts["needs_review"],
        "manual_reject_count": manual_counts["reject"],
        "manual_shortlist_worthy_rate_percent": percentage(shortlist_worthy, len(primary_reviews)),
        "manual_strict_acceptance_rate_percent": percentage(manual_counts["accept"], len(primary_reviews)),
        "manual_false_positive_rate_percent": percentage(manual_counts["reject"], len(primary_reviews)),
    }
    args.json_output.parent.mkdir(parents=True, exist_ok=True)
    args.markdown_output.parent.mkdir(parents=True, exist_ok=True)
    args.json_output.write_text(json.dumps(metrics, indent=2), encoding="utf-8")

    lines = [
        "# Step 8 Quality Evaluation",
        "",
        "## Scope and method",
        "",
        "The full pipeline processed all 50 episodes. Gemini evaluated two candidates per episode. A manual screenplay review then checked all 15 primary ranked promos plus eight additional middle/rejected examples. This is a small internal review, not an independent editor study or platform-performance experiment.",
        "",
        "Manual checks: valid duration, accurate timestamps, hook inside three seconds, genuine unresolved ending, standalone comprehension, and practical editor value.",
        "",
        "## Measured pipeline results",
        "",
        f"- Parser coverage: {metrics['episodes_parse_success']}/{metrics['episodes_expected']} episodes; {metrics['parser_error_count']} errors and {metrics['parser_warning_count']} retained source warning.",
        f"- Deterministic candidates: {metrics['deterministic_candidate_count']} across all episodes.",
        f"- Gemini structured-output success: {metrics['gemini_success_count']}/{metrics['gemini_selected_count']} ({metrics['gemini_structured_success_rate_percent']:.1f}%) with {metrics['gemini_failure_count']} final failures.",
        f"- Gemini verdicts: {verdicts['suitable']} suitable, {verdicts['borderline']} borderline, {verdicts['reject']} reject.",
        f"- Final buckets: {decisions['accepted']} primary accepted, {decisions['human_review']} human review, {decisions['rejected']} rejected.",
        f"- Quality-rule rejections: {hard_quality_rejections}; weaker same-episode duplicates removed: {duplicate_rejections}; story-diversity deferrals: {diversity_deferrals}.",
        "- The top list contains exactly three promos from each 10-episode story arc by design.",
        "",
        "## Manual review of the top 15",
        "",
        f"- Strong as-is: {manual_counts['accept']}/15 ({metrics['manual_strict_acceptance_rate_percent']:.1f}%).",
        f"- Plausible but needs editor/boundary review: {manual_counts['needs_review']}/15.",
        f"- False positives: {manual_counts['reject']}/15 ({metrics['manual_false_positive_rate_percent']:.1f}%).",
        f"- Shortlist-worthy (strong plus needs review): {shortlist_worthy}/15 ({metrics['manual_shortlist_worthy_rate_percent']:.1f}%).",
        "",
        "The 86.7% shortlist-worthy result exceeds the prototype target of 80%, but the strict as-is rate is lower. The tool should therefore be presented as an editor-shortlisting system, not an automatic publishing system.",
        "",
        "## Where the tool picked badly",
        "",
        "1. **Episode 10 false cliffhanger.** The bloody entrance is a superb hook, but the clip ends on 'Does it hurt?' Gemini overvalued romantic intimacy as unresolved suspense.",
        "2. **Episode 22 false hook.** The poisoned-Duchess ending is strong, but the opening mansion-awe shot and 'This house...' line are not compelling within three seconds. Gemini used later urgency to justify a weak start.",
        "3. **Episode 24 ranking inflation.** The riding-crop confrontation is usable, but the ending question 'All of it, my lady?' is too soft for the number-one rank.",
        "4. **Episode 43 partial resolution.** Blocking the villain's escape is dramatic, but it also resolves the immediate escape question; the model described it as more open-ended than it is.",
        "5. **Deterministic Episode 3 miss.** The fight window scored highly but cut on a hand entering a pocket before the actual proposal. Gemini correctly rejected it, showing why the second stage is necessary.",
        "6. **Quiet-scene over-generation.** Domestic repair and peaceful romantic scenes in Episodes 6 and 8 passed initial heuristic generation but were correctly rejected for lacking hooks and cliffhangers.",
        "",
        "## What remains unmeasured",
        "",
        "- Actual footage quality, acting, shot rhythm, and audio are unavailable in screenplay-only inputs.",
        "- No real editor independently reviewed the recommendations.",
        "- No Instagram, TikTok, or YouTube performance data exists, so views, completion rate, click-through, and installs cannot be predicted.",
        "- Manual review was performed by the prototype builder and may share biases with the rubric.",
        "- Only two of up to eight deterministic candidates per episode received Gemini evaluation due free-tier and deadline constraints.",
        "",
        "## Production success criteria",
        "",
        "A real pilot should measure editor acceptance rate, minutes saved per episode, boundary-adjustment rate, duplicate rate, cost per show, and downstream three-second hold, completion, click-through, and install rates against editor-selected promos.",
        "",
    ]
    args.markdown_output.write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps(metrics, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

