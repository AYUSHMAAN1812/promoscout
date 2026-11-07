"""Tests for deterministic post-validation and ranking."""

import sys
import unittest
from dataclasses import replace
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from promoscout.candidates import generate_candidates  # noqa: E402
from promoscout.evaluation import validate_evaluation  # noqa: E402
from promoscout.parser import parse_screenplay  # noqa: E402
from promoscout.ranking import RankingConfig, rank_promos, score_candidate  # noqa: E402
from test_candidates import synthetic_episode  # noqa: E402
from test_evaluation import valid_response  # noqa: E402


class RankingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.episode = parse_screenplay(synthetic_episode())
        self.candidates = generate_candidates(self.episode)

    def evaluation(self, candidate, **updates):
        raw = valid_response(candidate.candidate_id)
        raw.update(updates)
        return validate_evaluation(raw, candidate.candidate_id)

    def test_accepts_strong_valid_candidate(self) -> None:
        candidate = self.candidates[0]
        scored = score_candidate(candidate, self.evaluation(candidate))
        self.assertEqual(scored.decision, "accepted")
        self.assertGreaterEqual(scored.final_score, 70)

    def test_rejects_false_cliffhanger_despite_borderline_verdict(self) -> None:
        candidate = self.candidates[0]
        raw = valid_response(candidate.candidate_id)
        raw["verdict"] = "borderline"
        raw["cliffhanger"]["score"] = 4
        raw["cliffhanger"]["unresolved_at_cut"] = False
        evaluation = validate_evaluation(raw, candidate.candidate_id)
        scored = score_candidate(candidate, evaluation)
        self.assertEqual(scored.decision, "rejected")
        self.assertTrue(any("Cliffhanger" in reason or "unresolved" in reason for reason in scored.rejection_reasons))

    def test_rejects_low_standalone_clarity(self) -> None:
        candidate = self.candidates[0]
        raw = valid_response(candidate.candidate_id)
        raw["standalone"]["score"] = 4
        evaluation = validate_evaluation(raw, candidate.candidate_id)
        self.assertEqual(score_candidate(candidate, evaluation).decision, "rejected")

    def test_ranking_keeps_stronger_overlapping_candidate(self) -> None:
        first = self.candidates[0]
        second = replace(
            first,
            candidate_id=first.candidate_id + "-weaker",
            start_seconds=first.start_seconds + 1,
            end_seconds=first.end_seconds - 1,
        )
        first_scored = score_candidate(first, self.evaluation(first))
        second_raw = valid_response(second.candidate_id)
        second_raw["overall_score"] = 75
        second_raw["hook"]["score"] = 7
        second_scored = score_candidate(second, validate_evaluation(second_raw, second.candidate_id))
        ranked = rank_promos([second_scored, first_scored])
        self.assertEqual(len(ranked), 1)
        self.assertEqual(ranked[0].candidate.candidate_id, first.candidate_id)

    def test_story_arc_cap_diversifies_primary_ranking(self) -> None:
        source = self.candidates[0]
        scored = []
        for episode_number in range(1, 5):
            candidate = replace(
                source,
                candidate_id=f"arc-candidate-{episode_number}",
                episode_number=episode_number,
            )
            scored.append(score_candidate(candidate, self.evaluation(candidate)))
        ranked = rank_promos(scored, RankingConfig(max_per_story_arc=2))
        self.assertEqual(len(ranked), 2)


if __name__ == "__main__":
    unittest.main()

