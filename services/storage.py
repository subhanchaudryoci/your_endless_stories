from __future__ import annotations

import json
import os
import sqlite3
from pathlib import Path
from typing import Any, Optional

from models.schemas import (
    ChildProfile,
    QuizQuestion,
    ReadingSession,
    ScoreBreakdown,
    StoryBook,
    VocabularyItem,
    utc_now_iso,
)


APP_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = APP_ROOT / "data"
DEFAULT_DB_PATH = DATA_DIR / "yes.db"
SEED_PATH = DATA_DIR / "seed_data.json"
JUDGE_DEMO_CHILD_NAME = "Mia"
JUDGE_DEMO_STORY_TITLE = "Mia and the Moon Cat"
JUDGE_DEMO_QUESTION = "What did Mia draw one night?"


def db_path() -> Path:
    configured = os.getenv("YES_DB_PATH")
    if configured:
        return Path(configured).expanduser()
    return DEFAULT_DB_PATH


def connect() -> sqlite3.Connection:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path())
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(seed: bool = True) -> None:
    with connect() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS children (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                age INTEGER NOT NULL,
                interests_json TEXT NOT NULL,
                reading_goal TEXT NOT NULL,
                baseline_score REAL,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS stories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                child_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                story_text TEXT NOT NULL,
                vocabulary_json TEXT NOT NULL,
                questions_json TEXT NOT NULL,
                tricky_words_json TEXT NOT NULL,
                theme TEXT,
                source TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY(child_id) REFERENCES children(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                child_id INTEGER NOT NULL,
                story_id INTEGER NOT NULL,
                answers_json TEXT NOT NULL,
                score_json TEXT NOT NULL,
                quiz_score REAL NOT NULL,
                total_score REAL NOT NULL,
                notes TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY(child_id) REFERENCES children(id) ON DELETE CASCADE,
                FOREIGN KEY(story_id) REFERENCES stories(id) ON DELETE CASCADE
            );
            """
        )
        child_count = conn.execute("SELECT COUNT(*) FROM children").fetchone()[0]
    if seed:
        if child_count == 0:
            seed_demo_data()
        else:
            seed_missing_demo_children()


def _dumps(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False)


def _loads(value: str | None, default: Any) -> Any:
    if not value:
        return default
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return default


def _child_from_row(row: sqlite3.Row) -> ChildProfile:
    return ChildProfile(
        id=row["id"],
        name=row["name"],
        age=row["age"],
        interests=_loads(row["interests_json"], []),
        reading_goal=row["reading_goal"],
        baseline_score=row["baseline_score"],
        created_at=row["created_at"],
    )


def _story_from_row(row: sqlite3.Row) -> StoryBook:
    vocabulary = [
        VocabularyItem.from_dict(item)
        for item in _loads(row["vocabulary_json"], [])
        if isinstance(item, dict)
    ]
    questions = [
        QuizQuestion.from_dict(item)
        for item in _loads(row["questions_json"], [])
        if isinstance(item, dict)
    ]
    return StoryBook(
        id=row["id"],
        child_id=row["child_id"],
        title=row["title"],
        story_text=row["story_text"],
        vocabulary=vocabulary,
        questions=questions,
        tricky_words=_loads(row["tricky_words_json"], []),
        theme=row["theme"] or "",
        source=row["source"],
        created_at=row["created_at"],
    )


def _score_from_dict(data: dict[str, Any]) -> ScoreBreakdown:
    return ScoreBreakdown(
        phonics_decoding=float(data.get("phonics_decoding", 0)),
        fluency=float(data.get("fluency", 0)),
        comprehension=float(data.get("comprehension", 0)),
        independence=float(data.get("independence", 0)),
        consistency=float(data.get("consistency", 0)),
        total=float(data.get("total", 0)),
        strengths=list(data.get("strengths", [])),
        weak_areas=list(data.get("weak_areas", [])),
        recommendation=str(data.get("recommendation", "")),
        details=dict(data.get("details", {})),
    )


def _session_from_row(row: sqlite3.Row) -> ReadingSession:
    score = _score_from_dict(_loads(row["score_json"], {}))
    return ReadingSession(
        id=row["id"],
        child_id=row["child_id"],
        story_id=row["story_id"],
        answers=_loads(row["answers_json"], {}),
        score=score,
        quiz_score=row["quiz_score"],
        total_score=row["total_score"],
        notes=row["notes"] or "",
        created_at=row["created_at"],
    )


def create_child(profile: ChildProfile) -> int:
    with connect() as conn:
        cursor = conn.execute(
            """
            INSERT INTO children (name, age, interests_json, reading_goal, baseline_score, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                profile.name.strip(),
                int(profile.age),
                _dumps(profile.interests),
                profile.reading_goal.strip(),
                profile.baseline_score,
                profile.created_at or utc_now_iso(),
            ),
        )
        return int(cursor.lastrowid)


def update_child(profile: ChildProfile) -> None:
    if profile.id is None:
        raise ValueError("Cannot update a child profile without an id.")
    with connect() as conn:
        conn.execute(
            """
            UPDATE children
            SET name = ?, age = ?, interests_json = ?, reading_goal = ?, baseline_score = ?
            WHERE id = ?
            """,
            (
                profile.name.strip(),
                int(profile.age),
                _dumps(profile.interests),
                profile.reading_goal.strip(),
                profile.baseline_score,
                profile.id,
            ),
        )


def list_children() -> list[ChildProfile]:
    with connect() as conn:
        rows = conn.execute("SELECT * FROM children ORDER BY name COLLATE NOCASE").fetchall()
    return [_child_from_row(row) for row in rows]


def find_child_by_name(name: str) -> Optional[ChildProfile]:
    with connect() as conn:
        row = conn.execute(
            "SELECT * FROM children WHERE lower(name) = lower(?) ORDER BY id LIMIT 1",
            (name.strip(),),
        ).fetchone()
    return _child_from_row(row) if row else None


def get_child(child_id: int) -> Optional[ChildProfile]:
    with connect() as conn:
        row = conn.execute("SELECT * FROM children WHERE id = ?", (child_id,)).fetchone()
    return _child_from_row(row) if row else None


def save_story(story: StoryBook) -> int:
    with connect() as conn:
        cursor = conn.execute(
            """
            INSERT INTO stories (
                child_id, title, story_text, vocabulary_json, questions_json,
                tricky_words_json, theme, source, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                story.child_id,
                story.title,
                story.story_text,
                _dumps([item.__dict__ for item in story.vocabulary]),
                _dumps([item.__dict__ for item in story.questions]),
                _dumps(story.tricky_words),
                story.theme,
                story.source,
                story.created_at or utc_now_iso(),
            ),
        )
        return int(cursor.lastrowid)


def list_stories(child_id: Optional[int] = None, limit: int = 50) -> list[StoryBook]:
    with connect() as conn:
        if child_id is None:
            rows = conn.execute(
                "SELECT * FROM stories ORDER BY datetime(created_at) DESC LIMIT ?",
                (limit,),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM stories WHERE child_id = ? ORDER BY datetime(created_at) DESC LIMIT ?",
                (child_id, limit),
            ).fetchall()
    return [_story_from_row(row) for row in rows]


def get_story(story_id: int) -> Optional[StoryBook]:
    with connect() as conn:
        row = conn.execute("SELECT * FROM stories WHERE id = ?", (story_id,)).fetchone()
    return _story_from_row(row) if row else None


def find_story_by_title(child_id: int, title: str) -> Optional[StoryBook]:
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT * FROM stories
            WHERE child_id = ? AND lower(title) = lower(?)
            ORDER BY datetime(created_at) DESC, id DESC
            """,
            (child_id, title.strip()),
        ).fetchall()
    for row in rows:
        story = _story_from_row(row)
        if any(question.question == JUDGE_DEMO_QUESTION for question in story.questions):
            return story
    return _story_from_row(rows[0]) if rows else None


def save_session(session: ReadingSession) -> int:
    with connect() as conn:
        cursor = conn.execute(
            """
            INSERT INTO sessions (
                child_id, story_id, answers_json, score_json, quiz_score,
                total_score, notes, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                session.child_id,
                session.story_id,
                _dumps(session.answers),
                _dumps(session.score.to_dict()),
                session.quiz_score,
                session.total_score,
                session.notes,
                session.created_at or utc_now_iso(),
            ),
        )
        return int(cursor.lastrowid)


def list_sessions(child_id: Optional[int] = None, limit: int = 100) -> list[ReadingSession]:
    with connect() as conn:
        if child_id is None:
            rows = conn.execute(
                "SELECT * FROM sessions ORDER BY datetime(created_at) DESC LIMIT ?",
                (limit,),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM sessions WHERE child_id = ? ORDER BY datetime(created_at) DESC LIMIT ?",
                (child_id, limit),
            ).fetchall()
    return [_session_from_row(row) for row in rows]


def profile_stats(child_id: int) -> dict[str, Any]:
    stories = list_stories(child_id)
    sessions = list_sessions(child_id)
    latest = sessions[0] if sessions else None
    average = sum(session.total_score for session in sessions) / len(sessions) if sessions else None
    return {
        "story_count": len(stories),
        "session_count": len(sessions),
        "latest_score": latest.total_score if latest else None,
        "average_score": average,
        "latest_session_at": latest.created_at if latest else None,
    }


def _load_seed_payload() -> dict[str, Any]:
    if not SEED_PATH.exists():
        return {}
    try:
        return json.loads(SEED_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def _seed_story_payload(child_id: int, story_data: dict[str, Any]) -> int:
    story = StoryBook.from_dict(story_data, child_id=child_id, source=story_data.get("source", "seed"))
    story_id = save_story(story)

    for session_data in story_data.get("sessions", []):
        score = _score_from_dict(session_data.get("score", {}))
        session = ReadingSession(
            id=None,
            child_id=child_id,
            story_id=story_id,
            answers=dict(session_data.get("answers", {})),
            score=score,
            quiz_score=float(session_data.get("quiz_score", score.comprehension)),
            total_score=float(session_data.get("total_score", score.total)),
            notes=session_data.get("notes", ""),
            created_at=session_data.get("created_at", utc_now_iso()),
        )
        save_session(session)
    return story_id


def _seed_child_payload(child_data: dict[str, Any]) -> int:
    profile = ChildProfile(
        id=None,
        name=child_data["name"],
        age=int(child_data["age"]),
        interests=list(child_data.get("interests", [])),
        reading_goal=child_data.get("reading_goal", "Build reading confidence"),
        baseline_score=child_data.get("baseline_score"),
        created_at=child_data.get("created_at", utc_now_iso()),
    )
    child_id = create_child(profile)

    for story_data in child_data.get("stories", []):
        _seed_story_payload(child_id, story_data)
    return child_id


def _seed_missing_stories(child_id: int, child_data: dict[str, Any]) -> None:
    existing_titles = {story.title.strip().lower() for story in list_stories(child_id, limit=200)}
    for story_data in child_data.get("stories", []):
        title = str(story_data.get("title", "")).strip()
        if not title or title.lower() in existing_titles:
            continue
        _seed_story_payload(child_id, story_data)
        existing_titles.add(title.lower())


def seed_missing_demo_children() -> None:
    payload = _load_seed_payload()
    existing_children = {child.name.strip().lower(): child for child in list_children()}
    for child_data in payload.get("children", []):
        name = str(child_data.get("name", "")).strip()
        if not name:
            continue
        existing_child = existing_children.get(name.lower())
        if existing_child and existing_child.id:
            _seed_missing_stories(existing_child.id, child_data)
            continue
        child_id = _seed_child_payload(child_data)
        existing_children[name.lower()] = get_child(child_id) or ChildProfile(
            id=child_id,
            name=name,
            age=int(child_data["age"]),
            interests=list(child_data.get("interests", [])),
            reading_goal=child_data.get("reading_goal", "Build reading confidence"),
        )


def seed_demo_data() -> None:
    seed_missing_demo_children()


def prepare_judge_demo() -> tuple[int, int]:
    seed_missing_demo_children()
    child = find_child_by_name(JUDGE_DEMO_CHILD_NAME)
    if child is None or child.id is None:
        raise RuntimeError("Judge demo child profile is missing.")

    story = find_story_by_title(child.id, JUDGE_DEMO_STORY_TITLE)
    if story and story.id and any(question.question == JUDGE_DEMO_QUESTION for question in story.questions):
        return child.id, story.id

    payload = _load_seed_payload()
    for child_data in payload.get("children", []):
        if str(child_data.get("name", "")).strip().lower() != JUDGE_DEMO_CHILD_NAME.lower():
            continue
        for story_data in child_data.get("stories", []):
            if str(story_data.get("title", "")).strip().lower() == JUDGE_DEMO_STORY_TITLE.lower():
                story_id = _seed_story_payload(child.id, story_data)
                return child.id, story_id

    if story and story.id:
        return child.id, story.id
    raise RuntimeError("Judge demo storybook is missing.")
