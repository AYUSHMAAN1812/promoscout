"""Deterministic parser for Kuku timestamped screenplay text files."""

from __future__ import annotations

import re
import zipfile
from io import BytesIO
from pathlib import Path

from .models import Episode, Scene, ScriptEntry, ValidationIssue


TIMESTAMP_PATTERN = r"(?P<minutes>\d{1,3}):(?P<seconds>\d{2})\.(?P<centiseconds>\d{2})"
TIMESTAMP_RE = re.compile(rf"^{TIMESTAMP_PATTERN}$")
ENTRY_TIMES_RE = re.compile(
    r"^Start:\s*\((?P<minutes>\d{1,3}):(?P<seconds>\d{2})\.(?P<centiseconds>\d{2})\)"
    r"\s*\|\s*End:\s*\((?P<end_minutes>\d{1,3}):(?P<end_seconds>\d{2})\."
    r"(?P<end_centiseconds>\d{2})\)\s*$",
    re.IGNORECASE,
)
SCENE_RE = re.compile(r"^SCENE\s+(\d+)\s*$", re.IGNORECASE)
ENTRY_LABEL_RE = re.compile(r"^\*\*(.+?):\*\*\s*$")
SOURCE_ID_RE = re.compile(r"Episode\s+(\d+)\.txt$", re.IGNORECASE)


class ScreenplayParseError(ValueError):
    """Raised when a screenplay cannot be represented as an episode."""


def timestamp_to_seconds(value: str) -> float:
    match = TIMESTAMP_RE.fullmatch(value.strip().strip("()"))
    if not match:
        raise ValueError(f"Invalid timestamp: {value!r}")
    seconds = (
        int(match.group("minutes")) * 60
        + int(match.group("seconds"))
        + int(match.group("centiseconds")) / 100
    )
    return round(seconds, 2)


def seconds_to_timestamp(value: float) -> str:
    centiseconds = int(round(value * 100))
    minutes, remainder = divmod(centiseconds, 6000)
    seconds, fraction = divmod(remainder, 100)
    return f"{minutes:02d}:{seconds:02d}.{fraction:02d}"


def _metadata_value(lines: list[str], label: str) -> str | None:
    pattern = re.compile(rf"^{re.escape(label)}\s*:\s*(.*)$", re.IGNORECASE)
    for line in lines:
        match = pattern.match(line.strip())
        if match:
            return match.group(1).strip()
    return None


def _next_nonempty(lines: list[str], start: int, stop: int) -> tuple[int, str] | None:
    for index in range(start, stop):
        if lines[index].strip():
            return index, lines[index].strip()
    return None


def _entry_kind(label: str) -> tuple[str, str | None]:
    normalized = label.strip()
    upper = normalized.upper()
    if upper == "CAMERA":
        return "camera", None
    if upper == "ACTION":
        return "action", None
    if upper in {"SOUND", "SOUND FX", "SFX"}:
        return "sound", None
    speaker = re.split(r"\s*\(", normalized, maxsplit=1)[0].strip()
    if speaker:
        return "dialogue", speaker
    return "other", None


def _parse_entry_times(line: str) -> tuple[float, float] | None:
    match = ENTRY_TIMES_RE.fullmatch(line.strip())
    if not match:
        return None
    start = (
        int(match.group("minutes")) * 60
        + int(match.group("seconds"))
        + int(match.group("centiseconds")) / 100
    )
    end = (
        int(match.group("end_minutes")) * 60
        + int(match.group("end_seconds"))
        + int(match.group("end_centiseconds")) / 100
    )
    return round(start, 2), round(end, 2)


def _parse_scene(
    lines: list[str], start_index: int, end_index: int, issues: list[ValidationIssue]
) -> Scene | None:
    scene_match = SCENE_RE.match(lines[start_index].strip())
    if not scene_match:
        return None
    scene_number = int(scene_match.group(1))

    heading: str | None = None
    scene_start: float | None = None
    scene_end: float | None = None

    for index in range(start_index + 1, min(end_index, start_index + 12)):
        stripped = lines[index].strip()
        metadata_match = re.match(
            r"^Scene\s+(heading|start|end)\s*:\s*(.*)$", stripped, re.IGNORECASE
        )
        if not metadata_match:
            continue
        field, value = metadata_match.groups()
        field = field.lower()
        if field == "heading":
            heading = value.strip()
        elif field == "start":
            try:
                scene_start = timestamp_to_seconds(value)
            except ValueError:
                issues.append(
                    ValidationIssue(
                        "INVALID_SCENE_START",
                        f"Scene {scene_number} has invalid start timestamp {value!r}.",
                        "error",
                        index + 1,
                    )
                )
        elif field == "end":
            try:
                scene_end = timestamp_to_seconds(value)
            except ValueError:
                issues.append(
                    ValidationIssue(
                        "INVALID_SCENE_END",
                        f"Scene {scene_number} has invalid end timestamp {value!r}.",
                        "error",
                        index + 1,
                    )
                )

    missing = [
        name
        for name, value in (
            ("heading", heading),
            ("start", scene_start),
            ("end", scene_end),
        )
        if value is None
    ]
    if missing:
        issues.append(
            ValidationIssue(
                "INCOMPLETE_SCENE",
                f"Scene {scene_number} is missing: {', '.join(missing)}.",
                "error",
                start_index + 1,
            )
        )
        return None

    entries: list[ScriptEntry] = []
    index = start_index + 1
    while index < end_index:
        label_match = ENTRY_LABEL_RE.match(lines[index].strip())
        if not label_match:
            index += 1
            continue

        label = label_match.group(1).strip()
        timing_line = _next_nonempty(lines, index + 1, end_index)
        if timing_line is None:
            issues.append(
                ValidationIssue(
                    "ENTRY_WITHOUT_TIMES",
                    f"Entry {label!r} has no timing line.",
                    "warning",
                    index + 1,
                )
            )
            index += 1
            continue

        timing_index, timing_text = timing_line
        times = _parse_entry_times(timing_text)
        if times is None:
            issues.append(
                ValidationIssue(
                    "ENTRY_WITHOUT_TIMES",
                    f"Entry {label!r} is not followed by a valid timing line.",
                    "warning",
                    index + 1,
                )
            )
            index += 1
            continue

        text_start = timing_index + 1
        text_end = text_start
        while text_end < end_index:
            if ENTRY_LABEL_RE.match(lines[text_end].strip()) or SCENE_RE.match(
                lines[text_end].strip()
            ):
                break
            if lines[text_end].strip() == "--- SCRIPT END ---":
                break
            text_end += 1
        text = "\n".join(line.strip() for line in lines[text_start:text_end]).strip()
        if not text:
            issues.append(
                ValidationIssue(
                    "EMPTY_ENTRY_TEXT",
                    f"Entry {label!r} has no content.",
                    "warning",
                    index + 1,
                )
            )

        entry_start, entry_end = times
        kind, speaker = _entry_kind(label)
        entries.append(
            ScriptEntry(
                label=label,
                kind=kind,  # type: ignore[arg-type]
                start_seconds=entry_start,
                end_seconds=entry_end,
                text=text,
                source_line=index + 1,
                speaker=speaker,
            )
        )
        index = text_end

    return Scene(
        number=scene_number,
        heading=heading or "",
        start_seconds=scene_start or 0.0,
        end_seconds=scene_end or 0.0,
        source_line=start_index + 1,
        entries=entries,
    )


def _validate_episode(episode: Episode) -> None:
    issues = episode.issues
    seen_scene_numbers: set[int] = set()
    previous_scene_start = -1.0

    for scene in episode.scenes:
        if scene.number in seen_scene_numbers:
            issues.append(
                ValidationIssue(
                    "DUPLICATE_SCENE_NUMBER",
                    f"Scene number {scene.number} occurs more than once.",
                    "error",
                    scene.source_line,
                )
            )
        seen_scene_numbers.add(scene.number)
        if scene.start_seconds >= scene.end_seconds:
            issues.append(
                ValidationIssue(
                    "INVALID_SCENE_RANGE",
                    f"Scene {scene.number} does not have a positive duration.",
                    "error",
                    scene.source_line,
                )
            )
        if scene.start_seconds < previous_scene_start:
            issues.append(
                ValidationIssue(
                    "SCENES_OUT_OF_ORDER",
                    f"Scene {scene.number} starts before the preceding scene.",
                    "error",
                    scene.source_line,
                )
            )
        previous_scene_start = scene.start_seconds

        for entry in scene.entries:
            if entry.start_seconds >= entry.end_seconds:
                issues.append(
                    ValidationIssue(
                        "INVALID_ENTRY_RANGE",
                        f"Entry {entry.label!r} does not have a positive duration.",
                        "error",
                        entry.source_line,
                    )
                )
            tolerance = 0.05
            if entry.start_seconds < scene.start_seconds - tolerance or entry.end_seconds > scene.end_seconds + tolerance:
                issues.append(
                    ValidationIssue(
                        "ENTRY_OUTSIDE_SCENE",
                        f"Entry {entry.label!r} ({seconds_to_timestamp(entry.start_seconds)}-"
                        f"{seconds_to_timestamp(entry.end_seconds)}) falls outside scene {scene.number} "
                        f"({seconds_to_timestamp(scene.start_seconds)}-{seconds_to_timestamp(scene.end_seconds)}).",
                        "warning",
                        entry.source_line,
                    )
                )

    if not episode.scenes:
        issues.append(
            ValidationIssue("NO_SCENES", "No valid scenes were parsed.", "error", None)
        )
    if not episode.entries:
        issues.append(
            ValidationIssue("NO_ENTRIES", "No timestamped entries were parsed.", "error", None)
        )


def parse_screenplay(text: str, source_name: str = "input.txt") -> Episode:
    """Parse one screenplay text document into a validated Episode."""

    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = normalized.split("\n")
    issues: list[ValidationIssue] = []

    number_text = _metadata_value(lines[:20], "EPISODE NUMBER")
    number_match = re.search(r"(\d+)", number_text or "")
    if not number_match:
        raise ScreenplayParseError(f"{source_name}: missing or invalid EPISODE NUMBER")
    episode_number = int(number_match.group(1))

    logline = _metadata_value(lines[:20], "EPISODE LOGLINE") or ""
    continuity = _metadata_value(lines[:20], "CONTINUITY NOTES") or ""
    if not logline:
        issues.append(ValidationIssue("MISSING_LOGLINE", "Episode logline is missing."))
    if not continuity:
        issues.append(
            ValidationIssue("MISSING_CONTINUITY_NOTES", "Continuity notes are missing.")
        )
    if "\ufffd" in normalized:
        issues.append(
            ValidationIssue(
                "SOURCE_REPLACEMENT_CHARACTER",
                "Source contains Unicode replacement characters; original punctuation cannot be recovered safely.",
            )
        )

    scene_starts = [index for index, line in enumerate(lines) if SCENE_RE.match(line.strip())]
    scenes: list[Scene] = []
    for offset, scene_start in enumerate(scene_starts):
        scene_end = scene_starts[offset + 1] if offset + 1 < len(scene_starts) else len(lines)
        scene = _parse_scene(lines, scene_start, scene_end, issues)
        if scene is not None:
            scenes.append(scene)

    source_match = SOURCE_ID_RE.search(Path(source_name).name)
    source_id = source_match.group(1) if source_match else None
    episode = Episode(
        episode_number=episode_number,
        source_id=source_id,
        source_name=source_name,
        logline=logline,
        continuity_notes=continuity,
        scenes=scenes,
        issues=issues,
        raw_text=normalized,
    )
    _validate_episode(episode)
    return episode


def _decode_screenplay(data: bytes, source_name: str) -> str:
    for encoding in ("utf-8-sig", "utf-8", "cp1252"):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    raise ScreenplayParseError(f"{source_name}: unsupported text encoding")


def parse_screenplay_zip(path: str | Path) -> list[Episode]:
    """Parse all screenplay text files in a ZIP archive."""

    archive_path = Path(path)
    with zipfile.ZipFile(archive_path) as archive:
        return _parse_zip_archive(archive, str(archive_path))


def parse_screenplay_zip_bytes(data: bytes, source_name: str = "upload.zip") -> list[Episode]:
    """Parse screenplay text files directly from uploaded ZIP bytes."""

    try:
        with zipfile.ZipFile(BytesIO(data)) as archive:
            return _parse_zip_archive(archive, source_name)
    except zipfile.BadZipFile as exc:
        raise ScreenplayParseError(f"{source_name}: invalid ZIP archive") from exc


def _parse_zip_archive(archive: zipfile.ZipFile, source_name: str) -> list[Episode]:
    episodes: list[Episode] = []
    try:
        names = sorted(
            name
            for name in archive.namelist()
            if name.lower().endswith(".txt") and not name.endswith("/")
        )
        if not names:
            raise ScreenplayParseError(f"{source_name}: ZIP contains no .txt files")
        for name in names:
            text = _decode_screenplay(archive.read(name), name)
            episodes.append(parse_screenplay(text, source_name=name))
    except RuntimeError as exc:
        raise ScreenplayParseError(f"{source_name}: unable to read ZIP archive") from exc

    numbers: dict[int, str] = {}
    for episode in episodes:
        existing = numbers.get(episode.episode_number)
        if existing:
            episode.issues.append(
                ValidationIssue(
                    "DUPLICATE_EPISODE_NUMBER",
                    f"Episode {episode.episode_number} duplicates {existing}.",
                    "error",
                )
            )
        else:
            numbers[episode.episode_number] = episode.source_name
    return sorted(episodes, key=lambda episode: episode.episode_number)

