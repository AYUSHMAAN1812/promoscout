"""Resumable full-pack Gemini evaluation, ranking, and export pipeline."""

from __future__ import annotations

import argparse
import json
import sys
import time
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from promoscout.candidates import generate_show_candidates  # noqa: E402
from promoscout.evaluation import PromoEvaluation, validate_evaluation  # noqa: E402
from promoscout.exporters import export_csv, export_json, export_markdown  # noqa: E402
from promoscout.gemini_client import GeminiPromoEvaluator  # noqa: E402
from promoscout.parser import parse_screenplay_zip  # noqa: E402
from promoscout.ranking import rank_promos, score_candidate  # noqa: E402


def cached_evaluation(raw_dir: Path, candidate_id: str, model: str):
    pattern = f"{candidate_id}__{model.replace('/', '_')}__*.json"
    for path in reversed(sorted(raw_dir.glob(pattern))):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            return validate_evaluation(payload, candidate_id), path
        except Exception:
            continue
    return None


def select_candidates(all_candidates, per_episode: int):
    selected = []
    episode_numbers = sorted({candidate.episode_number for candidate in all_candidates})
    for episode_number in episode_numbers:
        episode_candidates = sorted(
            (candidate for candidate in all_candidates if candidate.episode_number == episode_number),
            key=lambda candidate: candidate.deterministic_score,
            reverse=True,
        )
        selected.extend(episode_candidates[:per_episode])
    return selected


def write_json(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("zip_path", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--per-episode", type=int, default=2)
    args = parser.parse_args()
    if not 1 <= args.per_episode <= 8:
        parser.error("--per-episode must be between 1 and 8")

    started = time.monotonic()
    episodes = parse_screenplay_zip(args.zip_path)
    episode_map = {episode.episode_number: episode for episode in episodes}
    all_candidates = generate_show_candidates(episodes)
    selected = select_candidates(all_candidates, args.per_episode)
    raw_dir = ROOT / "raw_outputs" / "gemini" / "full_run"
    evaluator = GeminiPromoEvaluator(raw_output_dir=raw_dir, max_attempts=2)

    results: list[dict] = []
    failures: list[dict] = []
    total_usage = Counter()
    checkpoint_path = args.output_dir / "evaluation_checkpoint.json"
    last_new_request_started = 0.0
    minimum_request_interval = 4.5

    for index, candidate in enumerate(selected, start=1):
        cached = cached_evaluation(raw_dir, candidate.candidate_id, evaluator.model)
        if cached:
            evaluation, raw_path = cached
            attempt_count = 0
            usage = None
            status = "cached"
        else:
            try:
                wait_seconds = minimum_request_interval - (time.monotonic() - last_new_request_started)
                if wait_seconds > 0:
                    time.sleep(wait_seconds)
                last_new_request_started = time.monotonic()
                run = evaluator.evaluate(episode_map[candidate.episode_number], candidate)
                evaluation = run.evaluation
                raw_path = run.raw_response_path
                attempt_count = run.attempt_count
                usage = run.usage_metadata
                status = "new"
            except Exception as exc:
                failures.append(
                    {
                        "candidate_id": candidate.candidate_id,
                        "episode": candidate.episode_number,
                        "error": f"{type(exc).__name__}: {exc}",
                    }
                )
                print(f"[{index}/{len(selected)}] FAIL {candidate.candidate_id}: {exc}", flush=True)
                write_json(
                    checkpoint_path,
                    {"complete": False, "results": results, "failures": failures},
                )
                continue

        if usage:
            for key, value in usage.items():
                if isinstance(value, (int, float)):
                    total_usage[key] += value
        results.append(
            {
                "candidate": candidate.to_dict(),
                "evaluation": evaluation.to_dict(),
                "model": evaluator.model,
                "status": status,
                "attempt_count": attempt_count,
                "usage_metadata": usage,
                "raw_response_path": str(raw_path.relative_to(ROOT)),
            }
        )
        write_json(
            checkpoint_path,
            {"complete": False, "results": results, "failures": failures},
        )
        print(
            f"[{index}/{len(selected)}] OK {candidate.candidate_id} "
            f"{evaluation.verdict} {evaluation.overall_score}",
            flush=True,
        )

    scored = []
    for result in results:
        candidate_data = result["candidate"]
        candidate = next(
            item for item in selected if item.candidate_id == candidate_data["candidate_id"]
        )
        evaluation = validate_evaluation(result["evaluation"], candidate.candidate_id)
        scored.append(score_candidate(candidate, evaluation))
    ranked = rank_promos(scored)

    decision_counts = Counter(item.decision for item in scored)
    verdict_counts = Counter(result["evaluation"]["verdict"] for result in results)
    episodes_evaluated = sorted({result["candidate"]["episode_number"] for result in results})
    elapsed = round(time.monotonic() - started, 2)
    summary = {
        "model": evaluator.model,
        "episodes_parsed": len(episodes),
        "episodes_evaluated": len(episodes_evaluated),
        "episode_numbers_evaluated": episodes_evaluated,
        "deterministic_candidates": len(all_candidates),
        "selected_for_gemini": len(selected),
        "successful_evaluations": len(results),
        "failed_evaluations": len(failures),
        "verdict_counts": dict(sorted(verdict_counts.items())),
        "decision_counts": dict(sorted(decision_counts.items())),
        "primary_ranked_promos": len(ranked),
        "usage_metadata_records": sum(
            result.get("usage_metadata") is not None for result in results
        ),
        "total_usage_metadata": dict(total_usage),
        "elapsed_seconds": elapsed,
    }

    write_json(checkpoint_path, {"complete": True, "results": results, "failures": failures})
    write_json(args.output_dir / "evaluations.json", results)
    write_json(args.output_dir / "failures.json", failures)
    write_json(args.output_dir / "scored_all.json", [item.to_dict() for item in scored])
    (args.output_dir / "ranked_promos.json").write_text(export_json(ranked), encoding="utf-8")
    (args.output_dir / "ranked_promos.csv").write_text(export_csv(ranked), encoding="utf-8")
    (args.output_dir / "ranked_promos.md").write_text(export_markdown(ranked), encoding="utf-8")

    summary_lines = [
        "# Step 7 Full-Pack Run Summary",
        "",
        f"- Model: `{summary['model']}`",
        f"- Episodes parsed: {summary['episodes_parsed']}",
        f"- Episodes with successful Gemini coverage: {summary['episodes_evaluated']}",
        f"- Deterministic candidates generated: {summary['deterministic_candidates']}",
        f"- Candidates selected for Gemini: {summary['selected_for_gemini']}",
        f"- Successful evaluations: {summary['successful_evaluations']}",
        f"- Failed evaluations: {summary['failed_evaluations']}",
        f"- Primary ranked promos after safety and diversity rules: {summary['primary_ranked_promos']}",
        f"- Runtime: {summary['elapsed_seconds']:.2f} seconds",
        "",
        "## Gemini verdicts",
        "",
    ]
    summary_lines.extend(f"- {key}: {value}" for key, value in summary["verdict_counts"].items())
    summary_lines.extend(["", "## Final deterministic decisions", ""])
    summary_lines.extend(f"- {key}: {value}" for key, value in summary["decision_counts"].items())
    summary_lines.extend(
        [
            "",
            "## Usage metadata",
            "",
            f"Usage metadata captured for {summary['usage_metadata_records']} of "
            f"{summary['successful_evaluations']} evaluations. Cached raw responses may not retain "
            "API-envelope usage fields.",
            "",
        ]
    )
    if total_usage:
        summary_lines.extend(f"- {key}: {value}" for key, value in sorted(total_usage.items()))
    else:
        summary_lines.append("No usage metadata was available for the responses in this process.")
    summary_lines.extend(
        [
            "",
            "The candidate selection stage covered every episode before Gemini evaluation. Two candidates per episode were chosen to balance recall, free-tier constraints, and runtime.",
            "",
        ]
    )
    (args.output_dir / "run_summary.md").write_text("\n".join(summary_lines), encoding="utf-8")
    print(json.dumps(summary, indent=2), flush=True)
    return 0 if not failures else 2


if __name__ == "__main__":
    raise SystemExit(main())

