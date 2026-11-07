"""Tests for the structured Gemini evaluation contract."""

import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from promoscout.candidates import generate_candidates  # noqa: E402
from promoscout.evaluation import EvaluationValidationError, validate_evaluation  # noqa: E402
from promoscout.gemini_client import GeminiPromoEvaluator, build_candidate_input  # noqa: E402
from promoscout.parser import parse_screenplay  # noqa: E402
from test_candidates import synthetic_episode  # noqa: E402


def valid_response(candidate_id: str) -> dict:
    return {
        "candidate_id": candidate_id,
        "verdict": "suitable",
        "hook": {
            "description": "The doors explode open.",
            "evidence": "The doors burst open in an explosion.",
            "score": 9,
            "within_first_three_seconds": True,
        },
        "cliffhanger": {
            "description": "The confrontation is about to turn violent.",
            "evidence": "The guards raise their blades",
            "score": 8,
            "unresolved_at_cut": True,
        },
        "standalone": {
            "summary": "A presumed-lost heir returns to confront the people who stole his position.",
            "score": 8,
            "required_context": [],
        },
        "visual_emotional_intensity_score": 9,
        "spoiler_risk": "medium",
        "why_it_works": "It combines an immediate entrance with an unresolved confrontation.",
        "failure_reasons": [],
        "warnings": [],
        "boundary_verdict": "keep",
        "boundary_reason": "The entrance and armed response fit inside the proposed boundaries.",
        "overall_score": 86,
        "confidence": 0.9,
    }


class EvaluationContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.episode = parse_screenplay(synthetic_episode())
        self.candidate = generate_candidates(self.episode)[0]

    def test_validates_complete_response(self) -> None:
        result = validate_evaluation(valid_response(self.candidate.candidate_id), self.candidate.candidate_id)
        self.assertEqual(result.verdict, "suitable")
        self.assertEqual(result.overall_score, 86)

    def test_rejects_candidate_id_mismatch(self) -> None:
        with self.assertRaises(EvaluationValidationError):
            validate_evaluation(valid_response("wrong-id"), self.candidate.candidate_id)

    def test_rejects_score_out_of_range(self) -> None:
        response = valid_response(self.candidate.candidate_id)
        response["hook"]["score"] = 11
        with self.assertRaises(EvaluationValidationError):
            validate_evaluation(response, self.candidate.candidate_id)

    def test_input_separates_background_and_candidate(self) -> None:
        prompt = build_candidate_input(self.episode, self.candidate)
        self.assertIn("BACKGROUND - NOT VISIBLE", prompt)
        self.assertIn("PROPOSED CLIP TO EVALUATE", prompt)
        self.assertIn(self.candidate.candidate_id, prompt)

    def test_mock_transport_preserves_raw_response(self) -> None:
        calls = []

        def transport(**kwargs):
            calls.append(kwargs)
            return json.dumps(valid_response(self.candidate.candidate_id))

        workspace_temp = ROOT / "tmp" / "tests"
        workspace_temp.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=workspace_temp) as directory:
            evaluator = GeminiPromoEvaluator(
                api_key="test-key",
                model="test-model",
                raw_output_dir=directory,
                transport=transport,
            )
            run = evaluator.evaluate(self.episode, self.candidate)
            self.assertEqual(run.evaluation.candidate_id, self.candidate.candidate_id)
            self.assertTrue(run.raw_response_path.exists())
            self.assertEqual(len(calls), 1)
            self.assertNotIn("test-key", calls[0]["contents"])


if __name__ == "__main__":
    unittest.main()

