from __future__ import annotations

import streamlit as st

from services import storage
from services.oci_genai import genai_status
from services.ui import (
    child_selector,
    genai_status_banner,
    page_title,
    panel,
    profile_summary,
    score_badge,
    setup_page,
    workflow_steps,
)


def render_home() -> None:
    setup_page("Home")
    page_title(
        "Your Endless Stories",
        "Pick a child, choose a storybook, read together, and see the next practice step.",
    )

    status = genai_status()
    genai_status_banner(status)
    workflow_steps("profile")

    judge_col, _ = st.columns([0.42, 0.58])
    with judge_col:
        if st.button("Start Judge Demo", type="primary", use_container_width=True):
            try:
                child_id, story_id = storage.prepare_judge_demo()
                st.session_state["judge_demo_active"] = True
                st.session_state["selected_child_id"] = child_id
                st.session_state["selected_story_id"] = story_id
                st.session_state.pop("session_result", None)
                st.switch_page("pages/1_Child_Profile.py")
            except RuntimeError as exc:
                st.error(str(exc))

    child = child_selector("Choose reader")

    if child:
        stats = storage.profile_stats(child.id or 0)
        stories = storage.list_stories(child.id or 0)
        sessions = storage.list_sessions(child.id or 0)

        left, right = st.columns([1, 1.1])
        with left:
            profile_summary(child)
            metric_cols = st.columns(3)
            metric_cols[0].metric("Stories", stats["story_count"])
            metric_cols[1].metric("Sessions", stats["session_count"])
            metric_cols[2].metric("Latest", score_badge(stats["latest_score"]))

        with right:
            if not stories:
                next_label = "Create Storybook"
                next_page = "pages/2_Generate_Story.py"
                next_text = "Start with a short storybook built from this child's age, interests, and goal."
            elif not sessions:
                next_label = "Start Reading"
                next_page = "pages/3_Reading_Session.py"
                next_text = "Open the selected storybook, read it together, and finish with the quiz."
            else:
                next_label = "View Dashboard"
                next_page = "pages/4_Parent_Dashboard.py"
                next_text = "Review the latest score, trend, strengths, and next practice recommendation."

            panel("Next step", next_text, accent="Flow")
            if st.button(next_label, type="primary", use_container_width=True):
                st.switch_page(next_page)
            st.page_link("pages/1_Child_Profile.py", label="Manage child profiles")

        if sessions:
            st.subheader("Recent practice")
            cols = st.columns(min(3, len(sessions)))
            for index, session in enumerate(sessions[:3]):
                story = storage.get_story(session.story_id)
                title = story.title if story else "Story"
                with cols[index % len(cols)]:
                    panel(f"{session.total_score:.0f}/100", title, accent="Saved score")
    else:
        st.page_link("pages/1_Child_Profile.py", label="Create a child profile")


render_home()
