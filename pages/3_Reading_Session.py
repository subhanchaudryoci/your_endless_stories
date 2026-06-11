from __future__ import annotations

import html
import re

import streamlit as st

from models.schemas import ReadingSession
from services import storage
from services.scoring import WEIGHTS, calculate_session_score
from services.ui import child_selector, format_date, page_title, panel, setup_page, workflow_steps


setup_page("Reading Session")
page_title("Reading Session", "Turn each storybook into measurable comprehension and phonics practice.")
workflow_steps("session")

child = child_selector()
if child:
    stories = storage.list_stories(child.id or 0)
    if not stories:
        st.info("Generate a storybook before starting a reading session.")
        st.page_link("pages/2_Generate_Story.py", label="Generate storybook")
        st.stop()

    selected_id = st.session_state.get("selected_story_id")
    default_index = 0
    if selected_id:
        for index, item in enumerate(stories):
            if item.id == selected_id:
                default_index = index
                break

    story = st.selectbox(
        "Storybook",
        stories,
        index=default_index,
        format_func=lambda item: f"{item.title} ({format_date(item.created_at)})",
    )
    if story and story.id:
        st.session_state["selected_story_id"] = story.id

    story_col, help_col = st.columns([1.45, 1])
    with story_col:
        st.subheader(story.title)
        large_text = st.toggle("Large reading view", value=False)
        escaped_story = html.escape(story.story_text).replace("\n", "<br>")
        font_size = "1.3rem" if large_text else "1.08rem"
        st.markdown(
            f'<div class="yes-story" style="font-size:{font_size};">{escaped_story}</div>',
            unsafe_allow_html=True,
        )

        with st.expander("Line-by-line view"):
            sentences = [part.strip() for part in re.split(r"(?<=[.!?])\s+", story.story_text) if part.strip()]
            for sentence in sentences:
                st.write(sentence)

    with help_col:
        st.subheader("Reading help")
        if story.vocabulary:
            vocab_markup = ['<div class="yes-word-grid">']
            for item in story.vocabulary:
                vocab_markup.append(
                    f'<div class="yes-word-card">'
                    f'<div class="yes-word">{html.escape(item.word)}</div>'
                    f'<div>{html.escape(item.meaning)}</div>'
                    f'<div class="yes-hint">{html.escape(item.hint)}</div>'
                    f'</div>'
                )
            vocab_markup.append("</div>")
            st.markdown("".join(vocab_markup), unsafe_allow_html=True)
        else:
            st.info("No vocabulary list found for this story.")

        st.subheader("Scoring model")
        score_cols = st.columns(2)
        for index, (label, weight) in enumerate(WEIGHTS.items()):
            with score_cols[index % 2]:
                panel(label.replace("_", " ").title(), f"{weight} points", accent="Score")

    st.divider()
    st.subheader("Quiz")
    with st.form(f"quiz_{story.id}"):
        answers: dict[str, str] = {}
        for index, question in enumerate(story.questions):
            st.markdown(
                (
                    f'<div class="yes-question">'
                    f'<div class="yes-question-type">{html.escape(question.question_type.title())}</div>'
                    f'<strong>{index + 1}. {html.escape(question.question)}</strong>'
                    f'</div>'
                ),
                unsafe_allow_html=True,
            )
            options = question.options or ["I am not sure"]
            answers[str(index)] = st.radio(
                "Answer",
                options,
                key=f"answer_{story.id}_{index}",
                label_visibility="collapsed",
            )

        rating_cols = st.columns(3)
        with rating_cols[0]:
            phonics_rating = st.slider("Phonics / decoding", 1, 5, 4)
        with rating_cols[1]:
            fluency_rating = st.slider("Fluency", 1, 5, 4)
        with rating_cols[2]:
            independence_rating = st.slider("Independence", 1, 5, 4)
        notes = st.text_area("Session notes", placeholder="optional")
        submitted = st.form_submit_button("Score and save session", type="primary")

    if submitted:
        prior_sessions = storage.list_sessions(child.id or 0)
        score, quiz_percent = calculate_session_score(
            child,
            story.questions,
            answers,
            phonics_rating,
            fluency_rating,
            independence_rating,
            prior_sessions,
        )
        session = ReadingSession(
            id=None,
            child_id=child.id or 0,
            story_id=story.id or 0,
            answers=answers,
            score=score,
            quiz_score=quiz_percent,
            total_score=score.total,
            notes=notes,
        )
        storage.save_session(session)

        st.success(f"Session saved. Total score: {score.total:.0f}/100")
        metric_cols = st.columns(5)
        metric_cols[0].metric("Comprehension", f"{score.comprehension:.0f}/{WEIGHTS['comprehension']}")
        metric_cols[1].metric("Phonics", f"{score.phonics_decoding:.0f}/{WEIGHTS['phonics_decoding']}")
        metric_cols[2].metric("Fluency", f"{score.fluency:.0f}/{WEIGHTS['fluency']}")
        metric_cols[3].metric("Independence", f"{score.independence:.0f}/{WEIGHTS['independence']}")
        metric_cols[4].metric("Consistency", f"{score.consistency:.0f}/{WEIGHTS['consistency']}")

        st.write(f"Strengths: {', '.join(score.strengths)}")
        st.write(f"Practice focus: {', '.join(score.weak_areas)}")
        st.markdown(f'<div class="yes-note">{html.escape(score.recommendation)}</div>', unsafe_allow_html=True)

        with st.expander("Question feedback"):
            for result in score.details["question_results"]:
                status = "Correct" if result["correct"] else "Review"
                st.write(f"**{status}:** {result['question']}")
                st.caption(f"Answer: {result['answer']} | {result['explanation']}")
