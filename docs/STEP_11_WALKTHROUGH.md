# PromoScout walkthrough (target: 2 minutes 40 seconds)

## Before recording

1. Start the app with `./run_app.ps1` and keep `http://localhost:8501` open.
2. Keep the private screenplay ZIP ready, but do not reveal its local filename longer than necessary.
3. Open `artifacts/step7/ranked_promos.md` and `artifacts/step8/quality_report.md` in advance.
4. Close `.env`, terminals containing secrets, notifications, and unrelated browser tabs.
5. Record at 1080p with browser zoom near 100% and use your own voice.

## Exact recording sequence and script

### 0:00-0:15 - Introduction

**Screen:** PromoScout title in the Streamlit app.

**Say:**

> Hi, this is PromoScout, my solution for Kuku's Problem 1, Find the Promos. It reads timestamped microdrama screenplays and gives an editor ranked 20-to-60-second promo recommendations with exact boundaries, hooks, cliffhangers, evidence, and warnings.

### 0:15-0:35 - Problem and scope

**Screen:** Input and workflow area of the app.

**Say:**

> I chose this problem because editors currently repeat this search for every episode. I scoped the first version to continuous clips within one episode. The screenplay timestamps are treated as authoritative, and a human still checks the final footage before publishing.

### 0:35-1:05 - Run the deterministic stages

**Screen:** Upload the private ZIP, parse it, then generate candidates. Briefly show episode count, warnings, and candidate count.

**Say:**

> The first stages are deterministic Python. The parser normalizes and validates timestamps. Candidate generation creates valid 20-to-60-second windows around reveals, conflict, dialogue, and episode endings. On the supplied pack it parsed all 50 episodes and generated 232 valid candidates.

### 1:05-1:35 - Explain the AI boundary

**Screen:** Gemini settings and evaluation controls; do not rerun all 100 calls during the video.

**Say:**

> Only the strongest configurable candidates go to Gemini. It returns a strict structured judgment for the opening hook, unresolved ending, standalone clarity, intensity, evidence, and risks. Code then validates the response, rejects weak boundaries, removes duplicates, and enforces diversity. The model is configuration, so it can be swapped without changing the pipeline.

### 1:35-2:05 - Show usable output

**Screen:** Open the saved ranked recommendations. Show one recommendation's episode, timestamps, hook, cliffhanger, rationale, source evidence, warnings, and export formats.

**Say:**

> The full run evaluated 100 candidates successfully and produced 15 primary recommendations, three from each story arc. Each recommendation is traceable to timestamped source entries and can be exported as JSON, CSV, or Markdown for an editor.

### 2:05-2:30 - Quality and failure

**Screen:** Open the quality report and point to the summary and one failure case.

**Say:**

> I manually reviewed all 15 primary results plus eight additional examples. Eleven were strong, two needed boundary review, and two were false positives, giving a shortlist-worthy rate of 86.7 percent. One clear model mistake was treating the soft question, 'Does it hurt?', as a strong cliffhanger. That is why the final decision stays with an editor.

### 2:30-2:40 - Close

**Screen:** Return to the app overview or architecture.

**Say:**

> The system is rerunnable, cached, free-tier friendly, and honest about what screenplay text cannot reveal, including acting, shot rhythm, audio, and real platform performance.

## Recording guardrails

- Keep the final video under 3 minutes.
- Never show the Gemini key or the contents of `.env`.
- Do not make the video public; use an unlisted YouTube, Loom, or restricted Drive link accessible to reviewers.
- Avoid scrolling through large portions of the confidential screenplay.
- If a live Gemini call is slow, show the saved full-run result and explain that responses are cached and resumable.

