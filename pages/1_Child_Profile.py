from __future__ import annotations

import html

import streamlit as st

from models.schemas import ChildProfile, normalize_interests
from services import storage
from services.ui import child_selector, page_title, panel, profile_summary, setup_page, workflow_steps


setup_page("Child Profile")
page_title("Child Profile", "Select a reader or create a new one.")
workflow_steps("profile")

if st.session_state.get("judge_demo_active"):
    try:
        judge_child_id, judge_story_id = storage.prepare_judge_demo()
        judge_child = storage.get_child(judge_child_id)
        judge_story = storage.get_story(judge_story_id)
        st.session_state["selected_child_id"] = judge_child_id
        st.session_state["selected_story_id"] = judge_story_id
        st.success("Judge demo active")
        if judge_child and judge_story:
            st.markdown(
                (
                    '<div class="yes-soft">'
                    '<div class="yes-kicker">Pick reader</div>'
                    '<h3>Mia profile loaded</h3>'
                    f'<p><strong>Reader:</strong> {html.escape(judge_child.name)}, age {judge_child.age}</p>'
                    f'<p><strong>Storybook:</strong> {html.escape(judge_story.title)}</p>'
                    '</div>'
                ),
                unsafe_allow_html=True,
            )
        if st.button("Continue to storybooks", type="primary", use_container_width=True):
            st.switch_page("pages/2_Generate_Story.py")
        st.divider()
    except RuntimeError as exc:
        st.error(str(exc))

create_tab, manage_tab = st.tabs(["Create profile", "Manage profiles"])

with create_tab:
    form_col, guide_col = st.columns([1.35, 1])
    with form_col:
        with st.form("create_child_profile", clear_on_submit=False):
            name = st.text_input("Child name or nickname", max_chars=40)
            age = st.number_input("Age", min_value=3, max_value=14, value=7, step=1)
            interests = st.text_input("Interests", placeholder="space, soccer, animals")
            reading_goal = st.text_input("Reading goal", value="Improve comprehension and confidence")
            include_baseline = st.checkbox("Add baseline score", value=False)
            baseline_score = st.slider("Baseline reading score", 0, 100, 70)
            st.caption("The baseline is saved only when Add baseline score is checked.")
            submitted = st.form_submit_button("Create profile", type="primary")
    with guide_col:
        panel(
            "What this sets",
            "The app uses age for reading level, interests for theme, and goal plus baseline for progress context.",
            accent="Personalization",
        )

    if submitted:
        if not name.strip():
            st.error("Add a name or nickname.")
        elif not reading_goal.strip():
            st.error("Add a reading goal.")
        else:
            profile = ChildProfile(
                id=None,
                name=name.strip(),
                age=int(age),
                interests=normalize_interests(interests),
                reading_goal=reading_goal.strip(),
                baseline_score=float(baseline_score) if include_baseline else None,
            )
            child_id = storage.create_child(profile)
            st.session_state["selected_child_id"] = child_id
            st.switch_page("pages/2_Generate_Story.py")

with manage_tab:
    child = child_selector("Select profile")
    if child:
        left, right = st.columns([1, 1.35])
        with left:
            profile_summary(child)
        with right:
            with st.form(f"edit_child_{child.id}"):
                updated_name = st.text_input("Name or nickname", value=child.name, max_chars=40)
                updated_age = st.number_input("Age", min_value=3, max_value=14, value=child.age, step=1)
                updated_interests = st.text_input("Interests", value=", ".join(child.interests))
                updated_goal = st.text_input("Reading goal", value=child.reading_goal)
                has_baseline = st.checkbox("Use baseline score", value=child.baseline_score is not None)
                updated_baseline = st.slider(
                    "Baseline score",
                    0,
                    100,
                    int(child.baseline_score or 70),
                )
                st.caption("The baseline is saved only when Use baseline score is checked.")
                saved = st.form_submit_button("Save changes")

        if saved:
            storage.update_child(
                ChildProfile(
                    id=child.id,
                    name=updated_name.strip(),
                    age=int(updated_age),
                    interests=normalize_interests(updated_interests),
                    reading_goal=updated_goal.strip(),
                    baseline_score=float(updated_baseline) if has_baseline else None,
                    created_at=child.created_at,
                )
            )
            st.success("Profile updated.")
            st.rerun()

        if st.button("Continue to storybooks", type="primary", use_container_width=True):
            st.switch_page("pages/2_Generate_Story.py")
