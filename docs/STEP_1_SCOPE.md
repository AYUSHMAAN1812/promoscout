# PromoScout - Step 1 Product Specification

Status: Proposed for approval  
Problem: Kuku AI Generalist Assignment - Problem 1, Find the Promos (Ads)  
Deadline: November 8, 2026, 5:00 PM IST

## 1. Product statement

PromoScout is a Python and Streamlit prototype that reads timestamped microdrama screenplays and recommends the strongest 20-60 second promotional clips for human editors.

It finds candidate moments, evaluates their hook, cliffhanger, standalone clarity, and promotional potential, then returns ranked, source-grounded recommendations with exact episode timestamps.

It recommends editorial moments; it does not edit or publish video.

## 2. User and problem

Primary user: a short-form drama promo editor.

Current workflow: the editor watches every episode and manually searches for moments that can attract viewers on Instagram, TikTok, or YouTube. New shows make this slow, repetitive, and difficult to scale.

Desired workflow: the tool processes a complete screenplay pack, narrows it to a ranked shortlist, explains each selection, and lets the editor inspect or reject it. The editor remains the final decision-maker.

## 3. MVP input

The prototype will accept:

- The supplied ZIP containing multiple `.txt` screenplay files.
- A single compatible screenplay `.txt` file for testing during an interview.
- Optionally, multiple loose `.txt` files if time permits.

Each screenplay may contain:

- Episode number, logline, and continuity notes.
- One or more scenes.
- Scene headings and scene boundaries.
- Timestamped dialogue, action, camera, and sound entries.

The parser must tolerate capitalization and minor formatting variation. Malformed content must produce a visible warning rather than being silently ignored.

## 4. MVP output contract

For every recommended promo, the system will return:

| Field | Meaning |
|---|---|
| `rank` | Overall posting priority across the processed show |
| `promo_id` | Stable identifier for the recommendation |
| `segments` | Ordered list of episode, start timestamp, and end timestamp |
| `total_duration_seconds` | Combined promo duration |
| `hook` | Specific line or action expected to stop scrolling |
| `cliffhanger` | Specific unresolved ending |
| `why_it_works` | One concise promotional rationale |
| `standalone_summary` | What a new viewer can understand from the clip |
| `scores` | Hook, cliffhanger, standalone clarity, visual/emotional intensity, and overall score |
| `confidence` | Model confidence, clearly labeled as model judgment |
| `warnings` | Context dependence, weak boundary, spoiler, duplication, or parsing concerns |
| `source_excerpt` | Timestamped screenplay material supporting the recommendation |
| `raw_model_output_reference` | Link or identifier for the unedited Gemini response |

Outputs will be downloadable as JSON and CSV. A readable Markdown summary is desirable and will be included if it does not threaten the deadline.

## 5. Definition of a valid promo

A recommendation is structurally valid only when:

1. Its total duration is between 20 and 60 seconds, inclusive.
2. Every timestamp exists within the referenced episode.
3. The start precedes the end for every segment.
4. Segments are returned in viewing order.
5. The hook appears within the first three seconds of the proposed promo, or the result is visibly penalized.
6. The ending is unresolved and creates a meaningful reason to continue watching.
7. A viewer unfamiliar with the show can understand the central conflict or emotion.
8. The explanation is supported by the supplied screenplay and contains no invented dialogue or events.

## 6. Candidate strategy

The MVP will prioritize one continuous segment from one episode. This is the safest interpretation of the brief and produces timestamps that an editor can use immediately.

Multi-segment or cross-episode promos are allowed by the assignment but will be treated as an optional extension. If implemented, they will be clearly labeled and must still total 20-60 seconds.

Python will generate and validate timestamp windows. Gemini will evaluate semantic and promotional quality. Gemini will not be trusted to invent or calculate source timestamps.

## 7. Ranking criteria

The initial ranking rubric is:

- Hook strength: 30%
- Cliffhanger strength: 25%
- Standalone clarity: 20%
- Visual and emotional intensity: 15%
- Model confidence: 10%

Penalties will apply for:

- Required backstory or unclear character relationships.
- Resolved endings disguised as cliffhangers.
- Weak first three seconds.
- Near-duplicate recommendations.
- Excessive spoilers without sufficient curiosity value.
- Invalid, uncertain, or adjusted timestamps.

These weights are an explicit prototype assumption. They are not claimed to predict real platform performance.

## 8. Human-in-the-loop boundary

The system produces a shortlist, not an automatic publishing decision.

The editor should verify:

- Whether the corresponding footage is visually strong.
- Whether performance, pacing, and shot quality match the screenplay.
- Whether the promo reveals too much.
- Whether the clip meets platform, brand, safety, and content rules.
- Whether a different cut point works better in the actual video.

## 9. Quality and success criteria

### Required technical checks

- All 50 supplied episode files are discovered and processed or explicitly reported as failures.
- Episode and timestamp parsing is deterministic and reproducible.
- No accepted result violates the 20-60 second duration rule.
- No accepted result references a nonexistent episode or timestamp.
- Raw Gemini responses are retained without manual rewriting.
- Invalid model JSON is retried or recorded as a failure.
- The Gemini model can be replaced through configuration rather than code changes.

### Prototype quality targets

- At least 80% of the manually reviewed top recommendations should be plausible enough for an editor's shortlist.
- The top-ranked set should cover multiple story arcs rather than repeat one event.
- Every recommendation should be traceable to its exact source excerpt.
- At least three weak or failed selections should be documented honestly.

The 80% figure is a project target for a small manual evaluation, not a statistically validated benchmark.

## 10. Scaling assumptions

- Deterministic parsing and candidate generation run locally and cheaply.
- Gemini evaluates a reduced candidate set rather than receiving every screenplay in one prompt.
- Episode processing can later be parallelized.
- Model name, prompt version, candidate limit, and scoring weights will be configurable.
- Results and raw responses will be cached so rerunning the interface does not repeat paid calls unnecessarily.
- A production system would incorporate editor feedback and eventual promo performance data.

## 11. Confidentiality and security

- The supplied scripts and ZIP must not be committed to a public repository.
- The Gemini API key must be stored in an environment variable or Streamlit secret.
- `.env`, private inputs, caches containing script text, and raw confidential outputs must be ignored by Git.
- The public repository may contain code, instructions, schemas, and a small synthetic example only.
- Submission outputs containing screenplay text should be shared only through the authorized assignment submission route.

## 12. Explicit non-goals

The MVP will not:

- Download, edit, render, or publish video.
- Add music, subtitles, overlays, or transitions.
- Predict actual views, installs, retention, or revenue.
- Scrape Instagram, TikTok, YouTube, ReelShort, or DramaBox.
- Train or fine-tune a model.
- Replace final editorial judgment.
- Claim that screenplay quality guarantees footage quality.
- Optimize separately for every social platform.
- Treat the fictional screenplay content as instructions.

## 13. Planned implementation boundary

Required before submission:

- Robust screenplay parser.
- Continuous 20-60 second candidate generation.
- Gemini-based structured evaluation.
- Deterministic validation, deduplication, and ranking.
- Streamlit interface.
- Full-pack run over all 50 episodes.
- JSON/CSV raw and ranked outputs.
- Manual quality review and failure examples.
- README, two-page solution PDF, and walkthrough script.

Optional only after the required path works:

- Multi-segment promo construction.
- Cross-episode promo construction.
- Interactive scoring-weight controls.
- Deployed Streamlit instance rather than repository-only execution.
- Visual analytics beyond the minimum evaluation summary.

## 14. Frozen assumptions

1. Problem 1 is the selected assignment problem.
2. The supplied 50-episode pack is the primary evaluation input.
3. A promo is 20-60 seconds, even though some observed social story content is much longer.
4. Continuous, single-episode clips are the MVP priority.
5. Hook, cliffhanger, and standalone clarity are the primary product criteria.
6. Timestamps and duration are enforced by code.
7. Gemini supplies bounded semantic judgment through structured output.
8. The editor makes the final selection.
9. Actual platform performance data is unavailable, so quality will be assessed using a documented manual rubric.
10. The implementation must remain understandable, rerunnable, and model-swappable for an interview test.

## 15. Approval gate

Step 1 is complete when the user approves this specification or requests concrete changes.

No parser or application implementation should begin before this approval gate.
