from __future__ import annotations

import html

import pandas as pd
import streamlit as st

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


setup_page("Parent Dashboard")
page_title("Parent Dashboard", "Make reading progress visible to parents after every session.")
workflow_steps("dashboard")

child = child_selector()
if child:
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
    st.subheader("Score trend")
    st.line_chart(chart_df)

    latest = sessions[0]
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
        st.markdown(f'<div class="yes-note">{html.escape(latest.score.recommendation)}</div>', unsafe_allow_html=True)

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
