from __future__ import annotations

from datetime import datetime
import html
from typing import Optional

import streamlit as st

from models.schemas import ChildProfile
from services import storage


def setup_page(title: str) -> None:
    st.set_page_config(page_title=f"YES! | {title}", layout="wide")
    storage.init_db()
    st.markdown(
        """
        <style>
        :root {
            --yes-ink: #202724;
            --yes-charcoal: #1e211f;
            --yes-panel: #242a27;
            --yes-gold: #f3cd69;
            --yes-gold-deep: #a77d18;
            --yes-green: #2f765f;
            --yes-blue: #2e6076;
            --yes-paper: #fffdf7;
            --yes-line: #ded8c7;
            --yes-muted: #65716b;
        }
        .stApp { background: #f6f4ed; }
        .block-container {
            padding-top: 1.1rem;
            padding-bottom: 3rem;
            max-width: 1220px;
        }
        h1, h2, h3 { letter-spacing: 0; }
        h1 { color: var(--yes-charcoal); }
        div[data-testid="stMetric"] {
            background: #fffdf7;
            border: 1px solid var(--yes-line);
            border-radius: 8px;
            padding: 0.8rem 0.9rem;
        }
        div[data-testid="stMetricLabel"] { color: var(--yes-muted); }
        div[data-testid="stMetricValue"] { color: var(--yes-green); font-weight: 750; }
        div.stButton > button[kind="primary"] {
            background: var(--yes-gold);
            border: 1px solid #d3ad48;
            color: #1d211f;
            font-weight: 750;
        }
        div.stButton > button {
            border-radius: 8px;
            border-color: var(--yes-line);
            font-weight: 650;
        }
        div[data-testid="stTabs"] button p { font-weight: 650; }
        .yes-hero {
            background: var(--yes-charcoal);
            border: 1px solid #343b37;
            border-radius: 8px;
            padding: 1.35rem 1.55rem;
            color: #ffffff;
            margin-bottom: 1rem;
            position: relative;
            overflow: hidden;
        }
        .yes-hero:after {
            content: "";
            position: absolute;
            right: 1.1rem;
            top: 1.1rem;
            width: 9rem;
            height: 4.2rem;
            border: 1px solid rgba(243, 205, 105, 0.7);
        }
        .yes-hero h1 {
            color: #ffffff;
            margin: 0.1rem 0 0.25rem 0;
            font-size: clamp(2rem, 5vw, 3.25rem);
            line-height: 1.03;
        }
        .yes-hero p {
            max-width: 790px;
            margin: 0;
            color: #ede7d8;
            font-size: 1.02rem;
        }
        .yes-kicker {
            color: var(--yes-gold);
            text-transform: uppercase;
            font-size: 0.78rem;
            font-weight: 800;
            letter-spacing: 0.08em;
        }
        .yes-hero-meta {
            display: flex;
            flex-wrap: wrap;
            gap: 0.45rem;
            margin-top: 0.9rem;
            max-width: 860px;
        }
        .yes-pill {
            display: inline-flex;
            align-items: center;
            border: 1px solid rgba(243, 205, 105, 0.45);
            border-radius: 999px;
            padding: 0.2rem 0.55rem;
            color: #fff8df;
            background: rgba(255, 255, 255, 0.05);
            font-size: 0.78rem;
            font-weight: 650;
        }
        .yes-panel,
        .yes-soft,
        .yes-story {
            background: var(--yes-paper);
            border: 1px solid var(--yes-line);
            border-radius: 8px;
        }
        .yes-panel { padding: 1rem; }
        .yes-panel h3,
        .yes-soft h3 {
            margin-top: 0;
            margin-bottom: 0.35rem;
            font-size: 1rem;
        }
        .yes-panel p,
        .yes-soft p { margin: 0.25rem 0; }
        .yes-story {
            padding: 1.25rem;
            line-height: 1.75;
            font-size: 1.08rem;
            color: #222824;
        }
        .yes-soft {
            padding: 1rem;
        }
        .yes-profile-name {
            font-size: 1.2rem;
            font-weight: 800;
            color: var(--yes-charcoal);
        }
        .yes-muted { color: var(--yes-muted); }
        .yes-status {
            border-radius: 8px;
            padding: 0.72rem 0.9rem;
            border: 1px solid;
            margin-bottom: 1rem;
            font-weight: 650;
        }
        .yes-status.good {
            background: #edf6f0;
            border-color: #b8d9c4;
            color: #1d5d45;
        }
        .yes-status.warn {
            background: #fff7dc;
            border-color: #e8ca6c;
            color: #665014;
        }
        .yes-flow {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(128px, 1fr));
            gap: 0.65rem;
            margin: 0.8rem 0 1rem;
        }
        .yes-step {
            background: #ffffff;
            border: 1px solid var(--yes-line);
            border-radius: 8px;
            padding: 0.72rem;
            min-height: 86px;
        }
        .yes-step.active {
            border-color: var(--yes-gold-deep);
            box-shadow: inset 0 0 0 2px rgba(243, 205, 105, 0.3);
        }
        .yes-step-number {
            color: var(--yes-gold-deep);
            font-weight: 850;
            font-size: 0.8rem;
        }
        .yes-step-title {
            display: block;
            color: var(--yes-charcoal);
            font-weight: 800;
            margin-top: 0.16rem;
        }
        .yes-step-copy {
            color: var(--yes-muted);
            font-size: 0.84rem;
            line-height: 1.28;
            margin-top: 0.25rem;
        }
        .yes-quick-grid {
            display: grid;
            grid-template-columns: repeat(2, minmax(0, 1fr));
            gap: 0.65rem;
        }
        .yes-action {
            background: #ffffff;
            border: 1px solid var(--yes-line);
            border-left: 4px solid var(--yes-gold);
            border-radius: 8px;
            padding: 0.9rem;
            min-height: 104px;
        }
        .yes-action strong {
            display: block;
            color: var(--yes-charcoal);
            margin-bottom: 0.3rem;
        }
        .yes-action span {
            color: var(--yes-muted);
            font-size: 0.9rem;
        }
        .yes-word-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
            gap: 0.6rem;
            margin-top: 0.5rem;
        }
        .yes-word-card {
            background: #ffffff;
            border: 1px solid var(--yes-line);
            border-radius: 8px;
            padding: 0.78rem;
        }
        .yes-word {
            color: var(--yes-green);
            font-weight: 850;
            font-size: 1.02rem;
        }
        .yes-hint {
            color: var(--yes-muted);
            font-size: 0.86rem;
            line-height: 1.35;
        }
        .yes-question {
            background: #ffffff;
            border: 1px solid var(--yes-line);
            border-radius: 8px;
            padding: 0.85rem;
            margin-bottom: 0.7rem;
        }
        .yes-question-type {
            color: var(--yes-blue);
            text-transform: uppercase;
            font-size: 0.72rem;
            font-weight: 850;
            letter-spacing: 0.06em;
        }
        .yes-note {
            border-left: 4px solid var(--yes-green);
            background: #eef7f2;
            border-radius: 8px;
            padding: 0.85rem;
            color: #24463a;
        }
        @media (max-width: 760px) {
            .yes-quick-grid {
                grid-template-columns: 1fr;
            }
            .yes-hero:after { display: none; }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def page_title(title: str, subtitle: str = "", meta: list[str] | None = None) -> None:
    hero(title, subtitle, meta=meta)


def hero(title: str, subtitle: str = "", eyebrow: str = "Your Endless Stories | Powered by OCI", meta: list[str] | None = None) -> None:
    meta = meta or []
    meta_html = "".join(f'<span class="yes-pill">{html.escape(item)}</span>' for item in meta)
    st.markdown(
        (
            f'<section class="yes-hero">'
            f'<div class="yes-kicker">{html.escape(eyebrow)}</div>'
            f'<h1>{html.escape(title)}</h1>'
            f'<p>{html.escape(subtitle)}</p>'
            f'<div class="yes-hero-meta">{meta_html}</div>'
            f'</section>'
        ),
        unsafe_allow_html=True,
    )


def genai_status_banner(status: dict) -> None:
    if status.get("configured"):
        message = "OCI Generative AI connected. Live story, quiz, hint, and parent summaries are enabled."
        css_class = "good"
    else:
        missing = ", ".join(status.get("missing") or []) or "YES_DEMO_MODE is enabled"
        message = f"Demo mode active. Missing: {missing}."
        css_class = "warn"
    st.markdown(f'<div class="yes-status {css_class}">{html.escape(message)}</div>', unsafe_allow_html=True)


def workflow_steps(active: str) -> None:
    steps = [
        ("profile", "1", "Profile", "Age, interests, goal"),
        ("story", "2", "Storybook", "OCI-generated reading set"),
        ("session", "3", "Session", "Quiz plus transparent score"),
        ("dashboard", "4", "Dashboard", "Progress and next practice"),
    ]
    markup = ['<div class="yes-flow">']
    for key, number, title, copy in steps:
        active_class = " active" if key == active else ""
        markup.append(
            f'<div class="yes-step{active_class}">'
            f'<div class="yes-step-number">{html.escape(number)}</div>'
            f'<span class="yes-step-title">{html.escape(title)}</span>'
            f'<div class="yes-step-copy">{html.escape(copy)}</div>'
            f'</div>'
        )
    markup.append("</div>")
    st.markdown("".join(markup), unsafe_allow_html=True)


def panel(title: str, body: str, *, accent: str = "") -> None:
    accent_html = f'<div class="yes-kicker">{html.escape(accent)}</div>' if accent else ""
    st.markdown(
        (
            f'<div class="yes-panel">'
            f'{accent_html}'
            f'<h3>{html.escape(title)}</h3>'
            f'<p>{html.escape(body)}</p>'
            f'</div>'
        ),
        unsafe_allow_html=True,
    )


def action_grid(actions: list[tuple[str, str]]) -> None:
    markup = ['<div class="yes-quick-grid">']
    for title, body in actions:
        markup.append(
            f'<div class="yes-action">'
            f'<strong>{html.escape(title)}</strong>'
            f'<span>{html.escape(body)}</span>'
            f'</div>'
        )
    markup.append("</div>")
    st.markdown("".join(markup), unsafe_allow_html=True)


def selected_child_id() -> Optional[int]:
    value = st.session_state.get("selected_child_id")
    return int(value) if value else None


def child_selector(label: str = "Child profile") -> Optional[ChildProfile]:
    children = storage.list_children()
    if not children:
        st.info("Create a child profile to begin.")
        st.page_link("pages/1_Child_Profile.py", label="Go to child profiles")
        return None

    current_id = selected_child_id()
    default_index = 0
    if current_id:
        for index, child in enumerate(children):
            if child.id == current_id:
                default_index = index
                break

    child = st.selectbox(
        label,
        children,
        index=default_index,
        format_func=lambda item: f"{item.name}, age {item.age}",
    )
    if child and child.id:
        st.session_state["selected_child_id"] = child.id
    return child


def profile_summary(child: ChildProfile) -> None:
    interests = ", ".join(child.interests) if child.interests else "Not set"
    baseline = "Not set" if child.baseline_score is None else f"{child.baseline_score:.0f}/100"
    st.markdown(
        (
            f'<div class="yes-soft">'
            f'<div class="yes-profile-name">{html.escape(child.name)}</div>'
            f'<div class="yes-muted">Age {child.age}</div>'
            f'<p><strong>Interests:</strong> {html.escape(interests)}</p>'
            f'<p><strong>Goal:</strong> {html.escape(child.reading_goal)}</p>'
            f'<p><strong>Baseline:</strong> {html.escape(baseline)}</p>'
            f'</div>'
        ),
        unsafe_allow_html=True,
    )


def format_date(value: str) -> str:
    if not value:
        return ""
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return parsed.strftime("%b %d, %Y")
    except ValueError:
        return value[:10]


def score_badge(score: float | None) -> str:
    if score is None:
        return "No score yet"
    if score >= 85:
        label = "Strong"
    elif score >= 70:
        label = "Growing"
    else:
        label = "Practice focus"
    return f"{score:.0f}/100 - {label}"
