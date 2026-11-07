# PromoScout Assignment Plan

Deadline: November 8, 2026, 5:00 PM IST  
Selected assignment: Problem 1 - Find the Promos (Ads)  
Stack: Python, Streamlit, Gemini API  
Working method: Complete and approve one step before beginning the next.

## Goal

Build a rerunnable tool that processes Kuku's 50 timestamped microdrama screenplays and recommends ranked 20-60 second promotional clips. Every recommendation must include exact episode timestamps, a hook, a cliffhanger, a concise rationale, supporting source material, and visible quality warnings.

## Progress

| Step | Workstream | Status | Approval gate |
|---|---|---|---|
| 1 | Scope and success criteria | Complete | Approved by user |
| 2 | Input audit and screenplay parser | Complete | Approved by user; 50/50 episodes parsed |
| 3 | Deterministic candidate generation | Complete | Approved by user; 232 valid windows generated |
| 4 | Gemini evaluation contract | Complete | Approved by user; six live structured evaluations preserved |
| 5 | Validation, deduplication, and ranking | Complete | Approved by user; live sample ranked with deterministic safeguards |
| 6 | Streamlit prototype | Complete | Approved by user; local upload-to-export workflow verified |
| 7 | Full 50-episode run | Complete | Approved by user; 100 evaluations across 50 episodes preserved |
| 8 | Quality evaluation | Complete | Approved by user; 86.7% shortlist-worthy rate documented |
| 9 | Repository and run package | Complete | Approved by user; clean-environment and public-package checks pass |
| 10 | Two-page solution PDF | Complete | Approved by user; professional two-page PDF verified |
| 11 | Walkthrough and submission package | In progress | Walkthrough and submission manifest drafted; personal details and links pending |
| 12 | Final verification | Not started | Submission checklist passes |

## Step 1 - Freeze scope and success criteria

Detailed contract: [docs/STEP_1_SCOPE.md](docs/STEP_1_SCOPE.md)

Deliverables:

- Product statement and target user.
- Supported inputs and required output schema.
- Definition of a valid promo.
- Initial scoring rubric.
- Human-in-the-loop boundary.
- Technical and quality targets.
- Confidentiality rules.
- Explicit non-goals and optional features.

Decision already proposed:

- Prioritize continuous, single-episode clips.
- Enforce timestamps and duration in Python.
- Use Gemini only for bounded semantic evaluation.
- Keep cross-episode and stitched promos optional until the MVP works.

Completion condition: user approves the product specification.

## Step 2 - Audit inputs and build the parser

Tasks:

1. Create the Python project structure and dependency file.
2. Read ZIP, individual `.txt`, and optionally multiple text files.
3. Parse episode metadata, scenes, and timestamped screenplay entries.
4. Normalize capitalization, whitespace, punctuation, and label variants.
5. Preserve original source text for traceability.
6. Validate unique episodes, timestamps, ordering, and episode boundaries.
7. Produce machine-readable parsing warnings.
8. Add parser unit tests using synthetic examples and selected private inputs.
9. Run the parser over all 50 supplied episodes.

Deliverables:

- Parser module and data models.
- Tests.
- Full-pack validation report.
- Summary of malformed or ambiguous input patterns.

Completion condition: all 50 files are either parsed successfully or reported with explicit actionable errors.

## Step 3 - Generate deterministic promo candidates

Tasks:

1. Generate valid 20-60 second windows from screenplay boundaries.
2. Prefer dialogue, action, reveal, confrontation, and scene boundaries.
3. Detect likely hooks using transparent keyword and structural signals.
4. Detect likely cliffhangers near questions, threats, revelations, entrances, and episode endings.
5. Penalize starts inside sentences and endings after resolution.
6. Limit the number of candidates per episode to control Gemini calls.
7. Record why every candidate was generated.
8. Manually inspect candidates across different story arcs.

Deliverables:

- Candidate-generation module.
- Candidate JSON for a representative sample.
- Spot-check report.

Completion condition: candidates are timestamp-valid, varied, and sufficiently promising for semantic evaluation.

## Step 4 - Define and test Gemini evaluation

Tasks:

1. Create a versioned prompt template.
2. Define a strict JSON response schema.
3. Supply only candidate content and clearly separated background context.
4. Require source-grounded hook, cliffhanger, summary, scores, warnings, and rationale.
5. Prohibit invented dialogue, events, and timestamps.
6. Configure the Gemini model through environment settings.
7. Add retries and error capture for malformed responses.
8. Preserve every raw model response unchanged.
9. Test a small set of strong, weak, and ambiguous candidates.

Deliverables:

- Gemini client.
- Versioned scoring prompt.
- Structured response model.
- Unedited sample responses and observations.

Completion condition: Gemini reliably returns schema-valid, source-grounded evaluations on the sample set.

## Step 5 - Validate, deduplicate, and rank

Tasks:

1. Enforce duration and source-boundary rules after model evaluation.
2. Reject nonexistent or modified timestamps.
3. Calculate the documented weighted score.
4. Penalize weak hooks, false cliffhangers, context dependence, and spoilers.
5. Detect overlapping and semantically repetitive candidates.
6. Promote story-arc diversity in the top results.
7. Record every rejection and penalty for auditability.
8. Compare top, middle, and rejected sample results manually.

Deliverables:

- Validation and ranking modules.
- Ranked sample output.
- Rejection and failure report.

Completion condition: the ranking is explainable, structurally valid, and useful enough to proceed to the interface.

## Step 6 - Build the Streamlit prototype

Workflow:

1. Upload ZIP or screenplay file.
2. Parse and display input inventory and warnings.
3. Generate candidates.
4. Score with Gemini.
5. Display ranked promo cards with source evidence.
6. Let the editor accept or reject recommendations.
7. Download JSON, CSV, and readable summary outputs.

Required interface information:

- Rank, episode, timestamps, and duration.
- Hook, cliffhanger, standalone summary, and rationale.
- Component scores, confidence, and warnings.
- Exact timestamped source excerpt.
- Processing errors and API status.

Deliverables:

- Streamlit application.
- Secure configuration example.
- Local end-to-end test.

Completion condition: a user can upload an input and obtain downloadable ranked results without editing code.

## Step 7 - Run the full input pack

Tasks:

1. Process all 50 episodes.
2. Cache parsing, candidates, and Gemini responses.
3. Retain raw, unedited Gemini outputs.
4. Export accepted, rejected, and failed candidates.
5. Confirm no episode was silently skipped.
6. Record runtime, number of calls, token usage when available, and estimated cost.

Deliverables:

- Full parser output.
- Full candidate output.
- Raw Gemini response folder.
- Final ranked JSON, CSV, and Markdown outputs.
- Processing summary.

Completion condition: the required raw-output folder covers the entire supplied pack.

## Step 8 - Evaluate quality honestly

Manual rubric:

- Valid 20-60 second duration.
- Accurate source timestamps.
- Hook inside the opening three seconds.
- Genuine unresolved ending.
- Standalone comprehensibility.
- Practical value to an editor.

Tasks:

1. Review top, middle, rejected, and diverse story-arc samples.
2. Calculate parser success, valid-output, duplicate, and editor-acceptance rates.
3. Document at least three weak selections.
4. Identify at least one specific Gemini mistake.
5. Explain limitations caused by having screenplays but not actual video.
6. Estimate how editor feedback and platform results would improve production ranking.

Deliverables:

- Evaluation table.
- Metrics summary.
- Failure-case analysis.

Completion condition: quality claims are supported by real runs and limitations are explicit.

## Step 9 - Package the repository

Target structure:

```text
promoscout/
|-- app.py
|-- src/
|   |-- parser.py
|   |-- candidates.py
|   |-- gemini_client.py
|   |-- ranking.py
|   |-- validation.py
|   `-- exporters.py
|-- prompts/
|-- tests/
|-- sample_data/
|-- requirements.txt
|-- .env.example
|-- .gitignore
`-- README.md
```

Tasks:

1. Write setup, configuration, run, and interview-test instructions.
2. Add a synthetic non-confidential example.
3. Exclude scripts, keys, caches, and confidential outputs from Git.
4. Verify the application from a clean environment.
5. Choose repository-only or deployed delivery based on remaining time.

Completion condition: another evaluator can run the prototype from the README.

## Step 10 - Create the two-page solution PDF

Page 1:

- Problem choice and motivation.
- User, workflow, scope, and assumptions.
- Architecture and AI/code division.
- Representative recommendation.

Page 2:

- Full-pack results and quality metrics.
- Failure cases and limitations.
- Cost, scalability, and human review.
- AI tools used and a concrete AI mistake.

Tasks:

1. Draft concise content from verified results only.
2. Add a compact architecture or results visual if useful.
3. Render the PDF to images.
4. Check legibility, clipping, links, and the two-page limit.
5. Obtain user approval.

Completion condition: the final rendered PDF is accurate, polished, and no longer than two pages.

## Step 11 - Prepare walkthrough and submission package

Tasks:

1. Write a three-minute walkthrough script.
2. Define the exact recording sequence.
3. Organize private raw outputs for the authorized submission route.
4. Collect prototype/repository and document links.
5. Add name, roll number, branch, and final problem selection.

Completion condition: every required submission field and artifact is available.

## Step 12 - Final verification

Checklist:

- All links open for anyone with the intended access.
- The app or repository runs from documented instructions.
- No API key appears in code, history, logs, or outputs.
- No confidential screenplay is in the public repository.
- Raw outputs cover all 50 episodes.
- The solution PDF is at most two pages.
- The optional video is at most three minutes.
- Assumptions, AI use, AI failure, limitations, cost, and scale are covered.
- Personal details and selected problem are correct.
- Submission occurs before 5:00 PM IST, preferably with a one-hour buffer.

## Scope control rules

- Required work takes priority over optional features.
- Do not begin multi-segment promos until the continuous-clip pipeline works.
- Do not deploy before the local workflow is stable.
- Do not polish UI at the expense of full-pack outputs and evaluation.
- Do not make performance claims that are unsupported by the available data.
- Do not expose confidential inputs or credentials.
- Update this file whenever a step changes status or scope.
