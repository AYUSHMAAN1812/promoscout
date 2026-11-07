"""Tests for editor-ready result exports."""

import csv
import io
import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from promoscout.candidates import generate_candidates  # noqa: E402
from promoscout.evaluation import validate_evaluation  # noqa: E402
from promoscout.exporters import export_csv, export_json, export_markdown  # noqa: E402
from promoscout.parser import parse_screenplay  # noqa: E402
from promoscout.ranking import rank_promos, score_candidate  # noqa: E402
from test_candidates import synthetic_episode  # noqa: E402
from test_evaluation import valid_response  # noqa: E402


class ExporterTests(unittest.TestCase):
    def setUp(self) -> None:
        episode = parse_screenplay(synthetic_episode())
        candidate = generate_candidates(episode)[0]
        evaluation = validate_evaluation(valid_response(candidate.candidate_id), candidate.candidate_id)
        self.ranked = rank_promos([score_candidate(candidate, evaluation)])

    def test_json_export_contains_required_fields(self) -> None:
        records = json.loads(export_json(self.ranked, {self.ranked[0].candidate.candidate_id: "accept"}))
        self.assertEqual(records[0]["episode"], 1)
        self.assertIn("hook", records[0])
        self.assertIn("cliffhanger", records[0])
        self.assertEqual(records[0]["editor_review"], "accept")

    def test_csv_export_is_readable(self) -> None:
        rows = list(csv.DictReader(io.StringIO(export_csv(self.ranked))))
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["rank"], "1")

    def test_markdown_export_is_readable(self) -> None:
        result = export_markdown(self.ranked)
        self.assertIn("Episode 1", result)
        self.assertIn("**Hook:**", result)


if __name__ == "__main__":
    unittest.main()

