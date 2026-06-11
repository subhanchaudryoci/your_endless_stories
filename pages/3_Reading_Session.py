from __future__ import annotations

import html
import re

import streamlit as st

from models.schemas import ReadingSession
from services import storage
from services.scoring import WEIGHTS, calculate_session_score
from services.ui import child_selector, format_date, page_title, panel, setup_page, workflow_steps


def _highlight_terms(text: str, terms: list[str]) -> str:
    clean_terms = sorted({term.strip() for term in terms if term.strip()}, key=len, reverse=True)
    if not clean_terms:
        return html.escape(text)
    pattern = re.compile(r"\b(" + "|".join(re.escape(term) for term in clean_terms) + r")\b", re.IGNORECASE)
    pieces: list[str] = []
    last_end = 0
    for match in pattern.finditer(text):
        pieces.append(html.escape(text[last_end : match.start()]))
        pieces.append(f"<mark>{html.escape(match.group(0))}</mark>")
        last_end = match.end()
    pieces.append(html.escape(text[last_end:]))
    return "".join(pieces)


def _story_html(text: str, highlight_terms: list[str]) -> str:
    paragraphs = [part.strip() for part in text.split("\n") if part.strip()]
    if len(paragraphs) <= 1:
        sentences = [part.strip() for part in re.split(r"(?<=[.!?])\s+", text) if part.strip()]
        paragraphs = [" ".join(sentences[index : index + 3]) for index in range(0, len(sentences), 3)]
    return "".join(f"<p>{_highlight_terms(paragraph, highlight_terms)}</p>" for paragraph in paragraphs)


def _question_options(question_answer: str, options: list[str]) -> list[str]:
    choices: list[str] = []
    for option in options:
        if option and option not in choices:
            choices.append(option)
    if question_answer and question_answer not in choices:
        choices.append(question_answer)
    if "I am not sure" not in choices:
        choices.append("I am not sure")
    return ["Choose an answer"] + choices


def _session_result_matches(result: dict[str, object] | None, child_id: int, story_id: int) -> bool:
    if not result:
        return False
    return result.get("child_id") == child_id and result.get("story_id") == story_id


def _render_session_result(result: dict[str, object]) -> None:
    st.success("Session saved")
    st.metric("Proficiency Score", f"{float(result['total_score']):.0f}/100")
    score_cols = st.columns(4)
    score_cols[0].metric("Comprehension", f"{float(result['comprehension']):.0f}/40")
    score_cols[1].metric("Phonics", f"{float(result['phonics_decoding']):.0f}/20")
    score_cols[2].metric("Fluency", f"{float(result['fluency']):.0f}/15")
    score_cols[3].metric("Independence", f"{float(result['independence']):.0f}/15")
    st.markdown(
        f'<div class="yes-note"><strong>Recommendation:</strong> {html.escape(str(result["recommendation"]))}</div>',
        unsafe_allow_html=True,
    )
    if st.button("View parent dashboard", type="primary", use_container_width=True):
        st.session_state["latest_session_id"] = int(result["session_id"])
        st.session_state["selected_child_id"] = int(result["child_id"])
        st.session_state["selected_story_id"] = int(result["story_id"])
        st.switch_page("pages/4_Parent_Dashboard.py")


def _render_quiz_form(child, story) -> None:
    existing_result = st.session_state.get("session_result")
    if _session_result_matches(existing_result, child.id or 0, story.id or 0):
        _render_session_result(existing_result)
        return

    with st.form(f"quiz_{child.id}_{story.id}"):
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
            answers[str(index)] = st.radio(
                "Answer",
                _question_options(question.answer, question.options),
                index=0,
                key=f"answer_{story.id}_{index}",
                label_visibility="collapsed",
            )

        notes = st.text_area("Parent note", placeholder="optional")
        submitted = st.form_submit_button("Submit quiz", type="primary")

    if submitted:
        prior_sessions = storage.list_sessions(child.id or 0)
        score, quiz_percent = calculate_session_score(child, story.questions, answers, prior_sessions)
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
        session_id = storage.save_session(session)
        st.session_state["latest_session_id"] = session_id
        st.session_state["selected_child_id"] = child.id
        st.session_state["selected_story_id"] = story.id
        result = {
            "session_id": session_id,
            "child_id": child.id or 0,
            "story_id": story.id or 0,
            "total_score": score.total,
            "quiz_score": quiz_percent,
            "comprehension": score.comprehension,
            "phonics_decoding": score.phonics_decoding,
            "fluency": score.fluency,
            "independence": score.independence,
            "recommendation": score.recommendation,
        }
        st.session_state["session_result"] = result
        _render_session_result(result)


setup_page("Reading Session")
open_check_requested = bool(st.session_state.get("open_reading_check"))
page_title("Reading Time", "Read the story, then complete the Reading Check.")
workflow_steps("check" if open_check_requested else "session")

generation_notice = st.session_state.pop("generation_notice", None)
if generation_notice:
    st.warning(generation_notice["message"])
    if generation_notice.get("detail"):
        st.caption(generation_notice["detail"])

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
        except RuntimeError as exc:
            st.error(str(exc))

    open_check_requested = bool(st.session_state.pop("open_reading_check", False))
    stories = storage.list_stories(child.id or 0)
    if not stories:
        st.info("Choose or generate a storybook before reading.")
        st.page_link("pages/2_Generate_Story.py", label="Go to storybooks")
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

    if not story.questions:
        st.error("This storybook does not have quiz questions. Generate a new storybook to run a session.")
        st.stop()

    help_terms = story.tricky_words or [item.word for item in story.vocabulary]
    story_col, help_col = st.columns([1.55, 0.8])

    with story_col:
        story_markup = _story_html(story.story_text, help_terms)
        st.markdown(
            (
                f'<section class="yes-reader-shell">'
                f'<div class="yes-reader-title">{html.escape(story.title)}</div>'
                f'<div class="yes-reader-meta">Reader: {html.escape(child.name)} | Highlighted words are good ones to sound out.</div>'
                f'<div class="yes-reader-text">{story_markup}</div>'
                f'</section>'
            ),
            unsafe_allow_html=True,
        )
        st.markdown(
            (
                '<div class="yes-quiz-ready">'
                '<strong>Finished reading?</strong>'
                '<span> Reading Check</span>'
                '<div>Answer the story questions when the child is ready. The score is inferred from quiz answers and completion.</div>'
                '</div>'
            ),
            unsafe_allow_html=True,
        )

        if hasattr(st, "dialog"):
            @st.dialog("Reading check")
            def quiz_dialog() -> None:
                _render_quiz_form(child, story)

            if open_check_requested:
                quiz_dialog()
            if st.button("I am done reading - start quiz", type="primary", use_container_width=True):
                quiz_dialog()
        else:
            if open_check_requested:
                st.session_state["show_inline_quiz"] = True
            if st.button("I am done reading - start quiz", type="primary", use_container_width=True):
                st.session_state["show_inline_quiz"] = True
            if st.session_state.get("show_inline_quiz"):
                _render_quiz_form(child, story)

    with help_col:
        st.subheader("Words to try")
        if story.vocabulary:
            vocab_markup = ['<div class="yes-word-grid">']
            for item in story.vocabulary:
                pattern = f" ({html.escape(item.pattern)})" if item.pattern else ""
                vocab_markup.append(
                    f'<div class="yes-word-card">'
                    f'<div class="yes-word">{html.escape(item.word)}</div>'
                    f'<div>{html.escape(item.meaning)}</div>'
                    f'<div class="yes-hint">{html.escape(item.hint)}{pattern}</div>'
                    f'</div>'
                )
            vocab_markup.append("</div>")
            st.markdown("".join(vocab_markup), unsafe_allow_html=True)
        else:
            st.info("No vocabulary list found for this story.")

        st.subheader("Score evidence")
        panel(
            "Inferred score",
            "Quiz answers drive comprehension, vocabulary/phonics, fluency, independence, and consistency.",
            accent="No sliders",
        )
        with st.expander("100-point model"):
            for label, weight in WEIGHTS.items():
                st.write(f"**{label.replace('_', ' ').title()}**: {weight} points")
