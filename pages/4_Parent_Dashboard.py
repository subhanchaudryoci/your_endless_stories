from __future__ import annotations

import html

import pandas as pd
import streamlit as st

from models.schemas import ChildProfile, ReadingSession, StoryBook
from services import storage
from services.oci_genai import generate_parent_summary, genai_status
from services.scoring import aggregate_strengths_and_needs
from services.ui import (
    child_selector,
    format_date,
    genai_status_banner,
    page_title,
    panel,
    profile_summary,
    score_badge,
    setup_page,
    workflow_steps,
)


def _first_or_default(values: list[str], default: str) -> str:
    return values[0] if values else default


def _render_session_completion(child_name: str, session: ReadingSession, story: StoryBook | None) -> None:
    story_title = story.title if story else "Story"
    strongest = _first_or_default(session.score.strengths, "Steady participation")
    focus = _first_or_default(session.score.weak_areas, "No major weak area")
    st.markdown(
        (
            '<div class="yes-session-summary">'
            '<h3>Session complete</h3>'
            f'<div class="yes-muted">{html.escape(child_name)} finished {html.escape(story_title)}.</div>'
            '<div class="yes-summary-grid">'
            '<div class="yes-summary-item">'
            '<div class="yes-summary-label">Score saved</div>'
            f'<div class="yes-summary-value">{session.total_score:.0f}/100</div>'
            '</div>'
            '<div class="yes-summary-item">'
            '<div class="yes-summary-label">Quiz result</div>'
            f'<div class="yes-summary-value">{session.quiz_score:.0f}%</div>'
            '</div>'
            '<div class="yes-summary-item">'
            '<div class="yes-summary-label">Strongest area</div>'
            f'<div class="yes-summary-value">{html.escape(strongest)}</div>'
            '</div>'
            '<div class="yes-summary-item">'
            '<div class="yes-summary-label">Practice focus</div>'
            f'<div class="yes-summary-value">{html.escape(focus)}</div>'
            '</div>'
            '</div>'
            f'<div class="yes-note" style="margin-top:0.75rem;">{html.escape(session.score.recommendation)}</div>'
            '</div>'
        ),
        unsafe_allow_html=True,
    )


def _score_text(score: float | None) -> str:
    return "No score yet" if score is None else f"{score:.0f}/100"


def _trend_rows(reader: ChildProfile, sessions: list[ReadingSession]) -> list[dict[str, object]]:
    return [
        {
            "date": session.created_at,
            "Date": format_date(session.created_at),
            "Reader": reader.name,
            "Score": session.total_score,
        }
        for session in sessions
    ]


def _count_label(count: object, singular: str) -> str:
    value = int(count or 0)
    suffix = "" if value == 1 else "s"
    return f"{value} {singular}{suffix}"


def _render_reader_snapshot(
    reader: ChildProfile,
    stats: dict[str, object],
    sessions: list[ReadingSession],
) -> None:
    aggregate = aggregate_strengths_and_needs(sessions)
    st.markdown(f"#### {reader.name}")
    st.caption(
        f"Age {reader.age} | "
        f"{_count_label(stats['session_count'], 'session')} | "
        f"{_count_label(stats['story_count'], 'storybook')}"
    )
    score_cols = st.columns(2)
    score_cols[0].metric("Latest", _score_text(stats["latest_score"]))
    score_cols[1].metric("Average", _score_text(stats["average_score"]))
    panel("Strengths", ", ".join(aggregate["strengths"][:2]), accent="Pattern")
    panel("Practice focus", ", ".join(aggregate["weak_areas"][:2]), accent="Next practice")


def _render_reader_comparison(
    child: ChildProfile,
    child_sessions: list[ReadingSession],
    children: list[ChildProfile],
) -> None:
    comparison_options = [candidate for candidate in children if candidate.id != child.id]
    if not comparison_options:
        st.info("Add another child profile to compare readers.")
        return

    st.subheader("Compare readers")
    comparison_child = st.selectbox(
        "Compare with",
        comparison_options,
        format_func=lambda item: f"{item.name}, age {item.age}",
        key=f"compare_child_{child.id}",
    )
    comparison_sessions = storage.list_sessions(comparison_child.id or 0)
    child_stats = storage.profile_stats(child.id or 0)
    comparison_stats = storage.profile_stats(comparison_child.id or 0)

    comparison_cols = st.columns(2)
    with comparison_cols[0]:
        _render_reader_snapshot(child, child_stats, child_sessions)
    with comparison_cols[1]:
        _render_reader_snapshot(comparison_child, comparison_stats, comparison_sessions)

    trend_rows = _trend_rows(child, child_sessions) + _trend_rows(comparison_child, comparison_sessions)
    if trend_rows:
        trend_df = pd.DataFrame(trend_rows).sort_values("date")
        chart_df = trend_df.pivot_table(index="Date", columns="Reader", values="Score", aggfunc="last")
        st.caption("Score trend comparison")
        st.line_chart(chart_df)

    latest = child_stats["latest_score"]
    comparison_latest = comparison_stats["latest_score"]
    if latest is not None and comparison_latest is not None:
        difference = float(latest) - float(comparison_latest)
        st.caption(f"Latest score gap: {difference:+.0f} points for {child.name} vs {comparison_child.name}.")


setup_page("Parent Dashboard")
page_title("Proficiency Dashboard", "Review scores, trends, and the next practice step.")
workflow_steps("dashboard")

child = child_selector()
if child:
    latest_session_id = st.session_state.pop("latest_session_id", None)

    profile_summary(child)
    stats = storage.profile_stats(child.id or 0)
    metric_cols = st.columns(4)
    metric_cols[0].metric("Stories", stats["story_count"])
    metric_cols[1].metric("Sessions", stats["session_count"])
    metric_cols[2].metric("Latest", score_badge(stats["latest_score"]))
    average_score = "No score yet" if stats["average_score"] is None else f"{stats['average_score']:.0f}/100"
    metric_cols[3].metric("Average", average_score)

    sessions = storage.list_sessions(child.id or 0)
    stories = storage.list_stories(child.id or 0)
    children = storage.list_children()

    _render_reader_comparison(child, sessions, children)

    if not sessions:
        st.info("No completed sessions yet.")
        st.page_link("pages/3_Reading_Session.py", label="Start reading session")
        st.stop()

    rows = []
    for session in sessions:
        story = storage.get_story(session.story_id)
        rows.append(
            {
                "date": session.created_at,
                "Date": format_date(session.created_at),
                "Story": story.title if story else "Story",
                "Total": session.total_score,
                "Quiz": session.quiz_score,
                "Comprehension": session.score.comprehension,
                "Phonics": session.score.phonics_decoding,
                "Fluency": session.score.fluency,
                "Independence": session.score.independence,
                "Consistency": session.score.consistency,
                "Strengths": ", ".join(session.score.strengths),
                "Practice focus": ", ".join(session.score.weak_areas),
                "Recommendation": session.score.recommendation,
            }
        )

    df = pd.DataFrame(rows)
    chart_df = df.sort_values("date")[["Date", "Total"]].set_index("Date")
    latest = sessions[0]
    if latest_session_id:
        completion_session = next(
            (session for session in sessions if session.id == int(latest_session_id)),
            latest,
        )
        _render_session_completion(child.name, completion_session, storage.get_story(completion_session.story_id))

    st.subheader("Score trend")
    st.line_chart(chart_df)

    component_df = pd.DataFrame(
        {
            "Area": ["Comprehension", "Phonics", "Fluency", "Independence", "Consistency"],
            "Points": [
                latest.score.comprehension,
                latest.score.phonics_decoding,
                latest.score.fluency,
                latest.score.independence,
                latest.score.consistency,
            ],
        }
    ).set_index("Area")

    left, right = st.columns([1, 1])
    with left:
        st.subheader("Latest score breakdown")
        st.bar_chart(component_df)
    with right:
        aggregate = aggregate_strengths_and_needs(sessions)
        st.subheader("Patterns")
        panel("Strengths", ", ".join(aggregate["strengths"][:3]), accent="Observed")
        panel("Practice focus", ", ".join(aggregate["weak_areas"][:3]), accent="Next area")
        panel("Recommendation", latest.score.recommendation, accent="Next step")
        st.caption("Scoring is inferred from quiz answers, answer completion, and recent progress.")

    st.subheader("Recent sessions")
    st.dataframe(
        df[["Date", "Story", "Total", "Quiz", "Strengths", "Practice focus", "Recommendation"]],
        width="stretch",
        hide_index=True,
    )

    st.subheader("Recent stories")
    story_cols = st.columns(min(3, max(1, len(stories[:3]))))
    for index, story in enumerate(stories[:3]):
        with story_cols[index % len(story_cols)]:
            panel(
                story.title,
                f"{format_date(story.created_at)} | {story.theme or 'General'} | {story.source}",
                accent="Storybook",
            )

    st.divider()
    st.subheader("Parent summary")
    status = genai_status()
    genai_status_banner(status)

    if st.button("Generate parent summary"):
        with st.spinner("Generating summary..."):
            st.session_state[f"summary_{child.id}"] = generate_parent_summary(child, sessions)

    summary = st.session_state.get(f"summary_{child.id}")
    if summary:
        panel("Summary", summary["summary"], accent="Parent-ready")
        summary_cols = st.columns(2)
        with summary_cols[0]:
            panel("Strengths", ", ".join(summary["strengths"]), accent="OCI summary")
        with summary_cols[1]:
            panel("Weak areas", ", ".join(summary["weak_areas"]), accent="OCI summary")
        st.markdown(f'<div class="yes-note">{html.escape(summary["next_practice"])}</div>', unsafe_allow_html=True)
