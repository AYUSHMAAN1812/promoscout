"""Run a small strong/weak Gemini sample before approving full evaluation."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from promoscout.candidates import generate_show_candidates  # noqa: E402
from promoscout.evaluation import validate_evaluation  # noqa: E402
from promoscout.gemini_client import GeminiPromoEvaluator  # noqa: E402
from promoscout.parser import parse_screenplay_zip, seconds_to_timestamp  # noqa: E402


STRONG_EPISODES = (3, 18, 42, 50)


def cached_result(raw_dir: Path, candidate, model: str):
    matches = sorted(raw_dir.glob(f"{candidate.candidate_id}__{model.replace('/', '_')}__*.json"))
    for path in reversed(matches):
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
            evaluation = validate_evaluation(raw, candidate.candidate_id)
            return evaluation, path
        except Exception:
            continue
    return None


def write_checkpoint(path: Path, results: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps({"sample_size": len(results), "complete": False, "results": results}, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("zip_path", type=Path)
    parser.add_argument("--json-output", type=Path, required=True)
    parser.add_argument("--markdown-output", type=Path, required=True)
    args = parser.parse_args()

    episodes = parse_screenplay_zip(args.zip_path)
    episode_map = {episode.episode_number: episode for episode in episodes}
    all_candidates = generate_show_candidates(episodes)
    selected = []
    for episode_number in STRONG_EPISODES:
        episode_candidates = sorted(
            (candidate for candidate in all_candidates if candidate.episode_number == episode_number),
            key=lambda candidate: candidate.deterministic_score,
            reverse=True,
        )
        selected.append(episode_candidates[0])

    # Add two lowest-scoring candidates to test whether Gemini rejects weak heuristic windows.
    selected_ids = {candidate.candidate_id for candidate in selected}
    weak = sorted(
        (candidate for candidate in all_candidates if candidate.candidate_id not in selected_ids),
        key=lambda candidate: candidate.deterministic_score,
    )[:2]
    selected.extend(weak)

    raw_dir = ROOT / "raw_outputs" / "gemini" / "step4_sample"
    evaluator = GeminiPromoEvaluator(raw_output_dir=raw_dir)
    results = []
    for candidate in selected:
        episode = episode_map[candidate.episode_number]
        cached = cached_result(raw_dir, candidate, evaluator.model)
        if cached:
            evaluation, raw_path = cached
            attempt_count = 0
        else:
            run = evaluator.evaluate(episode, candidate)
            evaluation = run.evaluation
            raw_path = run.raw_response_path
            attempt_count = run.attempt_count
        results.append(
            {
                "candidate": candidate.to_dict(),
                "evaluation": evaluation.to_dict(),
                "model": evaluator.model,
                "attempt_count": attempt_count,
                "raw_response_path": str(raw_path.relative_to(ROOT)),
            }
        )
        write_checkpoint(args.json_output, results)

    payload = {"sample_size": len(results), "complete": True, "results": results}
    args.json_output.parent.mkdir(parents=True, exist_ok=True)
    args.markdown_output.parent.mkdir(parents=True, exist_ok=True)
    args.json_output.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    lines = [
        "# Step 4 Gemini Sample Evaluation",
        "",
        f"Model: `{evaluator.model}`",
        f"Candidates evaluated: {len(results)}",
        "",
        "The sample deliberately contains four high-scoring deterministic candidates and two low-scoring candidates.",
        "",
        "| Episode | Window | Heuristic | Gemini | Verdict | Hook | Cliffhanger | Standalone | Boundary |",
        "|---:|---:|---:|---:|---|---:|---:|---:|---|",
    ]
    for result in results:
        candidate = result["candidate"]
        evaluation = result["evaluation"]
        lines.append(
            f"| {candidate['episode_number']} | {seconds_to_timestamp(candidate['start_seconds'])}-"
            f"{seconds_to_timestamp(candidate['end_seconds'])} | {candidate['deterministic_score']:.2f} | "
            f"{evaluation['overall_score']} | {evaluation['verdict']} | "
            f"{evaluation['hook']['score']} | {evaluation['cliffhanger']['score']} | "
            f"{evaluation['standalone']['score']} | {evaluation['boundary_verdict']} |"
        )

    lines.extend(["", "## Detailed judgments", ""])
    for result in results:
        candidate = result["candidate"]
        evaluation = result["evaluation"]
        lines.extend(
            [
                f"### {candidate['candidate_id']}",
                "",
                f"- Verdict: {evaluation['verdict']} ({evaluation['overall_score']}/100)",
                f"- Hook: {evaluation['hook']['description']}",
                f"- Cliffhanger: {evaluation['cliffhanger']['description']}",
                f"- Why it works: {evaluation['why_it_works'] or 'Not applicable'}",
                f"- Failure reasons: {'; '.join(evaluation['failure_reasons']) or 'None'}",
                f"- Warnings: {'; '.join(evaluation['warnings']) or 'None'}",
                f"- Boundary: {evaluation['boundary_verdict']} - {evaluation['boundary_reason']}",
                f"- Raw response: `{result['raw_response_path']}`",
                "",
            ]
        )
    args.markdown_output.write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps({"model": evaluator.model, "sample_size": len(results)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

