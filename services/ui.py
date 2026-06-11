from __future__ import annotations

from datetime import datetime
import html
from typing import Optional

import streamlit as st

from models.schemas import ChildProfile
from services import storage


def setup_page(title: str) -> None:
    st.set_page_config(page_title=f"YES! | {title}", layout="wide", initial_sidebar_state="collapsed")
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
        header[data-testid="stHeader"] { background: #f6f4ed; }
        .block-container {
            padding-top: 2.55rem;
            padding-bottom: 3rem;
            max-width: 1180px;
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
        .yes-main-menu {
            display: flex;
            flex-wrap: wrap;
            align-items: center;
            gap: 0.45rem;
            margin: 2.15rem 0 0.65rem;
        }
        .yes-main-menu a {
            display: inline-flex;
            align-items: center;
            min-height: 2.15rem;
            padding: 0.28rem 0.7rem;
            border: 1px solid var(--yes-line);
            border-radius: 8px;
            background: #fffdf7;
            color: var(--yes-charcoal);
            text-decoration: none;
            font-weight: 750;
            font-size: 0.86rem;
        }
        .yes-main-menu a.active {
            background: var(--yes-charcoal);
            color: #ffffff;
            border-color: var(--yes-charcoal);
        }
        .yes-hero {
            background: var(--yes-charcoal);
            border: 1px solid #343b37;
            border-radius: 8px;
            padding: 0.95rem 1.1rem;
            color: #ffffff;
            margin-bottom: 0.85rem;
        }
        .yes-hero h1 {
            color: #ffffff;
            margin: 0.08rem 0 0.2rem 0;
            font-size: clamp(1.7rem, 3.3vw, 2.55rem);
            line-height: 1.05;
        }
        .yes-hero p {
            max-width: 760px;
            margin: 0;
            color: #ede7d8;
            font-size: 0.98rem;
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
            margin: 0.65rem 0 1rem;
        }
        .yes-step-link {
            display: block;
            background: #ffffff;
            border: 1px solid var(--yes-line);
            border-radius: 8px;
            padding: 0.72rem;
            min-height: 86px;
            text-decoration: none;
            transition: border-color 120ms ease, box-shadow 120ms ease, transform 120ms ease;
        }
        .yes-step-link:hover {
            border-color: var(--yes-gold-deep);
            box-shadow: 0 6px 18px rgba(32, 39, 36, 0.08);
            transform: translateY(-1px);
        }
        .yes-step-link.active {
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
        .yes-reader-shell {
            background: #fffaf0;
            border: 1px solid var(--yes-line);
            border-radius: 8px;
            padding: clamp(1rem, 2.5vw, 1.65rem);
            margin-bottom: 0.9rem;
        }
        .yes-reader-title {
            color: var(--yes-charcoal);
            font-size: clamp(2rem, 4.5vw, 3.2rem);
            line-height: 1.02;
            font-weight: 850;
            margin-bottom: 0.35rem;
        }
        .yes-reader-meta {
            color: var(--yes-muted);
            font-weight: 650;
            margin-bottom: 1rem;
        }
        .yes-reader-text {
            color: #202724;
            font-size: clamp(1.22rem, 2.1vw, 1.55rem);
            line-height: 1.82;
        }
        .yes-reader-text p {
            margin: 0 0 1.05rem;
        }
        .yes-reader-text mark {
            background: #ffe89a;
            color: #1f241f;
            padding: 0.02rem 0.18rem;
            border-radius: 5px;
        }
        .yes-quiz-ready {
            background: #202724;
            border-radius: 8px;
            color: #ffffff;
            padding: 0.95rem;
            margin-bottom: 0.9rem;
        }
        .yes-quiz-ready strong {
            display: block;
            color: var(--yes-gold);
            margin-bottom: 0.25rem;
        }
        .yes-session-summary {
            background: #fffdf7;
            border: 1px solid var(--yes-line);
            border-left: 5px solid var(--yes-green);
            border-radius: 8px;
            padding: 1rem;
            margin: 0.85rem 0 1rem;
        }
        .yes-session-summary h3 {
            margin: 0 0 0.35rem;
            color: var(--yes-charcoal);
        }
        .yes-summary-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 0.65rem;
            margin-top: 0.75rem;
        }
        .yes-summary-item {
            background: #ffffff;
            border: 1px solid var(--yes-line);
            border-radius: 8px;
            padding: 0.7rem;
        }
        .yes-summary-label {
            color: var(--yes-muted);
            font-size: 0.76rem;
            font-weight: 800;
            text-transform: uppercase;
            letter-spacing: 0.06em;
        }
        .yes-summary-value {
            color: var(--yes-charcoal);
            font-size: 1.05rem;
            font-weight: 850;
            line-height: 1.25;
            margin-top: 0.18rem;
        }
        @media (max-width: 760px) {
            .yes-quick-grid {
                grid-template-columns: 1fr;
            }
            .yes-main-menu a { flex: 1 1 auto; justify-content: center; }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
    active = _menu_key_for_title(title)
    sidebar_menu()
    main_menu(active)


def _menu_key_for_title(title: str) -> str:
    return {
        "Home": "home",
        "Child Profile": "profiles",
        "Generate Story": "",
        "Reading Session": "",
        "Parent Dashboard": "dashboard",
    }.get(title, "")


def main_menu(active: str = "") -> None:
    items = [
        ("home", "Home", "/"),
        ("profiles", "Profiles", "/Child_Profile"),
        ("dashboard", "Dashboard", "/Parent_Dashboard"),
    ]
    markup = ['<nav class="yes-main-menu" aria-label="Main navigation">']
    for key, label, href in items:
        active_class = " active" if key == active else ""
        markup.append(f'<a class="{active_class}" href="{href}" target="_self">{html.escape(label)}</a>')
    markup.append("</nav>")
    st.markdown("".join(markup), unsafe_allow_html=True)


def sidebar_menu() -> None:
    with st.sidebar:
        st.markdown("### Your Endless Stories")
        st.caption("Powered by OCI")
        st.markdown('<a href="/" target="_self">Home</a>', unsafe_allow_html=True)
        st.page_link("pages/1_Child_Profile.py", label="Child Profiles")
        st.page_link("pages/2_Generate_Story.py", label="Storybooks")
        st.page_link("pages/3_Reading_Session.py", label="Read Story")
        st.page_link("pages/4_Parent_Dashboard.py", label="Proficiency Dashboard")


def page_title(title: str, subtitle: str = "", meta: list[str] | None = None) -> None:
    hero(title, subtitle, meta=meta)


def hero(title: str, subtitle: str = "", eyebrow: str = "Your Endless Stories | Powered by OCI", meta: list[str] | None = None) -> None:
    meta = meta or []
    meta_html = "".join(f'<span class="yes-pill">{html.escape(item)}</span>' for item in meta)
    subtitle_html = f'<p>{html.escape(subtitle)}</p>' if subtitle else ""
    meta_block = f'<div class="yes-hero-meta">{meta_html}</div>' if meta_html else ""
    st.markdown(
        (
            f'<section class="yes-hero">'
            f'<div class="yes-kicker">{html.escape(eyebrow)}</div>'
            f'<h1>{html.escape(title)}</h1>'
            f'{subtitle_html}'
            f'{meta_block}'
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
        ("profile", "1", "Profile", "Pick or create a reader", "/Child_Profile"),
        ("story", "2", "Storybook", "Choose or generate", "/Generate_Story"),
        ("session", "3", "Read", "Story and word help", "/Reading_Session"),
        ("check", "4", "Reading Check", "Quiz and scoring", "/Reading_Session"),
        ("dashboard", "5", "Dashboard", "Scores and trends", "/Parent_Dashboard"),
    ]
    markup = ['<div class="yes-flow">']
    for key, number, title, copy, href in steps:
        active_class = " active" if key == active else ""
        markup.append(
            f'<a class="yes-step-link{active_class}" href="{href}" target="_self">'
            f'<div class="yes-step-number">{html.escape(number)}</div>'
            f'<span class="yes-step-title">{html.escape(title)}</span>'
            f'<div class="yes-step-copy">{html.escape(copy)}</div>'
            f'</a>'
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
    return f"{score:.0f}/100"
