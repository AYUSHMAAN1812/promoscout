"""Fail if the intended public package contains credentials or private inputs."""

from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PUBLIC_ROOT_FILES = {
    ".env.example",
    ".gitignore",
    "PLAN.md",
    "README.md",
    "app.py",
    "pyproject.toml",
    "requirements.txt",
    "run_app.ps1",
}
PUBLIC_DIRECTORIES = {"docs", "prompts", "sample_data", "scripts", "src", "tests"}
TEXT_SUFFIXES = {".md", ".py", ".ps1", ".txt", ".toml", ".example", ".gitignore"}
PRIVATE_ARCHIVE_MARKER = "I Married a Broken Soldier." + " He was a Duke-scripts"


def configured_key() -> str | None:
    dotenv = ROOT / ".env"
    if not dotenv.exists():
        return None
    for line in dotenv.read_text(encoding="utf-8").splitlines():
        if line.startswith("GEMINI_API_KEY="):
            value = line.split("=", 1)[1].strip()
            return value or None
    return None


def intended_public_files() -> list[Path]:
    files = [ROOT / name for name in sorted(PUBLIC_ROOT_FILES) if (ROOT / name).is_file()]
    for directory in sorted(PUBLIC_DIRECTORIES):
        path = ROOT / directory
        if path.exists():
            files.extend(file for file in path.rglob("*") if file.is_file() and "__pycache__" not in file.parts)
    return sorted(set(files))


def main() -> int:
    files = intended_public_files()
    key = configured_key()
    findings: list[str] = []

    for path in files:
        relative = path.relative_to(ROOT)
        if path.suffix.lower() not in TEXT_SUFFIXES and path.name not in {".gitignore"}:
            findings.append(f"Unexpected non-text public file: {relative}")
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            findings.append(f"Unreadable or binary public file: {relative}")
            continue
        if key and len(key) >= 12 and key in text:
            findings.append(f"Configured Gemini key appears in: {relative}")
        if PRIVATE_ARCHIVE_MARKER in text and path.name != "README.md":
            findings.append(f"Private archive name appears unexpectedly in: {relative}")

    forbidden_present = [
        name
        for name in (".env", "artifacts", "raw_outputs")
        if (ROOT / name) in files
    ]
    findings.extend(f"Forbidden path included: {name}" for name in forbidden_present)

    if findings:
        print("PUBLIC PACKAGE AUDIT FAILED")
        for finding in findings:
            print(f"- {finding}")
        return 1

    print("PUBLIC PACKAGE AUDIT PASSED")
    print(f"Public files inspected: {len(files)}")
    print("Configured key found outside .env: no")
    print("Private inputs or outputs included: no")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

