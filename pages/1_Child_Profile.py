from __future__ import annotations

import streamlit as st

from models.schemas import ChildProfile, normalize_interests
from services import storage
from services.ui import child_selector, page_title, panel, profile_summary, setup_page, workflow_steps


setup_page("Child Profile")
page_title("Child Profile", "Capture the minimum context needed to personalize safe reading practice.")
workflow_steps("profile")

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
            baseline_score = st.slider("Baseline reading score", 0, 100, 70, disabled=not include_baseline)
            submitted = st.form_submit_button("Create profile", type="primary")
    with guide_col:
        panel(
            "Profile data",
            "The app uses age for reading level, interests for theme, and goal plus baseline for progress context.",
            accent="Why it matters",
        )
        panel(
            "Demo target",
            "A parent can create a profile, generate a story, and complete a scored session during a short live demo.",
            accent="Acceptance",
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
            st.success("Profile created.")
            st.page_link("pages/2_Generate_Story.py", label="Generate a storybook")

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
                    disabled=not has_baseline,
                )
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
