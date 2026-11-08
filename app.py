"""PromoScout Streamlit application."""

from __future__ import annotations

import hashlib
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))

import streamlit as st  # noqa: E402

from promoscout.candidates import CandidateConfig, generate_show_candidates  # noqa: E402
from promoscout.exporters import export_csv, export_json, export_markdown  # noqa: E402
from promoscout.gemini_client import (  # noqa: E402
    GeminiConfigurationError,
    GeminiEvaluationError,
    GeminiPromoEvaluator,
)
from promoscout.parser import (  # noqa: E402
    ScreenplayParseError,
    parse_screenplay,
    parse_screenplay_zip_bytes,
    seconds_to_timestamp,
)
from promoscout.ranking import rank_promos, score_candidate  # noqa: E402


st.set_page_config(
    page_title="PromoScout",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    .block-container {padding-top: 2rem; padding-bottom: 4rem; max-width: 1400px;}
    .hero {padding: 1.25rem 1.4rem; border: 1px solid rgba(120,120,120,.25); border-radius: 18px;
           background: linear-gradient(135deg, rgba(120,70,255,.14), rgba(255,80,120,.08)); margin-bottom: 1rem;}
    .eyebrow {font-size: .78rem; letter-spacing: .14em; text-transform: uppercase; opacity: .68; font-weight: 700;}
    .hero h1 {margin: .25rem 0 .35rem; font-size: 2.25rem;}
    .muted {opacity: .72;}
    [data-testid="stMetric"] {border: 1px solid rgba(120,120,120,.22); border-radius: 14px; padding: .8rem 1rem;}
    .score-pill {display:inline-block; padding:.22rem .6rem; border-radius:999px; background:rgba(90,120,255,.16); font-weight:700;}
    </style>
    """,
    unsafe_allow_html=True,
)


def reset_downstream() -> None:
    for key in ("episodes", "candidates", "evaluations", "scored", "ranked", "editor_reviews"):
        st.session_state.pop(key, None)


def parse_upload(name: str, data: bytes):
    if name.lower().endswith(".zip"):
        return parse_screenplay_zip_bytes(data, source_name=name)
    text = data.decode("utf-8-sig")
    return [parse_screenplay(text, source_name=name)]


def source_excerpt(candidate) -> str:
    lines = []
    for entry in candidate.source_entries:
        lines.append(
            f"{seconds_to_timestamp(entry.start_seconds)}-{seconds_to_timestamp(entry.end_seconds)} "
            f"[{entry.label}] {entry.text}"
        )
    return "\n\n".join(lines)


st.markdown(
    """
    <div class="hero">
      <div class="eyebrow">AI-assisted microdrama editing</div>
      <h1>PromoScout</h1>
      <div class="muted">Find source-grounded 20–60 second promo moments, validate them with Gemini, and keep the editor in control.</div>
    </div>
    """,
    unsafe_allow_html=True,
)

with st.sidebar:
    st.header("Run configuration")
    upload = st.file_uploader("Screenplay input", type=["zip", "txt"], help="Upload the private Kuku ZIP or one compatible screenplay.")
    max_per_episode = st.slider("Candidates per episode", 1, 8, 5)
    evaluation_limit = st.number_input("Gemini evaluation limit", 1, 250, 10, help="Use a small limit for testing; the full run is a separate controlled step.")
    st.caption("API key configured securely through the environment or Streamlit Secrets and never displayed.")
    if st.button("Clear current run", width="stretch"):
        reset_downstream()
        st.session_state.pop("upload_hash", None)
        st.rerun()

if upload is None:
    st.info("Upload the supplied screenplay ZIP or a compatible `.txt` screenplay to begin.")
    st.markdown(
        """
        **Workflow**

        1. Parse and validate timestamped screenplay entries.
        2. Generate explainable 20–60 second candidate windows.
        3. Evaluate a controlled candidate batch with Gemini.
        4. Apply deterministic safety rules and rank the survivors.
        5. Review and export editor-ready recommendations.
        """
    )
    st.stop()

data = upload.getvalue()
upload_hash = hashlib.sha256(data).hexdigest()
if st.session_state.get("upload_hash") != upload_hash:
    reset_downstream()
    st.session_state.upload_hash = upload_hash

action_col, status_col = st.columns([1, 3])
with action_col:
    parse_clicked = st.button("1 · Parse screenplay", type="primary", width="stretch")
with status_col:
    st.caption(f"Loaded `{upload.name}` · {len(data) / 1024:.1f} KB")

if parse_clicked:
    try:
        with st.spinner("Parsing and validating screenplay timestamps…"):
            st.session_state.episodes = parse_upload(upload.name, data)
            for key in ("candidates", "evaluations", "scored", "ranked", "editor_reviews"):
                st.session_state.pop(key, None)
    except (ScreenplayParseError, UnicodeDecodeError) as exc:
        st.error(f"Could not parse the input: {exc}")

episodes = st.session_state.get("episodes")
if not episodes:
    st.stop()

errors = sum(episode.error_count for episode in episodes)
warnings = sum(episode.warning_count for episode in episodes)
metric_cols = st.columns(5)
metric_cols[0].metric("Episodes", len(episodes))
metric_cols[1].metric("Scenes", sum(len(episode.scenes) for episode in episodes))
metric_cols[2].metric("Timed entries", sum(len(episode.entries) for episode in episodes))
metric_cols[3].metric("Errors", errors)
metric_cols[4].metric("Warnings", warnings)

with st.expander("Input inventory and validation", expanded=bool(errors or warnings)):
    st.dataframe(
        [
            {
                "Episode": episode.episode_number,
                "Duration": seconds_to_timestamp(episode.duration_seconds),
                "Scenes": len(episode.scenes),
                "Entries": len(episode.entries),
                "Errors": episode.error_count,
                "Warnings": episode.warning_count,
            }
            for episode in episodes
        ],
        width="stretch",
        hide_index=True,
    )
    for episode in episodes:
        for issue in episode.issues:
            severity_label = "Blocking error" if issue.severity == "error" else "Non-blocking source warning"
            (st.error if issue.severity == "error" else st.warning)(
                f"Episode {episode.episode_number} · {severity_label} · {issue.code}: {issue.message}"
            )

if errors:
    st.error("Resolve parsing errors before candidate generation.")
    st.stop()

if st.button("2 · Generate promo candidates", width="stretch"):
    with st.spinner("Generating and deduplicating timestamp-valid windows…"):
        config = CandidateConfig(max_candidates_per_episode=max_per_episode)
        st.session_state.candidates = generate_show_candidates(episodes, config)
        for key in ("evaluations", "scored", "ranked", "editor_reviews"):
            st.session_state.pop(key, None)

candidates = st.session_state.get("candidates", [])
if not candidates:
    st.stop()

st.success(f"Generated {len(candidates)} timestamp-valid candidates across {len(set(c.episode_number for c in candidates))} episodes.")
st.caption(
    "Candidates are options for evaluation, not guaranteed promos. PromoScout may return fewer recommendations "
    "when candidates do not meet the quality thresholds."
)
with st.expander("Candidate shortlist", expanded=False):
    st.dataframe(
        [
            {
                "ID": candidate.candidate_id,
                "Episode": candidate.episode_number,
                "Window": f"{seconds_to_timestamp(candidate.start_seconds)}–{seconds_to_timestamp(candidate.end_seconds)}",
                "Duration": candidate.duration_seconds,
                "Heuristic score": candidate.deterministic_score,
                "Hook signals": ", ".join(candidate.hook_signals),
                "Cliff signals": ", ".join(candidate.cliffhanger_signals),
            }
            for candidate in candidates
        ],
        width="stretch",
        hide_index=True,
    )

evaluate_count = min(int(evaluation_limit), len(candidates))
st.caption(
    f"Gemini will evaluate the top {evaluate_count} candidates by deterministic score. "
    "Raw responses are preserved for the current run and available through downloadable exports."
)
if st.button("3 · Evaluate selected candidates with Gemini", width="stretch"):
    selected = sorted(candidates, key=lambda item: item.deterministic_score, reverse=True)[:evaluate_count]
    episode_map = {episode.episode_number: episode for episode in episodes}
    evaluations = {}
    failures = []
    progress = st.progress(0, text="Starting Gemini evaluation…")
    try:
        evaluator = GeminiPromoEvaluator(raw_output_dir=ROOT / "raw_outputs" / "gemini" / "app")
        for index, candidate in enumerate(selected, start=1):
            progress.progress((index - 1) / len(selected), text=f"Evaluating {candidate.candidate_id}…")
            try:
                run = evaluator.evaluate(episode_map[candidate.episode_number], candidate)
                evaluations[candidate.candidate_id] = run.evaluation
            except GeminiEvaluationError as exc:
                failures.append(str(exc))
        progress.progress(1.0, text="Gemini evaluation complete")
        st.session_state.evaluations = evaluations
        st.session_state.evaluation_failures = failures
        scored = [
            score_candidate(candidate, evaluations[candidate.candidate_id])
            for candidate in selected
            if candidate.candidate_id in evaluations
        ]
        st.session_state.scored = scored
        st.session_state.ranked = rank_promos(scored)
        st.session_state.editor_reviews = {}
    except GeminiConfigurationError as exc:
        st.error(str(exc))

for failure in st.session_state.get("evaluation_failures", []):
    st.warning(failure)

ranked = st.session_state.get("ranked", [])
scored = st.session_state.get("scored", [])
if not scored:
    st.stop()

decision_cols = st.columns(3)
decision_cols[0].metric("Accepted", sum(item.decision == "accepted" for item in scored))
decision_cols[1].metric("Human review", sum(item.decision == "human_review" for item in scored))
decision_cols[2].metric("Rejected", sum(item.decision == "rejected" for item in scored))

ranked_tab, rejected_tab, export_tab = st.tabs(["Ranked promos", "Rejected / audit", "Export"])
with ranked_tab:
    if not ranked:
        st.warning(
            "No candidates passed the current safety thresholds. This is a valid outcome: broaden the candidate "
            "pool, increase the evaluation limit, adjust boundaries during editor review, or inspect another episode."
        )
    elif len(ranked) < len(scored):
        st.info(
            f"{len(ranked)} of {len(scored)} evaluated candidates passed the current thresholds. "
            "PromoScout does not force weak candidates into the ranked shortlist."
        )
    for item in ranked:
        candidate = item.candidate
        evaluation = item.evaluation
        with st.container(border=True):
            title_col, score_col = st.columns([4, 1])
            title_col.subheader(
                f"#{item.rank} · Episode {candidate.episode_number} · "
                f"{seconds_to_timestamp(candidate.start_seconds)}–{seconds_to_timestamp(candidate.end_seconds)}"
            )
            score_col.markdown(f"<div class='score-pill'>{item.final_score:.1f}/100</div>", unsafe_allow_html=True)
            st.markdown(f"**Hook:** {evaluation.hook.description}")
            st.markdown(f"**Cliffhanger:** {evaluation.cliffhanger.description}")
            st.markdown(f"**Why it works:** {evaluation.why_it_works}")
            detail_cols = st.columns(4)
            detail_cols[0].metric("Hook", f"{evaluation.hook.score}/10")
            detail_cols[1].metric("Cliffhanger", f"{evaluation.cliffhanger.score}/10")
            detail_cols[2].metric("Standalone", f"{evaluation.standalone.score}/10")
            detail_cols[3].metric("Confidence", f"{evaluation.confidence:.0%}")
            if evaluation.warnings or item.penalties:
                st.caption(" · ".join(evaluation.warnings + item.penalties))
            review = st.segmented_control(
                "Editor decision",
                ["Accept", "Needs review", "Reject"],
                key=f"review_{candidate.candidate_id}",
                default="Needs review",
            )
            st.session_state.editor_reviews[candidate.candidate_id] = review.lower().replace(" ", "_")
            with st.expander("Inspect exact timestamped source"):
                st.text(source_excerpt(candidate))

with rejected_tab:
    rejected = [item for item in scored if item.decision == "rejected"]
    if not rejected:
        st.info("No evaluated candidates were rejected.")
    for item in sorted(rejected, key=lambda value: value.final_score, reverse=True):
        with st.expander(
            f"Episode {item.candidate.episode_number} · {seconds_to_timestamp(item.candidate.start_seconds)}–"
            f"{seconds_to_timestamp(item.candidate.end_seconds)} · {item.final_score:.1f}/100"
        ):
            for reason in item.rejection_reasons:
                st.write(f"- {reason}")
            st.caption(item.evaluation.boundary_reason)

with export_tab:
    if ranked:
        reviews = st.session_state.get("editor_reviews", {})
        json_data = export_json(ranked, reviews)
        csv_data = export_csv(ranked, reviews)
        markdown_data = export_markdown(ranked, reviews)
        download_cols = st.columns(3)
        download_cols[0].download_button("Download JSON", json_data, "promoscout_ranked.json", "application/json", width="stretch")
        download_cols[1].download_button("Download CSV", csv_data, "promoscout_ranked.csv", "text/csv", width="stretch")
        download_cols[2].download_button("Download Markdown", markdown_data, "promoscout_ranked.md", "text/markdown", width="stretch")
        st.caption("Exports contain confidential screenplay excerpts and should only be shared through the authorized assignment route.")

