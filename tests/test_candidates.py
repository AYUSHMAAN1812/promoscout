"""Tests for deterministic promo candidate generation."""

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from promoscout.candidates import CandidateConfig, generate_candidates  # noqa: E402
from promoscout.parser import parse_screenplay  # noqa: E402


def synthetic_episode() -> str:
    lines = [
        "EPISODE NUMBER: Episode 1",
        "EPISODE LOGLINE: A secret is revealed during an attack.",
        "CONTINUITY NOTES: Synthetic test.",
        "",
        "--- SCRIPT START ---",
        "",
        "SCENE 01",
        "Scene heading: INT. HALL - NIGHT",
        "Scene start: 00:00.00",
        "Scene end: 01:00.00",
        "",
        "Actions and dialogue:",
        "",
    ]
    events = [
        (0, 4, "ACTION", "The doors burst open in an explosion."),
        (4, 10, "MARA (Shocked)", '"Who are you?"'),
        (10, 20, "ACTION", "A stranger walks through the smoke."),
        (20, 28, "STRANGER (Cold)", '"You already know the truth."'),
        (28, 38, "ACTION", "He reveals the stolen royal crest."),
        (38, 48, "MARA (Terrified)", '"The rightful heir is alive?"'),
        (48, 56, "STRANGER (Threatening)", '"Now we settle what you stole."'),
        (56, 60, "CAMERA", "The guards raise their blades before an abrupt cut to black cliffhanger."),
    ]
    for start, end, label, text in events:
        lines.extend(
            [
                f"**{label}:**",
                f"Start: (00:{start:02d}.00) | End: (01:00.00)" if end == 60 else f"Start: (00:{start:02d}.00) | End: (00:{end:02d}.00)",
                text,
                "",
            ]
        )
    lines.append("--- SCRIPT END ---")
    return "\n".join(lines)


class CandidateGenerationTests(unittest.TestCase):
    def test_candidates_are_valid_and_source_grounded(self) -> None:
        episode = parse_screenplay(synthetic_episode())
        candidates = generate_candidates(episode)
        self.assertTrue(candidates)
        for candidate in candidates:
            self.assertGreaterEqual(candidate.duration_seconds, 20)
            self.assertLessEqual(candidate.duration_seconds, 60)
            self.assertTrue(candidate.source_entries)
            self.assertTrue(candidate.candidate_id.startswith("E001-"))

    def test_candidate_limit_is_respected(self) -> None:
        episode = parse_screenplay(synthetic_episode())
        candidates = generate_candidates(
            episode, CandidateConfig(max_candidates_per_episode=2, minimum_score=0)
        )
        self.assertLessEqual(len(candidates), 2)

    def test_top_candidate_has_hook_and_cliff_signals(self) -> None:
        episode = parse_screenplay(synthetic_episode())
        top = generate_candidates(episode)[0]
        self.assertTrue(top.hook_signals)
        self.assertTrue(top.cliffhanger_signals)


if __name__ == "__main__":
    unittest.main()

