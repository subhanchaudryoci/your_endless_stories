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
page_title("Generate Storybook", "Create a short, age-aware reading set the child can use immediately.")
workflow_steps("story")

child = child_selector()
if child:
    generation_notice = st.session_state.pop("generation_notice", None)
    if generation_notice:
        st.warning(generation_notice["message"])
        if generation_notice.get("detail"):
            st.caption(generation_notice["detail"])

    status = genai_status()
    genai_status_banner(status)

    left, right = st.columns([0.9, 1.35])
    with left:
        profile_summary(child)
        theme_hint = st.text_input("Theme focus", placeholder="optional, such as dinosaurs at the library")
        if status["configured"]:
            st.caption("Generation source: OCI Generative AI")
        else:
            st.caption("Generation source: local demo fallback")

        if st.button("Generate storybook", type="primary"):
            with st.spinner("Generating storybook..."):
                story = generate_storybook(child, theme_hint)
                story_id = storage.save_story(story)
                st.session_state["selected_story_id"] = story_id
            st.success("Storybook saved.")
            if status["configured"] and story.source != "oci":
                error = last_genai_error()
                st.session_state["generation_notice"] = {
                    "message": (
                        "OCI generation failed, so the app saved a local fallback story. "
                        "Check your OCI API key config, model access, and compartment policy."
                    ),
                    "detail": error[:500] if error else "",
                }
            st.rerun()
        panel(
            "Generated package",
            "Each storybook includes a title, short story, vocabulary list, tricky-word hints, and four quiz questions.",
            accent="Demo proof",
        )
        panel(
            "Safety guardrails",
            "Prompts enforce age-appropriate content, structured JSON, and graceful fallback when model output is malformed.",
            accent="Quality",
        )

    with right:
        stories = storage.list_stories(child.id or 0)
        if not stories:
            st.info("Generate the first storybook for this child.")
        else:
            selected_id = st.session_state.get("selected_story_id")
            default_index = 0
            if selected_id:
                for index, item in enumerate(stories):
                    if item.id == selected_id:
                        default_index = index
                        break
            story = st.selectbox(
                "Saved storybooks",
                stories,
                index=default_index,
                format_func=lambda item: f"{item.title} ({format_date(item.created_at)})",
            )
            if story and story.id:
                st.session_state["selected_story_id"] = story.id
                st.subheader(story.title)
                source_label = "Live OCI" if story.source == "oci" else story.source.title()
                st.caption(f"Theme: {story.theme or 'General'} | Source: {source_label}")
                escaped_story = html.escape(story.story_text).replace("\n", "<br>")
                st.markdown(f'<div class="yes-story">{escaped_story}</div>', unsafe_allow_html=True)

                vocab_tab, question_tab = st.tabs(["Vocabulary", "Questions"])
                with vocab_tab:
                    vocab_markup = ['<div class="yes-word-grid">']
                    for item in story.vocabulary:
                        vocab_markup.append(
                            f'<div class="yes-word-card">'
                            f'<div class="yes-word">{html.escape(item.word)}</div>'
                            f'<div>{html.escape(item.meaning)}</div>'
                            f'<div class="yes-hint">{html.escape(item.hint)} ({html.escape(item.pattern or "reading hint")})</div>'
                            f'</div>'
                        )
                    vocab_markup.append("</div>")
                    st.markdown("".join(vocab_markup), unsafe_allow_html=True)
                with question_tab:
                    for index, question in enumerate(story.questions, start=1):
                        st.markdown(
                            (
                                f'<div class="yes-question">'
                                f'<div class="yes-question-type">{html.escape(question.question_type.title())}</div>'
                                f'<strong>{index}. {html.escape(question.question)}</strong>'
                                f'<div class="yes-hint">Answer: {html.escape(question.answer)}</div>'
                                f'</div>'
                            ),
                            unsafe_allow_html=True,
                        )
