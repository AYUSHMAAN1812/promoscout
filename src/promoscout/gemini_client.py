"""Gemini adapter with structured output, retries, and raw-response preservation."""

from __future__ import annotations

import json
import os
import re
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from .evaluation import PROMO_EVALUATION_SCHEMA, PromoEvaluation, validate_evaluation
from .models import Episode, PromoCandidate
from .parser import seconds_to_timestamp


DEFAULT_MODEL = "gemini-3.5-flash-lite"
PROMPT_PATH = Path(__file__).resolve().parents[2] / "prompts" / "promo_scoring_v1.txt"


class GeminiConfigurationError(RuntimeError):
    """Raised when local Gemini configuration is unavailable or invalid."""


class GeminiEvaluationError(RuntimeError):
    """Raised when all Gemini evaluation attempts fail."""


@dataclass(slots=True)
class EvaluationRun:
    evaluation: PromoEvaluation
    raw_response_path: Path
    model: str
    attempt_count: int
    usage_metadata: dict[str, Any] | None = None


@dataclass(slots=True)
class TransportResult:
    text: str
    usage_metadata: dict[str, Any] | None = None
    model_version: str | None = None


def load_dotenv_if_present(path: str | Path = ".env") -> None:
    """Load simple KEY=VALUE pairs without overriding process environment values."""

    dotenv_path = Path(path)
    if not dotenv_path.exists():
        return
    for raw_line in dotenv_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def build_candidate_input(episode: Episode, candidate: PromoCandidate) -> str:
    """Create source-grounded input with background visibly separated from clip content."""

    rows = []
    for entry in candidate.source_entries:
        visible_start = max(entry.start_seconds, candidate.start_seconds)
        visible_end = min(entry.end_seconds, candidate.end_seconds)
        relative_start = visible_start - candidate.start_seconds
        relative_end = visible_end - candidate.start_seconds
        rows.append(
            f"[{seconds_to_timestamp(visible_start)}-{seconds_to_timestamp(visible_end)} | "
            f"relative {relative_start:.2f}-{relative_end:.2f}s] {entry.label}: {entry.text}"
        )

    return "\n".join(
        [
            "BACKGROUND - NOT VISIBLE IN THE PROPOSED CLIP",
            f"Episode: {episode.episode_number}",
            f"Logline: {episode.logline}",
            f"Continuity notes: {episode.continuity_notes}",
            "",
            "PROPOSED CLIP TO EVALUATE",
            f"Candidate ID: {candidate.candidate_id}",
            f"Fixed boundaries: {seconds_to_timestamp(candidate.start_seconds)} to {seconds_to_timestamp(candidate.end_seconds)}",
            f"Duration: {candidate.duration_seconds:.2f} seconds",
            "The relative times show what occurs during the opening three seconds and final moments.",
            "",
            *rows,
        ]
    )


def _rest_transport(
    *, api_key: str, model: str, system_instruction: str, contents: str, schema: dict[str, Any]
) -> TransportResult:
    endpoint = (
        f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    )
    payload = {
        "systemInstruction": {"parts": [{"text": system_instruction}]},
        "contents": [{"role": "user", "parts": [{"text": contents}]}],
        "generationConfig": {
            "temperature": 0.2,
            "responseMimeType": "application/json",
            "responseJsonSchema": schema,
        },
    }
    request = urllib.request.Request(
        endpoint,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "x-goog-api-key": api_key,
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=90) as response:
            response_data = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise GeminiEvaluationError(f"Gemini HTTP {exc.code}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise GeminiEvaluationError(f"Gemini network error: {exc.reason}") from exc

    try:
        text = response_data["candidates"][0]["content"]["parts"][0]["text"]
        return TransportResult(
            text=text,
            usage_metadata=response_data.get("usageMetadata"),
            model_version=response_data.get("modelVersion"),
        )
    except (KeyError, IndexError, TypeError) as exc:
        raise GeminiEvaluationError(
            f"Gemini response did not contain text: {json.dumps(response_data)[:1000]}"
        ) from exc


class GeminiPromoEvaluator:
    def __init__(
        self,
        *,
        api_key: str | None = None,
        model: str | None = None,
        raw_output_dir: str | Path = "raw_outputs/gemini",
        max_attempts: int = 3,
        transport: Callable[..., str] | None = None,
    ) -> None:
        load_dotenv_if_present()
        self.api_key = api_key or os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        self.model = model or os.getenv("GEMINI_MODEL", DEFAULT_MODEL)
        self.raw_output_dir = Path(raw_output_dir)
        self.max_attempts = max_attempts
        self.transport = transport or _rest_transport
        if not self.api_key:
            raise GeminiConfigurationError(
                "Set GEMINI_API_KEY in the environment or in a local .env file."
            )
        if max_attempts < 1:
            raise ValueError("max_attempts must be at least 1")

    def evaluate(self, episode: Episode, candidate: PromoCandidate) -> EvaluationRun:
        system_instruction = PROMPT_PATH.read_text(encoding="utf-8")
        contents = build_candidate_input(episode, candidate)
        errors: list[str] = []

        for attempt in range(1, self.max_attempts + 1):
            try:
                transport_result = self.transport(
                    api_key=self.api_key,
                    model=self.model,
                    system_instruction=system_instruction,
                    contents=contents,
                    schema=PROMO_EVALUATION_SCHEMA,
                )
                if isinstance(transport_result, str):
                    raw_text = transport_result
                    usage_metadata = None
                else:
                    raw_text = transport_result.text
                    usage_metadata = transport_result.usage_metadata
                raw_path = self._preserve_raw_response(candidate, raw_text, attempt)
                parsed = json.loads(raw_text)
                evaluation = validate_evaluation(parsed, candidate.candidate_id)
                return EvaluationRun(
                    evaluation,
                    raw_path,
                    self.model,
                    attempt,
                    usage_metadata,
                )
            except Exception as exc:  # Each failure is retained before a bounded retry.
                errors.append(f"attempt {attempt}: {type(exc).__name__}: {exc}")
                if attempt < self.max_attempts:
                    retry_match = re.search(
                        r'(?:retry in|"retryDelay":\s*")(\d+)', str(exc), re.IGNORECASE
                    )
                    if "HTTP 429" in str(exc) and retry_match:
                        delay = min(int(retry_match.group(1)) + 1, 65)
                    else:
                        delay = min(2 ** (attempt - 1), 4)
                    time.sleep(delay)

        raise GeminiEvaluationError(
            f"Gemini evaluation failed for {candidate.candidate_id}: " + " | ".join(errors)
        )

    def _preserve_raw_response(
        self, candidate: PromoCandidate, raw_text: str, attempt: int
    ) -> Path:
        self.raw_output_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
        path = self.raw_output_dir / (
            f"{candidate.candidate_id}__{self.model.replace('/', '_')}__a{attempt}__{timestamp}.json"
        )
        path.write_text(raw_text, encoding="utf-8")
        return path

