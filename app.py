from __future__ import annotations

import streamlit as st

from services import storage
from services.oci_genai import genai_status
from services.ui import (
    action_grid,
    child_selector,
    genai_status_banner,
    page_title,
    panel,
    profile_summary,
    score_badge,
    setup_page,
    workflow_steps,
)


setup_page("Home")
page_title(
    "Your Endless Stories",
    "A child-safe reading coach that creates personalized storybooks, scores practice sessions, and gives parents a clear next step.",
    meta=["Working prototype", "Local SQLite", "OCI Generative AI", "Hackathon MVP"],
)

status = genai_status()
genai_status_banner(status)
workflow_steps("profile")

top_left, top_right = st.columns([1.05, 1])

with top_left:
    child = child_selector()
    if child:
        profile_summary(child)
        stats = storage.profile_stats(child.id or 0)
        metric_cols = st.columns(3)
        metric_cols[0].metric("Stories", stats["story_count"])
        metric_cols[1].metric("Sessions", stats["session_count"])
        metric_cols[2].metric("Latest", score_badge(stats["latest_score"]))

with top_right:
    panel(
        "Problem",
        "Parents need a fast way to turn a child's interests into age-aware reading practice and understandable progress.",
        accent="Judging story",
    )
    panel(
        "Solution",
        "YES creates a personalized storybook, supports tricky words, scores the session, and recommends the next practice.",
        accent="Live demo",
    )

st.subheader("Demo actions")
action_grid(
    [
        ("Create or select reader", "Set age, interests, goal, and baseline in under a minute."),
        ("Generate storybook", "Use OCI Generative AI to create the reading set."),
        ("Run session", "Read, answer four questions, and save a transparent 100-point score."),
        ("Review progress", "See trends, strengths, weak areas, and next practice."),
    ]
)

link_cols = st.columns(4)
with link_cols[0]:
    st.page_link("pages/1_Child_Profile.py", label="Child profiles")
with link_cols[1]:
    st.page_link("pages/2_Generate_Story.py", label="Generate storybook")
with link_cols[2]:
    st.page_link("pages/3_Reading_Session.py", label="Reading session")
with link_cols[3]:
    st.page_link("pages/4_Parent_Dashboard.py", label="Parent dashboard")

st.divider()

recent_sessions = storage.list_sessions(limit=5)
if recent_sessions:
    st.subheader("Recent sessions")
    cols = st.columns(min(3, len(recent_sessions)))
    for index, session in enumerate(recent_sessions[:3]):
        story = storage.get_story(session.story_id)
        child = storage.get_child(session.child_id)
        title = story.title if story else "Story"
        child_name = child.name if child else "Child"
        with cols[index % len(cols)]:
            panel(
                f"{session.total_score:.0f}/100",
                f"{child_name}: {title}",
                accent="Latest saved score",
            )
else:
    st.info("Seed data loads automatically on first run. Add a profile or open the demo profile to begin.")
