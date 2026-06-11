from __future__ import annotations

import html

import streamlit as st

from services import storage
from services.oci_genai import generate_storybook, genai_status, last_genai_error
from services.ui import (
    child_selector,
    format_date,
    genai_status_banner,
    page_title,
    panel,
    profile_summary,
    setup_page,
    workflow_steps,
)


setup_page("Generate Story")
page_title("Storybook", "Choose a saved story or create a new one.")
workflow_steps("story")

child = child_selector("Reader")
if child:
    if st.session_state.get("judge_demo_active"):
        try:
            judge_child_id, judge_story_id = storage.prepare_judge_demo()
            st.session_state["selected_child_id"] = judge_child_id
            st.session_state["selected_story_id"] = judge_story_id
            if child.id != judge_child_id:
                st.rerun()
            st.success("Judge demo active")
            st.caption("Mia profile loaded")
        except RuntimeError as exc:
            st.error(str(exc))

    status = genai_status()
    genai_status_banner(status)

    ready_story_id = st.session_state.get("story_ready_id")
    if ready_story_id:
        ready_story = storage.get_story(int(ready_story_id))
        if ready_story and ready_story.child_id == child.id:
            st.success(f"Storybook ready: {ready_story.title}")
            ready_cols = st.columns(2)
            if ready_cols[0].button("Read storybook", type="primary", use_container_width=True):
                st.session_state["selected_story_id"] = ready_story.id
                st.switch_page("pages/3_Reading_Session.py")
            if ready_cols[1].button("Open Reading Check", use_container_width=True):
                st.session_state["selected_story_id"] = ready_story.id
                st.session_state["open_reading_check"] = True
                st.switch_page("pages/3_Reading_Session.py")

    left, right = st.columns([0.9, 1.25])

    with left:
        profile_summary(child)
        st.subheader("Create new")
        theme_hint = st.text_input("Theme focus", placeholder="optional, such as dinosaurs at the library")
        source_label = "OCI Generative AI" if status["configured"] else "local demo fallback"
        st.caption(f"Generation source: {source_label}")

        if st.button("Generate storybook", type="primary", use_container_width=True):
            with st.spinner("Building the storybook..."):
                story = generate_storybook(child, theme_hint)
                story_id = storage.save_story(story)
                st.session_state["selected_story_id"] = story_id
                st.session_state["story_ready_id"] = story_id
                if status["configured"] and story.source != "oci":
                    error = last_genai_error()
                    st.session_state["generation_notice"] = {
                        "message": "OCI generation failed, so a local fallback story was saved for the demo.",
                        "detail": error[:500] if error else "",
                    }
            st.rerun()

        panel(
            "Storybook contents",
            "Title, short story, vocabulary, decoding hints, and a mixed quiz.",
            accent="Generated set",
        )

    with right:
        st.subheader("Saved storybooks")
        stories = storage.list_stories(child.id or 0)
        if not stories:
            st.info("No saved storybooks yet. Generate one to continue.")
        else:
            selected_id = st.session_state.get("selected_story_id")
            default_index = 0
            if selected_id:
                for index, item in enumerate(stories):
                    if item.id == selected_id:
                        default_index = index
                        break
            story = st.selectbox(
                "Choose storybook",
                stories,
                index=default_index,
                format_func=lambda item: f"{item.title} ({format_date(item.created_at)})",
                label_visibility="collapsed",
            )
            if story and story.id:
                st.session_state["selected_story_id"] = story.id
                source = "Live OCI" if story.source == "oci" else story.source.title()
                st.caption(f"Theme: {story.theme or 'General'} | Source: {source}")
                preview = story.story_text[:650].strip()
                if len(story.story_text) > len(preview):
                    preview += "..."
                escaped_story = html.escape(preview).replace("\n", "<br>")
                st.markdown(f'<div class="yes-story">{escaped_story}</div>', unsafe_allow_html=True)

                vocab_count = len(story.vocabulary)
                question_count = len(story.questions)
                metric_cols = st.columns(2)
                metric_cols[0].metric("Vocabulary", vocab_count)
                metric_cols[1].metric("Questions", question_count)
                action_cols = st.columns(2)
                if action_cols[0].button("Read this storybook", type="primary", use_container_width=True):
                    st.session_state["selected_story_id"] = story.id
                    st.switch_page("pages/3_Reading_Session.py")
                if action_cols[1].button("Open Reading Check", use_container_width=True):
                    st.session_state["selected_story_id"] = story.id
                    st.session_state["open_reading_check"] = True
                    st.switch_page("pages/3_Reading_Session.py")
