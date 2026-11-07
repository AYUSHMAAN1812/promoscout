"""Unit tests for deterministic screenplay parsing."""

import sys
import unittest
import io
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from promoscout.parser import (  # noqa: E402
    ScreenplayParseError,
    parse_screenplay,
    parse_screenplay_zip_bytes,
    seconds_to_timestamp,
    timestamp_to_seconds,
)


SAMPLE = """EPISODE NUMBER: Episode 7
EPISODE LOGLINE: A synthetic test episode.
CONTINUITY NOTES: No prior context is required.

--- SCRIPT START ---

SCENE 01
Scene heading: INT. TEST ROOM - DAY
Scene start: 00:00.00
Scene end: 00:30.00

Actions and dialogue:

**CAMERA:**
Start: (00:00.00) | End: (00:03.00)
A door bursts open.

**ALEX (Shocked):**
Start: (00:03.00) | End: (00:05.00)
"You came back."

SCENE 02
SCENE HEADING: EXT. TEST STREET - CONTINUOUS
SCENE START: 00:30.00
SCENE END: 01:00.00

ACTIONS AND DIALOGUE:

**SOUND FX:**
Start: (00:30.00) | End: (00:32.00)
A bell rings.

**ACTION:**
Start: (00:32.00) | End: (00:35.00)
Alex turns toward the sound.

--- SCRIPT END ---
"""


class TimestampTests(unittest.TestCase):
    def test_timestamp_round_trip(self) -> None:
        self.assertEqual(timestamp_to_seconds("02:03.45"), 123.45)
        self.assertEqual(seconds_to_timestamp(123.45), "02:03.45")

    def test_invalid_timestamp(self) -> None:
        with self.assertRaises(ValueError):
            timestamp_to_seconds("2 minutes")


class ScreenplayParserTests(unittest.TestCase):
    def test_parses_episode_scene_and_entries(self) -> None:
        episode = parse_screenplay(SAMPLE, "episode-007-Episode 123.txt")
        self.assertEqual(episode.episode_number, 7)
        self.assertEqual(episode.source_id, "123")
        self.assertEqual(len(episode.scenes), 2)
        self.assertEqual(len(episode.entries), 4)
        self.assertEqual(episode.duration_seconds, 60.0)
        self.assertEqual(episode.entries[1].kind, "dialogue")
        self.assertEqual(episode.entries[1].speaker, "ALEX")
        self.assertEqual(episode.error_count, 0)

    def test_detects_entry_outside_scene(self) -> None:
        bad = SAMPLE.replace(
            "Start: (00:32.00) | End: (00:35.00)",
            "Start: (00:32.00) | End: (01:05.00)",
        )
        episode = parse_screenplay(bad)
        self.assertIn("ENTRY_OUTSIDE_SCENE", {issue.code for issue in episode.issues})

    def test_rejects_missing_episode_number(self) -> None:
        with self.assertRaises(ScreenplayParseError):
            parse_screenplay("EPISODE LOGLINE: Missing number")

    def test_parses_uploaded_zip_bytes(self) -> None:
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w") as archive:
            archive.writestr("episode.txt", SAMPLE)
        episodes = parse_screenplay_zip_bytes(buffer.getvalue())
        self.assertEqual(len(episodes), 1)
        self.assertEqual(episodes[0].episode_number, 7)



if __name__ == "__main__":
    unittest.main()

