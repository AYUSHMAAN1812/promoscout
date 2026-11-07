"""Parse the private input pack and write a non-destructive validation report."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from promoscout.parser import parse_screenplay_zip, seconds_to_timestamp  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("zip_path", type=Path)
    parser.add_argument("--json-output", type=Path, required=True)
    parser.add_argument("--markdown-output", type=Path, required=True)
    args = parser.parse_args()

    episodes = parse_screenplay_zip(args.zip_path)
    issue_counts = Counter(issue.code for episode in episodes for issue in episode.issues)
    entry_counts = Counter(entry.kind for episode in episodes for entry in episode.entries)
    error_count = sum(episode.error_count for episode in episodes)
    warning_count = sum(episode.warning_count for episode in episodes)

    report = {
        "source_archive": args.zip_path.name,
        "episode_count": len(episodes),
        "episode_numbers": [episode.episode_number for episode in episodes],
        "scene_count": sum(len(episode.scenes) for episode in episodes),
        "entry_count": sum(len(episode.entries) for episode in episodes),
        "entry_counts_by_kind": dict(sorted(entry_counts.items())),
        "total_duration_seconds": round(sum(episode.duration_seconds for episode in episodes), 2),
        "error_count": error_count,
        "warning_count": warning_count,
        "issue_counts": dict(sorted(issue_counts.items())),
        "episodes": [episode.to_dict(include_raw_text=False) for episode in episodes],
    }

    args.json_output.parent.mkdir(parents=True, exist_ok=True)
    args.markdown_output.parent.mkdir(parents=True, exist_ok=True)
    args.json_output.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    lines = [
        "# Step 2 Input Validation Report",
        "",
        f"Source archive: `{args.zip_path.name}`",
        "",
        "## Summary",
        "",
        f"- Episodes parsed: {len(episodes)}",
        f"- Episode range: {episodes[0].episode_number}-{episodes[-1].episode_number}",
        f"- Scenes parsed: {report['scene_count']}",
        f"- Timestamped entries parsed: {report['entry_count']}",
        f"- Combined episode duration: {seconds_to_timestamp(report['total_duration_seconds'])}",
        f"- Validation errors: {error_count}",
        f"- Validation warnings: {warning_count}",
        "",
        "## Entry types",
        "",
        "| Type | Count |",
        "|---|---:|",
    ]
    lines.extend(f"| {kind} | {count} |" for kind, count in sorted(entry_counts.items()))
    lines.extend(["", "## Validation issue counts", ""])
    if issue_counts:
        lines.extend(["| Code | Count |", "|---|---:|"])
        lines.extend(f"| {code} | {count} |" for code, count in sorted(issue_counts.items()))
    else:
        lines.append("No validation issues were detected.")

    lines.extend(
        [
            "",
            "## Episode inventory",
            "",
            "| Episode | Source ID | Duration | Scenes | Entries | Errors | Warnings |",
            "|---:|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for episode in episodes:
        lines.append(
            f"| {episode.episode_number} | {episode.source_id or ''} | "
            f"{seconds_to_timestamp(episode.duration_seconds)} | {len(episode.scenes)} | "
            f"{len(episode.entries)} | {episode.error_count} | {episode.warning_count} |"
        )

    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- Entry overlap is expected because camera, action, dialogue, and sound describe the same screen time.",
            "- Replacement-character warnings describe corruption already present in the supplied text; the parser preserves it rather than guessing the missing punctuation.",
            "- Entries just outside scene bounds are retained and flagged so later candidate validation can handle them transparently.",
            "- The JSON report intentionally excludes full raw screenplay text but contains parsed excerpts and must still be treated as confidential.",
            "",
        ]
    )
    args.markdown_output.write_text("\n".join(lines), encoding="utf-8")

    print(json.dumps({key: report[key] for key in report if key != "episodes"}, indent=2))
    return 1 if error_count else 0


if __name__ == "__main__":
    raise SystemExit(main())

