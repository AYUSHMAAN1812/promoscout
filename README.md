# PromoScout

PromoScout is an AI-assisted editor tool that reads timestamped microdrama screenplays and recommends ranked 20-60 second promotional clips.

It was built for Kuku's **Problem 1: Find the Promos (Ads)** assignment. The prototype searches every supplied episode, uses deterministic code to create timestamp-valid candidate windows, asks Gemini to evaluate promotional quality, and applies a final safety and diversity layer before presenting results to a human editor.

## What it produces

For each recommended promo, PromoScout returns:

- Episode and exact start/end timestamps.
- Total duration.
- Opening hook and supporting evidence.
- Ending cliffhanger and supporting evidence.
- Standalone summary and promotional rationale.
- Hook, cliffhanger, clarity, intensity, and confidence scores.
- Context, spoiler, and boundary warnings.
- Exact timestamped screenplay source entries.
- Human-editor decision.
- JSON, CSV, and Markdown exports.

The tool recommends source moments. It does not edit, render, or publish video.

## Why the system is hybrid

Python handles work that must be exact and reproducible:

- ZIP and screenplay parsing.
- Timestamp normalization.
- 20-60 second duration enforcement.
- Candidate generation.
- Source grounding.
- Invalid-output rejection.
- Duplicate suppression and story-arc diversity.
- Export generation.

Gemini handles bounded semantic judgments:

- Does the first three seconds contain a real hook?
- Is the ending genuinely unresolved?
- Can a new viewer understand the conflict?
- Is the moment emotionally and visually promising?
- What context, spoiler, or boundary risks remain?

A human editor remains responsible for verifying the actual footage and approving the final cut.

## Architecture

```text
Screenplay ZIP / TXT
        |
        v
Deterministic parser and validation
        |
        v
20-60 second candidate generation
        |
        v
Gemini structured evaluation
        |
        v
Hard validation + weighted ranking
        |
        v
Editor review + JSON / CSV / Markdown exports
```

Key modules:

```text
app.py                           Streamlit interface
src/promoscout/parser.py         Screenplay and timestamp parser
src/promoscout/candidates.py     Deterministic candidate generation
src/promoscout/gemini_client.py  Gemini REST adapter and raw-output capture
src/promoscout/evaluation.py     Structured response contract
src/promoscout/ranking.py        Safety rules, scoring, and diversity
src/promoscout/exporters.py      Editor-ready exports
prompts/promo_scoring_v1.txt     Versioned model instruction
```

## Setup on Windows

Requirements:

- Python 3.11 or newer.
- A Gemini API key from Google AI Studio.

From PowerShell:

```powershell
cd C:\path\to\promoscout
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
```

Edit `.env`:

```text
GEMINI_API_KEY=your_private_key
GEMINI_MODEL=gemini-3.5-flash-lite
```

Never commit `.env` or paste the key into an output file.

## Run the interface

```powershell
.\run_app.ps1
```

Or directly:

```powershell
.\.venv\Scripts\python.exe -m streamlit run app.py
```

Open `http://localhost:8501`.

For a safe first run, upload `sample_data/synthetic_episode.txt` and set a low Gemini evaluation limit.

## Run tests

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

The tests cover:

- Timestamp parsing and round trips.
- ZIP upload parsing.
- Candidate duration and source grounding.
- Structured Gemini response validation.
- Raw-response preservation.
- False-hook and false-cliffhanger rejection.
- Overlap and story-diversity controls.
- JSON, CSV, and Markdown exports.

## Reproduce a private full-pack run

The private screenplay archive is intentionally excluded from this repository.

```powershell
python scripts\run_full_pack.py `
  "path\to\private-screenplays.zip" `
  --output-dir "artifacts\step7" `
  --per-episode 2
```

The runner:

- Parses every episode.
- Generates candidates across the full pack.
- Evaluates the strongest configurable number per episode.
- Checkpoints every response.
- Resumes without paying for completed calls again.
- Throttles requests for Gemini's free-tier limit.
- Preserves unedited raw model responses.
- Produces evaluation, failure, scored, ranked, CSV, and Markdown files.

## Current full-pack results

On the supplied 50-episode pack:

- 50 episodes and 100 scenes parsed with zero parser errors.
- 232 deterministic candidate windows generated.
- 100 candidates evaluated with Gemini, with zero final failures.
- 65 suitable, 17 borderline, and 18 rejected by Gemini.
- 15 diverse primary recommendations produced automatically.
- Manual screenplay review found 11 strong as-is, two needing editor review, and two false positives.
- Shortlist-worthy rate on the top 15: 86.7%.

These figures describe one internal run, not a production benchmark.

## Known failure modes

- Romantic or emotional questions can be mistaken for cliffhangers.
- A strong ending can cause the model to overlook a weak first three seconds.
- A dramatic blocked escape may be described as unresolved even when the immediate action is partly resolved.
- Keyword heuristics over-generate quiet domestic scenes.
- Screenplays cannot reveal acting quality, shot rhythm, audio impact, or final footage quality.
- No platform-performance data is available, so the tool cannot predict views or installs.

## Scaling and cost controls

- Candidate generation is local and deterministic.
- Only a reduced candidate set is sent to Gemini.
- Model name and candidate limits are configurable.
- Raw responses are cached and reusable.
- The full-pack runner respects free-tier request limits.
- A production pipeline can parallelize episodes within account quotas.
- Editor feedback and real promo performance should eventually calibrate ranking weights.

## Confidentiality

The assignment screenplay pack belongs to Kuku and must not be published.

The repository excludes:

- ZIP and PDF assignment inputs.
- `.env` and API secrets.
- Raw model outputs.
- Parsed private screenplay artifacts.
- Ranked outputs containing confidential screenplay excerpts.

Only code, prompts, tests, documentation, and the synthetic example should be placed in a public repository.

## AI use and an observed mistake

Gemini was used to judge semantic qualities that simple rules cannot reliably capture. One observed mistake was Episode 10: Gemini rated a wounded-man clip highly even though it ended on the soft question “Does it hurt?”, which is romantic tension but not a strong acquisition cliffhanger. Manual review rejected that recommendation.

## Interview rerun

For a new screenplay during an interview:

1. Start the Streamlit app.
2. Upload the new `.txt` file or ZIP.
3. Parse and inspect warnings.
4. Generate candidates.
5. Evaluate a small candidate batch with Gemini.
6. Inspect accepted and rejected results.
7. Download the ranked output.

The Gemini model can be changed through `GEMINI_MODEL` without modifying the parser, candidate generator, or ranking system.

